from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import QuizStatus, QuizType, QuestionType, TaskStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import (
    CourseMaterial,
    CourseMembership,
    KnowledgeChunk,
    KnowledgePoint,
    QARecord,
    ProblemRecord,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizQuestion,
    Lesson,
    LessonPage,
    StudyCheckin,
    StudyPlan,
    StudyPlanTask,
    User,
    WrongQuestion,
    LearningProgress,
)
from app.schemas.learning import QuizGenerateRequest, StudyPlanCreateRequest
from app.services.ai import ai_service
from app.services.courses import _assert_course_owner, _get_course_or_404
from app.services.knowledge import ensure_knowledge_points
from app.services.usage import log_ai_usage


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内使用该功能")


def get_knowledge_points(db: Session, *, course_id: int, chapter_id: int | None, user: User) -> list[KnowledgePoint]:
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=course_id, user=user)
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, course_id)
        _assert_course_owner(course, user)
    return ensure_knowledge_points(db, course_id=course_id, chapter_id=chapter_id)


_PLACEHOLDER_SOURCE_TEXT = (
    "本页未提取到有效文字内容",
    "未提取到资料内容",
    "可结合课程资料进一步补充",
)


def _flatten_text(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        pieces: list[str] = []
        for item in value.values():
            pieces.extend(_flatten_text(item))
        return pieces
    if isinstance(value, (list, tuple, set)):
        pieces = []
        for item in value:
            pieces.extend(_flatten_text(item))
        return pieces
    text = " ".join(str(value).split())
    return [text] if text else []


def _append_source_piece(pieces: list[str], seen: set[str], value, *, limit: int = 1400) -> None:
    for text in _flatten_text(value):
        if not text or any(marker in text for marker in _PLACEHOLDER_SOURCE_TEXT):
            continue
        compact = text[:limit]
        fingerprint = compact[:220]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        pieces.append(compact)


def _knowledge_text_for_quiz(points: list[KnowledgePoint], *, pieces: list[str], seen: set[str]) -> None:
    for point in points[:12]:
        _append_source_piece(pieces, seen, f"知识点：{point.name}\n{point.description or ''}")
        content = point.content_by_level or {}
        if isinstance(content, dict):
            _append_source_piece(pieces, seen, content)


def _course_source_text_for_quiz(
    db: Session,
    *,
    course_id: int,
    chapter_ids: list[int],
    points: list[KnowledgePoint],
) -> str:
    pieces: list[str] = []
    seen: set[str] = set()

    chunk_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_ids:
        chunk_statement = chunk_statement.where(KnowledgeChunk.chapter_id.in_(chapter_ids))
    for chunk in db.scalars(chunk_statement.order_by(KnowledgeChunk.id).limit(16)):
        _append_source_piece(pieces, seen, f"{chunk.title}\n{chunk.content}", limit=1200)

    page_statement = select(LessonPage, Lesson).join(Lesson, Lesson.id == LessonPage.lesson_id).where(Lesson.course_id == course_id)
    if chapter_ids:
        page_statement = page_statement.where(Lesson.chapter_id.in_(chapter_ids))
    for page, lesson in db.execute(page_statement.order_by(Lesson.id, LessonPage.page_number).limit(16)):
        title = page.page_title or f"{lesson.title} 第{page.page_number}页"
        _append_source_piece(pieces, seen, f"{lesson.title} - {title}\n{page.page_text}", limit=1200)

    material_statement = select(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
    if chapter_ids:
        material_statement = material_statement.where(CourseMaterial.chapter_id.in_(chapter_ids))
    for material in db.scalars(material_statement.order_by(CourseMaterial.created_at.desc()).limit(8)):
        _append_source_piece(pieces, seen, f"{material.title}\n{material.extracted_text or ''}", limit=1200)

    _knowledge_text_for_quiz(points, pieces=pieces, seen=seen)
    return "\n\n".join(pieces)[:10000]


def _quiz_topic_for_generation(*, course_name: str, points: list[KnowledgePoint], source_text: str) -> str:
    names = [point.name for point in points if point.name and "练习" not in point.name and "测验" not in point.name]
    if names:
        return "、".join(dict.fromkeys(names[:4]))
    keywords = [item for item in ai_service.extract_keywords(source_text, limit=6) if item not in {"课程内容", "章节练习", "薄弱点章节练习"}]
    return "、".join(keywords[:4]) if keywords else course_name


def _chapter_ids_for_quiz(payload: QuizGenerateRequest) -> list[int]:
    values: list[int] = []
    if payload.chapter_id is not None:
        values.append(payload.chapter_id)
    for chapter_id in payload.chapter_ids or []:
        if chapter_id not in values:
            values.append(chapter_id)
    return values


def _knowledge_points_for_quiz(db: Session, *, course_id: int, chapter_ids: list[int]) -> list[KnowledgePoint]:
    if not chapter_ids:
        return ensure_knowledge_points(db, course_id=course_id, chapter_id=None)
    points: list[KnowledgePoint] = []
    seen: set[int] = set()
    for chapter_id in chapter_ids:
        for point in ensure_knowledge_points(db, course_id=course_id, chapter_id=chapter_id):
            if point.id not in seen:
                points.append(point)
                seen.add(point.id)
    return points


def _prioritize_weak_points(db: Session, *, points: list[KnowledgePoint], course_id: int, user: User, enabled: bool) -> list[KnowledgePoint]:
    if not enabled or user.role != UserRole.STUDENT.value or not points:
        return points
    weak_ids = [
        point_id
        for point_id in db.scalars(
            select(WrongQuestion.knowledge_point_id)
            .where(
                WrongQuestion.user_id == user.id,
                WrongQuestion.course_id == course_id,
                WrongQuestion.knowledge_point_id.is_not(None),
            )
            .group_by(WrongQuestion.knowledge_point_id)
            .order_by(func.sum(WrongQuestion.wrong_count).desc())
        )
        if point_id is not None
    ]
    if not weak_ids:
        return points
    weak_rank = {point_id: index for index, point_id in enumerate(weak_ids)}
    return sorted(points, key=lambda point: (weak_rank.get(point.id, len(weak_rank)), point.id))


def generate_quiz(db: Session, *, user: User, payload: QuizGenerateRequest) -> Quiz:
    course = _get_course_or_404(db, payload.course_id)
    if payload.quiz_type not in {item.value for item in QuizType}:
        raise bad_request("测验类型不合法")
    if user.role == UserRole.STUDENT.value and payload.quiz_type == QuizType.COURSE.value:
        raise forbidden("学生不能直接生成课程测验")
    if user.role == UserRole.TEACHER.value:
        _assert_course_owner(course, user)
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=payload.course_id, user=user)
    chapter_ids = _chapter_ids_for_quiz(payload)
    points = _knowledge_points_for_quiz(db, course_id=payload.course_id, chapter_ids=chapter_ids)
    points = _prioritize_weak_points(
        db,
        points=points,
        course_id=payload.course_id,
        user=user,
        enabled=payload.prefer_weak_points,
    )
    source_text = _course_source_text_for_quiz(db, course_id=payload.course_id, chapter_ids=chapter_ids, points=points)
    if not source_text.strip():
        target = "所选章节" if chapter_ids else "当前课程"
        raise bad_request(f"{target}暂无可用课程资料，无法生成练习。请先上传并解析课件或发布课时。")
    quiz_topic = _quiz_topic_for_generation(course_name=course.name, points=points, source_text=source_text)
    quiz = Quiz(
        course_id=payload.course_id,
        chapter_id=chapter_ids[0] if len(chapter_ids) == 1 else None,
        creator_id=user.id,
        title=payload.title,
        description=f"基于课程内容自动生成：{payload.title}",
        quiz_type=payload.quiz_type,
        status=QuizStatus.REVIEW.value if payload.quiz_type == QuizType.COURSE.value and user.role != UserRole.STUDENT.value else QuizStatus.PUBLISHED.value,
        metadata_json={
            "generated": True,
            "chapter_ids": chapter_ids,
            "prefer_weak_points": payload.prefer_weak_points,
            "source_topic": quiz_topic,
            "source_chars": len(source_text),
        },
        total_score=0,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    question_dicts = ai_service.generate_quiz_questions(
        topic=quiz_topic,
        source_text=source_text,
        count=payload.question_count,
        db=db,
    )
    total_score = 0.0
    for index, question_dict in enumerate(question_dicts):
        point = points[index % len(points)] if points else None
        question = QuizQuestion(
            quiz_id=quiz.id,
            course_id=payload.course_id,
            chapter_id=point.chapter_id if point else (chapter_ids[0] if len(chapter_ids) == 1 else None),
            knowledge_point_id=point.id if point else None,
            question_type=question_dict["question_type"],
            stem=question_dict["stem"],
            options=question_dict["options"],
            reference_answer=question_dict["reference_answer"],
            explanation=question_dict["explanation"],
            score=float(question_dict["score"]),
            difficulty=question_dict["difficulty"],
        )
        total_score += float(question.score)
        db.add(question)
    quiz.total_score = total_score
    db.add(quiz)
    log_ai_usage(
        db,
        module="quiz_generation",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(source_text),
        completion_chars=sum(len(item["stem"]) for item in question_dicts),
    )
    db.commit()
    return quiz


def publish_quiz(db: Session, *, quiz_id: int, user: User) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    course = _get_course_or_404(db, quiz.course_id)
    _assert_course_owner(course, user)
    quiz.status = QuizStatus.PUBLISHED.value
    quiz.published_at = datetime.now(UTC)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def list_quizzes(db: Session, *, course_id: int, user: User) -> list[Quiz]:
    statement = select(Quiz).where(Quiz.course_id == course_id)
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=course_id, user=user)
        statement = statement.where(
            (Quiz.status == QuizStatus.PUBLISHED.value)
            | ((Quiz.creator_id == user.id) & (Quiz.quiz_type != QuizType.COURSE.value))
        )
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, course_id)
        _assert_course_owner(course, user)
    return list(db.scalars(statement.order_by(Quiz.created_at.desc())))


def get_quiz_detail(db: Session, *, quiz_id: int, user: User) -> tuple[Quiz, list[QuizQuestion]]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=quiz.course_id, user=user)
        if quiz.status != QuizStatus.PUBLISHED.value and quiz.creator_id != user.id:
            raise forbidden("测验尚未发布")
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, quiz.course_id)
        _assert_course_owner(course, user)
    questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.id)))
    return quiz, questions


def extract_reference_answer_value(reference_answer):
    if isinstance(reference_answer, dict):
        for key in ("value", "answer", "correct_answer", "correct", "option_index", "index"):
            if key in reference_answer:
                return reference_answer[key]
        for key in ("values", "answers", "correct_answers"):
            if key in reference_answer:
                return reference_answer[key]
        if "keywords" in reference_answer:
            return reference_answer["keywords"]
        return None
    return reference_answer


def _string_equal(left, right) -> bool:
    return str(left).strip().lower() == str(right).strip().lower()


def _option_index(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
        if len(text) == 1 and text.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return ord(text.upper()) - ord("A")
    return None


def _option_value(value, options: list | None = None):
    index = _option_index(value)
    if index is not None and options and 0 <= index < len(options):
        return options[index]
    return value


def _answer_values(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for separator in ("，", ",", "；", ";", "、"):
            text = text.replace(separator, " ")
        parts = [part for part in text.split() if part]
        if len(parts) > 1 and all(part.isdigit() or (len(part) == 1 and part.isascii() and part.isalpha()) for part in parts):
            return parts
        if 1 < len(text) <= 8 and text.isascii() and text.isalpha() and text.upper() == text:
            return list(text)
        return [text]
    return [value]


def _choice_equal(user_answer, expected, options: list | None = None) -> bool:
    if expected is None:
        return False
    if _string_equal(user_answer, expected):
        return True
    user_index = _option_index(user_answer)
    expected_index = _option_index(expected)
    if user_index is not None and expected_index is not None and user_index == expected_index:
        return True
    if options and isinstance(expected, str):
        try:
            index = int(user_answer)
        except (TypeError, ValueError):
            index = None
        if index is not None and 0 <= index < len(options):
            return _string_equal(options[index], expected)
    if options and isinstance(user_answer, str):
        try:
            index = int(expected)
        except (TypeError, ValueError):
            index = None
        if index is not None and 0 <= index < len(options):
            return _string_equal(user_answer, options[index])
    if options:
        return _string_equal(_option_value(user_answer, options), _option_value(expected, options))
    return False


def _judge_equal(user_answer, expected, options: list | None = None) -> bool:
    if isinstance(expected, bool):
        normalized_user = user_answer
        if isinstance(user_answer, str):
            normalized_user = user_answer.strip().lower()
            if normalized_user in {"true", "正确", "对", "yes", "1"}:
                normalized_user = True
            elif normalized_user in {"false", "错误", "错", "no", "0"}:
                normalized_user = False
        elif isinstance(user_answer, int) and options:
            normalized_user = user_answer == 0
        return normalized_user is expected
    return _choice_equal(user_answer, expected, options)


def _answer_map(answers: list[dict]) -> dict[int, object]:
    mapped: dict[int, object] = {}
    for item in answers:
        try:
            question_id = int(item["question_id"])
        except (KeyError, TypeError, ValueError):
            continue
        mapped[question_id] = item.get("answer")
    return mapped


def _source_question_id(quiz: Quiz, question_id: int) -> int:
    metadata = quiz.metadata_json or {}
    source_map = metadata.get("source_question_map") if isinstance(metadata, dict) else None
    if not isinstance(source_map, dict):
        return question_id
    try:
        return int(source_map.get(str(question_id)) or source_map.get(question_id) or question_id)
    except (TypeError, ValueError):
        return question_id


def _record_answer_to_wrong_book(
    db: Session,
    *,
    user: User,
    quiz: Quiz,
    question: QuizQuestion,
    attempt: QuizAttempt,
    is_correct: bool,
) -> None:
    source_question_id = _source_question_id(quiz, question.id)
    source_question = db.get(QuizQuestion, source_question_id) or question
    wrong = db.scalar(
        select(WrongQuestion).where(WrongQuestion.user_id == user.id, WrongQuestion.question_id == source_question_id)
    )
    if is_correct:
        if quiz.quiz_type == QuizType.WRONG_BOOK.value and wrong is not None:
            db.delete(wrong)
        return
    if wrong is None:
        wrong = WrongQuestion(
            user_id=user.id,
            question_id=source_question_id,
            course_id=quiz.course_id,
            knowledge_point_id=source_question.knowledge_point_id,
            wrong_count=1,
            last_attempt_id=attempt.id,
        )
    else:
        wrong.wrong_count += 1
        wrong.last_attempt_id = attempt.id
    db.add(wrong)


def submit_quiz(db: Session, *, quiz_id: int, user: User, answers: list[dict]) -> QuizAttempt:
    quiz, questions = get_quiz_detail(db, quiz_id=quiz_id, user=user)
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可提交测验")
    answer_map = _answer_map(answers)
    attempt = QuizAttempt(quiz_id=quiz_id, user_id=user.id, total_score=quiz.total_score, submitted_at=datetime.now(UTC))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    total_score = 0.0
    for question in questions:
        user_answer = answer_map.get(question.id)
        is_correct = False
        score = 0.0
        feedback = question.explanation
        has_answer = user_answer is not None and user_answer != "" and user_answer != []
        if not has_answer:
            feedback = "本题未作答。"
        elif question.question_type in {QuestionType.SINGLE_CHOICE.value, QuestionType.JUDGE.value}:
            expected = extract_reference_answer_value(question.reference_answer)
            if question.question_type == QuestionType.JUDGE.value:
                is_correct = _judge_equal(user_answer, expected, question.options)
            else:
                is_correct = _choice_equal(user_answer, expected, question.options)
            score = question.score if is_correct else 0.0
        elif question.question_type == QuestionType.MULTIPLE_CHOICE.value:
            expected = extract_reference_answer_value(question.reference_answer)
            expected_values = sorted(str(_option_index(item) if _option_index(item) is not None else item).lower() for item in _answer_values(expected))
            actual_values = sorted(str(_option_index(item) if _option_index(item) is not None else item).lower() for item in _answer_values(user_answer))
            is_correct = actual_values == expected_values
            score = question.score if is_correct else 0.0
        elif question.question_type == QuestionType.BLANK.value:
            expected = question.reference_answer or {}
            expected_values = []
            if isinstance(expected, dict):
                if "value" in expected:
                    expected_values = [str(expected["value"])]
                else:
                    expected_values = [str(item) for item in expected.get("keywords", [])]
            elif isinstance(expected, list):
                expected_values = [str(item) for item in expected]
            else:
                expected_values = [str(expected)]
            actual_text = str(user_answer or "").lower()
            matched = sum(1 for item in expected_values if item and item.lower() in actual_text)
            is_correct = bool(expected_values) and matched == len(expected_values)
            score = question.score if is_correct else round(question.score * matched / max(len(expected_values), 1), 2)
        else:
            expected_keywords = []
            if isinstance(question.reference_answer, dict):
                expected_keywords = question.reference_answer.get("keywords", [])
            score, feedback = ai_service.score_subjective_answer(
                reference_keywords=expected_keywords,
                user_answer=str(user_answer or ""),
                full_score=question.score,
                db=db,
            )
            is_correct = score >= question.score * 0.6
        total_score += score
        quiz_answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            user_answer=user_answer,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
        )
        db.add(quiz_answer)
        _record_answer_to_wrong_book(db, user=user, quiz=quiz, question=question, attempt=attempt, is_correct=is_correct)
    attempt.score = round(total_score, 2)
    attempt.accuracy = round((total_score / max(quiz.total_score, 1)) * 100, 2)
    attempt.ai_feedback = f"本次得分 {attempt.score}/{quiz.total_score}，建议优先复盘错题并回看对应知识点。"
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def list_wrong_questions(db: Session, *, course_id: int, user: User) -> list[tuple[WrongQuestion, QuizQuestion]]:
    _assert_student_course_access(db, course_id=course_id, user=user)
    rows = list(
        db.execute(
            select(WrongQuestion, QuizQuestion)
            .join(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
            .where(WrongQuestion.user_id == user.id, WrongQuestion.course_id == course_id)
            .order_by(WrongQuestion.updated_at.desc())
        ).all()
    )
    return rows


def generate_wrong_book_practice(db: Session, *, course_id: int, user: User) -> Quiz:
    wrong_rows = list_wrong_questions(db, course_id=course_id, user=user)
    if not wrong_rows:
        raise bad_request("暂无错题可重练")
    quiz = Quiz(
        course_id=course_id,
        chapter_id=None,
        creator_id=user.id,
        title="错题重练",
        description="基于错题本自动生成",
        quiz_type=QuizType.WRONG_BOOK.value,
        status=QuizStatus.PUBLISHED.value,
        metadata_json={"generated": True, "source": "wrong_book", "source_question_map": {}},
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    total_score = 0.0
    source_question_map: dict[str, int] = {}
    for wrong, question in wrong_rows[:10]:
        clone = QuizQuestion(
            quiz_id=quiz.id,
            course_id=question.course_id,
            chapter_id=question.chapter_id,
            knowledge_point_id=question.knowledge_point_id,
            question_type=question.question_type,
            stem=question.stem,
            options=question.options,
            reference_answer=question.reference_answer,
            explanation=question.explanation,
            score=question.score,
            difficulty=question.difficulty,
        )
        total_score += question.score
        db.add(clone)
        db.flush()
        source_question_map[str(clone.id)] = question.id
    quiz.total_score = total_score
    quiz.metadata_json = {"generated": True, "source": "wrong_book", "source_question_map": source_question_map}
    db.add(quiz)
    db.commit()
    return quiz


def get_weak_points(db: Session, *, course_id: int, user: User) -> list[dict]:
    rows = list_wrong_questions(db, course_id=course_id, user=user)
    counter: Counter[str] = Counter()
    for wrong, question in rows:
        if question.knowledge_point_id:
            point = db.get(KnowledgePoint, question.knowledge_point_id)
            counter[point.name if point else "未命名知识点"] += wrong.wrong_count
        else:
            counter["未标注知识点"] += wrong.wrong_count
    return [{"knowledge_point": name, "wrong_count": count} for name, count in counter.most_common(10)]


def create_study_plan(db: Session, *, user: User, payload: StudyPlanCreateRequest) -> tuple[StudyPlan, list[StudyPlanTask]]:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    course = _get_course_or_404(db, payload.course_id)
    plan = StudyPlan(
        user_id=user.id,
        course_id=payload.course_id,
        title=payload.title,
        goal=payload.goal,
        available_days=payload.available_days,
        daily_minutes=payload.daily_minutes,
        summary=f"围绕目标“{payload.goal}”持续 {payload.available_days} 天，每天 {payload.daily_minutes} 分钟。",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    task_payloads = ai_service.generate_study_plan(
        goal=payload.goal,
        available_days=payload.available_days,
        daily_minutes=payload.daily_minutes,
        course_name=course.name,
        db=db,
    )
    tasks: list[StudyPlanTask] = []
    for item in task_payloads:
        task = StudyPlanTask(
            plan_id=plan.id,
            title=item["title"],
            task_date=item["task_date"],
            task_type=item["task_type"],
            estimated_minutes=item["estimated_minutes"],
            metadata_json={"summary": item["summary"]},
        )
        db.add(task)
        tasks.append(task)
    log_ai_usage(
        db,
        module="study_plan",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(payload.goal),
        completion_chars=sum(len(item["title"]) + len(item["summary"]) for item in task_payloads),
    )
    db.commit()
    return plan, tasks


def list_study_plans(db: Session, *, user: User, course_id: int | None = None) -> list[StudyPlan]:
    statement = select(StudyPlan).where(StudyPlan.user_id == user.id)
    if course_id is not None:
        statement = statement.where(StudyPlan.course_id == course_id)
    return list(db.scalars(statement.order_by(StudyPlan.created_at.desc())))


def get_plan_tasks(db: Session, *, plan_id: int, user: User) -> list[StudyPlanTask]:
    plan = db.scalar(select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user.id))
    if plan is None:
        raise not_found("学习计划不存在")
    return list(db.scalars(select(StudyPlanTask).where(StudyPlanTask.plan_id == plan_id).order_by(StudyPlanTask.task_date)))


def checkin_task(db: Session, *, task_id: int, user: User, notes: str | None) -> StudyCheckin:
    task = db.get(StudyPlanTask, task_id)
    if task is None:
        raise not_found("学习任务不存在")
    plan = db.get(StudyPlan, task.plan_id)
    if plan is None or plan.user_id != user.id:
        raise forbidden("无权限打卡该任务")
    task.status = TaskStatus.DONE.value
    checkin = db.scalar(select(StudyCheckin).where(StudyCheckin.task_id == task_id, StudyCheckin.user_id == user.id))
    if checkin is None:
        checkin = StudyCheckin(task_id=task_id, user_id=user.id, notes=notes)
    else:
        checkin.notes = notes
        checkin.checked_in_at = datetime.now(UTC)
    db.add_all([task, checkin])
    db.commit()
    db.refresh(checkin)
    return checkin


def get_learning_records(db: Session, *, course_id: int, user: User) -> dict:
    _assert_student_course_access(db, course_id=course_id, user=user)
    progress_count = db.scalar(
        select(func.count(LearningProgress.id))
        .join(Lesson, Lesson.id == LearningProgress.lesson_id)
        .where(LearningProgress.user_id == user.id, Lesson.course_id == course_id)
    )
    qa_count = db.scalar(select(func.count(QARecord.id)).where(QARecord.user_id == user.id, QARecord.course_id == course_id))
    problem_count = db.scalar(
        select(func.count(ProblemRecord.id)).where(ProblemRecord.user_id == user.id, ProblemRecord.course_id == course_id)
    )
    attempt_count = db.scalar(
        select(func.count(QuizAttempt.id))
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.user_id == user.id, Quiz.course_id == course_id)
    )
    progress_rows = list(
        db.execute(
            select(LearningProgress, Lesson)
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(LearningProgress.user_id == user.id, Lesson.course_id == course_id)
            .order_by(LearningProgress.updated_at.desc())
            .limit(10)
        ).all()
    )
    qa_rows = list(
        db.scalars(
            select(QARecord)
            .where(QARecord.user_id == user.id, QARecord.course_id == course_id)
            .order_by(QARecord.created_at.desc())
            .limit(10)
        )
    )
    problem_rows = list(
        db.scalars(
            select(ProblemRecord)
            .where(ProblemRecord.user_id == user.id, ProblemRecord.course_id == course_id)
            .order_by(ProblemRecord.created_at.desc())
            .limit(10)
        )
    )
    attempt_rows = list(
        db.execute(
            select(QuizAttempt, Quiz)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(QuizAttempt.user_id == user.id, Quiz.course_id == course_id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(10)
        ).all()
    )
    return {
        "progress_count": int(progress_count or 0),
        "qa_count": int(qa_count or 0),
        "problem_count": int(problem_count or 0),
        "attempt_count": int(attempt_count or 0),
        "recent_progress": [
            {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "current_page": progress.current_page,
                "progress_percent": progress.progress_percent,
                "total_study_seconds": progress.total_study_seconds,
                "updated_at": progress.updated_at,
            }
            for progress, lesson in progress_rows
        ],
        "recent_qa": [
            {
                "id": record.id,
                "question": record.question,
                "answer": record.answer,
                "is_favorite": record.is_favorite,
                "created_at": record.created_at,
            }
            for record in qa_rows
        ],
        "recent_problems": [
            {
                "id": record.id,
                "source_type": record.source_type,
                "text": record.corrected_text or record.ocr_text or record.raw_text,
                "knowledge_points": record.knowledge_points or [],
                "created_at": record.created_at,
            }
            for record in problem_rows
        ],
        "recent_attempts": [
            {
                "attempt_id": attempt.id,
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                "score": attempt.score,
                "total_score": attempt.total_score,
                "accuracy": attempt.accuracy,
                "created_at": attempt.created_at,
            }
            for attempt, quiz in attempt_rows
        ],
    }
