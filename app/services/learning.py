from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ProcessStatus, QuizStatus, QuizType, QuestionType, TaskStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import (
    AsyncTaskLog,
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
from app.schemas.learning import QuizEditRequest, QuizGenerateRequest, StudyPlanCreateRequest, WeakQuizGenerateRequest
from app.services.ai import ai_service, sanitize_quiz_source_text
from app.services.courses import _assert_course_owner, _get_course_or_404
from app.services.knowledge import ensure_knowledge_points
from app.services.learning_signals import learning_signal_point_stats
from app.services.notifications import push_user_notification
from app.services.pedagogy import quiz_artifact_source_text
from app.services.usage import log_ai_usage


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内使用该功能")


def _student_course_scope(db: Session, *, user: User, course_id: int | None) -> int | None:
    if course_id is not None:
        _assert_student_course_access(db, course_id=course_id, user=user)
        return course_id
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    course_ids = list(db.scalars(select(CourseMembership.course_id).where(CourseMembership.user_id == user.id).limit(2)))
    return course_ids[0] if len(course_ids) == 1 else None


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
QUIZ_SOURCE_PIECE_LIMIT = 3000
QUIZ_SOURCE_CONTEXT_HARD_LIMIT = 80000


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
    if isinstance(value, str):
        text = "\n".join(" ".join(line.split()) for line in value.splitlines())
    else:
        text = " ".join(str(value).split())
    return [text] if text else []


def _append_source_piece(pieces: list[str], seen: set[str], value, *, limit: int = 1400) -> None:
    for text in _flatten_text(value):
        if not text or any(marker in text for marker in _PLACEHOLDER_SOURCE_TEXT):
            continue
        compact = sanitize_quiz_source_text(text)
        if not compact:
            continue
        if len(compact) > limit:
            compact = _truncate_source_piece(compact, limit)
        fingerprint = compact[:220]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        pieces.append(compact)


def _append_long_source_pieces(
    pieces: list[str],
    seen: set[str],
    title: str,
    text: str | None,
    *,
    window: int = QUIZ_SOURCE_PIECE_LIMIT,
) -> None:
    compact = sanitize_quiz_source_text(text or "")
    if not compact or any(marker in compact for marker in _PLACEHOLDER_SOURCE_TEXT):
        return
    if len(compact) <= window:
        _append_source_piece(pieces, seen, f"{title}\n{compact}", limit=window + 240)
        return
    total = (len(compact) + window - 1) // window
    for index, start in enumerate(range(0, len(compact), window), start=1):
        excerpt = compact[start : start + window]
        _append_source_piece(pieces, seen, f"{title}（全文片段{index}/{total}）\n{excerpt}", limit=window + 260)


def _join_source_pieces_for_quiz(pieces: list[str]) -> str:
    pieces = [piece for piece in pieces if piece.strip()]
    if not pieces:
        return ""
    joined = "\n\n".join(pieces)
    if len(joined) <= QUIZ_SOURCE_CONTEXT_HARD_LIMIT:
        return joined
    separator_chars = 2 * max(len(pieces) - 1, 0)
    per_piece_limit = max(1, (QUIZ_SOURCE_CONTEXT_HARD_LIMIT - separator_chars) // len(pieces))
    compressed = [_truncate_source_piece(piece, per_piece_limit) for piece in pieces]
    return "\n\n".join(compressed)


def _truncate_source_piece(piece: str, limit: int) -> str:
    if len(piece) <= limit:
        return piece
    if limit <= 0:
        return ""
    if "\n" not in piece:
        return _sample_text_across_body(piece, limit)
    header, body = piece.split("\n", 1)
    header_limit = min(len(header), max(24, limit // 3))
    body_limit = max(0, limit - header_limit - 1)
    body_excerpt = _sample_text_across_body(body, body_limit)
    return f"{header[:header_limit].rstrip()}\n{body_excerpt}".strip()


def _sample_text_across_body(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    if limit <= 0:
        return ""
    if limit < 80:
        separator = "..."
        available = max(1, limit - len(separator))
        head_limit = max(1, available // 2)
        tail_limit = max(1, available - head_limit)
        return f"{text[:head_limit]}{separator}{text[-tail_limit:]}".strip()

    separator = " ... "
    available = limit - len(separator) * 2
    if available <= 0:
        return text[:limit].rstrip()
    head_limit = max(1, available // 3)
    middle_limit = max(1, available // 3)
    tail_limit = max(1, available - head_limit - middle_limit)
    middle_start = max(head_limit, (len(text) - middle_limit) // 2)
    middle_end = middle_start + middle_limit
    return (
        f"{text[:head_limit].rstrip()}"
        f"{separator}{text[middle_start:middle_end].strip()}"
        f"{separator}{text[-tail_limit:].lstrip()}"
    ).strip()


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
    artifact_text, _artifact_count = quiz_artifact_source_text(db, course_id=course_id, chapter_ids=chapter_ids)
    if artifact_text:
        _append_long_source_pieces(pieces, seen, "结构化教学对象", artifact_text, window=QUIZ_SOURCE_PIECE_LIMIT)

    chunk_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_ids:
        chunk_statement = chunk_statement.where(KnowledgeChunk.chapter_id.in_(chapter_ids))
    chunks = list(db.scalars(chunk_statement.order_by(KnowledgeChunk.id)))
    for chunk in chunks:
        _append_source_piece(pieces, seen, f"{chunk.title}\n{chunk.content}", limit=QUIZ_SOURCE_PIECE_LIMIT)

    page_statement = (
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(Lesson.course_id == course_id)
    )
    if chapter_ids:
        page_statement = page_statement.where(
            or_(Lesson.chapter_id.in_(chapter_ids), CourseMaterial.chapter_id.in_(chapter_ids))
        )
    pages = list(db.execute(page_statement.order_by(Lesson.id, LessonPage.page_number)))
    material_ids_with_pages: set[int] = set()
    for page, lesson, material in pages:
        if lesson.material_id is not None:
            material_ids_with_pages.add(lesson.material_id)
        material_prefix = f"{material.title} - " if material is not None and material.title != lesson.title else ""
        title = page.page_title or f"{lesson.title} 第{page.page_number}页"
        _append_source_piece(
            pieces,
            seen,
            f"{material_prefix}{lesson.title} - {title}\n{page.page_text}",
            limit=QUIZ_SOURCE_PIECE_LIMIT,
        )

    material_statement = select(CourseMaterial).where(
        CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None)
    )
    if chapter_ids:
        material_statement = material_statement.where(CourseMaterial.chapter_id.in_(chapter_ids))
    materials = list(db.scalars(material_statement.order_by(CourseMaterial.created_at.desc())))
    for material in materials:
        if material.id in material_ids_with_pages:
            continue
        _append_long_source_pieces(pieces, seen, material.title, material.extracted_text, window=QUIZ_SOURCE_PIECE_LIMIT)

    _knowledge_text_for_quiz(points, pieces=pieces, seen=seen)
    return _join_source_pieces_for_quiz(pieces)


def _course_context_text_for_quiz(*, course, points: list[KnowledgePoint]) -> str:
    pieces = [f"课程名称：{course.name}"]
    if getattr(course, "description", None):
        pieces.append(f"课程简介：{course.description}")
    point_names = [point.name for point in points if point.name]
    if point_names:
        pieces.append(f"相关知识点：{'、'.join(dict.fromkeys(point_names[:12]))}")
    return "\n".join(pieces)


def _quiz_topic_for_generation(*, course_name: str, points: list[KnowledgePoint], source_text: str) -> str:
    names = [point.name for point in points if point.name and "练习" not in point.name and "测验" not in point.name]
    if names:
        return "、".join(dict.fromkeys(names[:4]))
    if source_text.startswith("课程名称："):
        return course_name
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


def _knowledge_points_by_ids(db: Session, *, course_id: int, point_ids: list[int]) -> list[KnowledgePoint]:
    unique_ids = list(dict.fromkeys(int(point_id) for point_id in point_ids if int(point_id or 0) > 0))
    if not unique_ids:
        return []
    points = list(
        db.scalars(
            select(KnowledgePoint)
            .where(KnowledgePoint.course_id == course_id, KnowledgePoint.id.in_(unique_ids))
        )
    )
    by_id = {point.id: point for point in points}
    if len(by_id) != len(unique_ids):
        raise bad_request("知识点不属于当前课程")
    return [by_id[point_id] for point_id in unique_ids]


def _normalize_question_type_counts(raw: dict[str, int] | None) -> dict[str, int] | None:
    if not raw:
        return None
    allowed = {
        QuestionType.SINGLE_CHOICE.value,
        QuestionType.MULTIPLE_CHOICE.value,
        QuestionType.JUDGE.value,
        QuestionType.BLANK.value,
        QuestionType.SHORT_ANSWER.value,
    }
    normalized: dict[str, int] = {}
    for question_type, value in raw.items():
        if question_type not in allowed:
            raise bad_request("题型不合法")
        count = int(value or 0)
        if count < 0:
            raise bad_request("题型数量不能为负数")
        if count:
            normalized[question_type] = count
    return normalized or None


def _combined_weak_point_stats_by_id(
    db: Session,
    *,
    course_id: int,
    user: User,
    point_ids: list[int] | None = None,
) -> dict[int, dict[str, float | int]]:
    if user.role not in {UserRole.STUDENT.value, UserRole.TEACHER.value, UserRole.ADMIN.value}:
        return {}

    point_id_expr = func.coalesce(WrongQuestion.knowledge_point_id, QuizQuestion.knowledge_point_id)
    statement = (
        select(point_id_expr.label("point_id"), func.sum(WrongQuestion.wrong_count))
        .select_from(WrongQuestion)
        .outerjoin(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
        .where(WrongQuestion.course_id == course_id, point_id_expr.is_not(None))
        .group_by(point_id_expr)
    )
    if user.role == UserRole.STUDENT.value:
        statement = statement.where(WrongQuestion.user_id == user.id)
    if point_ids:
        statement = statement.where(point_id_expr.in_(point_ids))

    stats: dict[int, dict[str, float | int]] = {}
    for point_id, wrong_count in db.execute(statement):
        if point_id is None:
            continue
        stats[int(point_id)] = {
            "wrong_count": int(wrong_count or 0),
            "learning_signal_count": 0,
            "qa_signal_count": 0,
            "signal_score": 0.0,
            "weak_score": float(wrong_count or 0),
        }

    signal_stats = learning_signal_point_stats(
        db,
        course_id=course_id,
        user_id=user.id if user.role == UserRole.STUDENT.value else None,
        point_ids=point_ids,
    )
    for point_id, signal in signal_stats.items():
        entry = stats.setdefault(
            point_id,
            {
                "wrong_count": 0,
                "learning_signal_count": 0,
                "qa_signal_count": 0,
                "signal_score": 0.0,
                "weak_score": 0.0,
            },
        )
        entry["learning_signal_count"] = int(signal.get("learning_signal_count") or 0)
        entry["qa_signal_count"] = int(signal.get("qa_signal_count") or 0)
        entry["signal_score"] = float(signal.get("signal_score") or 0)
        entry["weak_score"] = round(float(entry.get("wrong_count") or 0) + float(entry["signal_score"]), 2)
    return stats


def _prioritize_weak_points(db: Session, *, points: list[KnowledgePoint], course_id: int, user: User, enabled: bool) -> list[KnowledgePoint]:
    if not enabled or not points:
        return points
    stats = _combined_weak_point_stats_by_id(db, course_id=course_id, user=user, point_ids=[point.id for point in points])
    weak_ids = [
        point_id
        for point_id, item in sorted(
            stats.items(),
            key=lambda pair: (-float(pair[1].get("weak_score") or 0), -int(pair[1].get("wrong_count") or 0), pair[0]),
        )
        if float(item.get("weak_score") or 0) > 0
    ]
    if not weak_ids:
        return points
    weak_rank = {point_id: index for index, point_id in enumerate(weak_ids)}
    return sorted(points, key=lambda point: (weak_rank.get(point.id, len(weak_rank)), point.id))


def _validate_quiz_generation_request(db: Session, *, user: User, payload: QuizGenerateRequest):
    course = _get_course_or_404(db, payload.course_id)
    if payload.quiz_type not in {item.value for item in QuizType}:
        raise bad_request("测验类型不合法")
    question_type_counts = _normalize_question_type_counts(payload.question_type_counts)
    if question_type_counts and sum(question_type_counts.values()) != payload.question_count:
        raise bad_request("题型数量合计必须等于总题量")
    if user.role == UserRole.STUDENT.value and payload.quiz_type == QuizType.COURSE.value:
        raise forbidden("学生不能直接生成课程测验")
    if user.role == UserRole.TEACHER.value:
        _assert_course_owner(course, user, require_active=True)
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=payload.course_id, user=user)
    return course, question_type_counts


def _quiz_generation_task_detail(*, user: User, course, payload: dict, kind: str, title: str) -> dict:
    return {
        "kind": kind,
        "user_id": user.id,
        "user_role": user.role,
        "course_id": course.id,
        "course_name": course.name,
        "title": title,
        "payload": payload,
    }


def _dispatch_quiz_generation(task_id: int) -> bool:
    from app.tasks.quizzes import process_quiz_generation_task

    try:
        process_quiz_generation_task.delay(task_id)
        return True
    except Exception:
        return False


def _mark_quiz_task_dispatch_failed(db: Session, task: AsyncTaskLog) -> None:
    db.refresh(task)
    if task.status not in {ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value}:
        return
    detail = task.detail if isinstance(task.detail, dict) else {}
    task.status = ProcessStatus.FAILED.value
    task.detail = {**detail, "error": "quiz_generation_dispatch_failed", "failed_at": datetime.now(UTC).isoformat()}
    db.add(task)
    db.commit()
    db.refresh(task)


def enqueue_quiz_generation(db: Session, *, user: User, payload: QuizGenerateRequest) -> AsyncTaskLog:
    course, question_type_counts = _validate_quiz_generation_request(db, user=user, payload=payload)
    task = AsyncTaskLog(
        task_name="quiz.generate",
        target_type="quiz",
        target_id=None,
        status=ProcessStatus.PENDING.value,
        detail=_quiz_generation_task_detail(
            user=user,
            course=course,
            payload={**payload.model_dump(mode="json"), "question_type_counts": question_type_counts},
            kind="quiz",
            title=payload.title,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if not _dispatch_quiz_generation(task.id):
        _mark_quiz_task_dispatch_failed(db, task)
    db.refresh(task)
    return task


def generate_quiz(db: Session, *, user: User, payload: QuizGenerateRequest) -> Quiz:
    course, question_type_counts = _validate_quiz_generation_request(db, user=user, payload=payload)
    chapter_ids = _chapter_ids_for_quiz(payload)
    points = (
        _knowledge_points_by_ids(db, course_id=payload.course_id, point_ids=payload.knowledge_point_ids)
        if payload.knowledge_point_ids
        else _knowledge_points_for_quiz(db, course_id=payload.course_id, chapter_ids=chapter_ids)
    )
    points = _prioritize_weak_points(
        db,
        points=points,
        course_id=payload.course_id,
        user=user,
        enabled=payload.prefer_weak_points,
    )
    source_text = _course_source_text_for_quiz(db, course_id=payload.course_id, chapter_ids=chapter_ids, points=points)
    _artifact_text, pedagogy_artifact_count = quiz_artifact_source_text(db, course_id=payload.course_id, chapter_ids=chapter_ids)
    if not source_text.strip():
        source_text = _course_context_text_for_quiz(course=course, points=points)
    quiz_topic = _quiz_topic_for_generation(course_name=course.name, points=points, source_text=source_text)
    question_kwargs = {
        "topic": quiz_topic,
        "source_text": source_text,
        "count": payload.question_count,
        "db": db,
    }
    if question_type_counts:
        question_kwargs["type_counts"] = question_type_counts
    question_dicts = ai_service.generate_quiz_questions(**question_kwargs)
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
            "knowledge_point_ids": [point.id for point in points],
            "knowledge_point_names": [point.name for point in points],
            "question_type_counts": question_type_counts,
            "prefer_weak_points": payload.prefer_weak_points,
            "source_topic": quiz_topic,
            "source_chars": len(source_text),
            "pedagogy_artifact_count": pedagogy_artifact_count,
        },
        total_score=0,
    )
    db.add(quiz)
    db.flush()
    db.refresh(quiz)
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
    _assert_course_owner(course, user, require_active=True)
    quiz.status = QuizStatus.PUBLISHED.value
    quiz.published_at = datetime.now(UTC)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _assert_quiz_teacher_access(db: Session, *, quiz: Quiz, user: User, require_active: bool = False) -> None:
    course = _get_course_or_404(db, quiz.course_id)
    _assert_course_owner(course, user, require_active=require_active)


def _validate_reference_answer(question_type: str, reference_answer) -> None:
    if reference_answer is None or reference_answer == "":
        raise bad_request("题目必须设置正确答案")
    if question_type in {QuestionType.SINGLE_CHOICE.value, QuestionType.MULTIPLE_CHOICE.value}:
        value = extract_reference_answer_value(reference_answer)
        values = _answer_values(value)
        if not values:
            raise bad_request("选择题必须设置正确选项")


def _validate_question_payload(item) -> tuple[list | None, object]:
    question_type = item.question_type
    if question_type not in {value.value for value in QuestionType}:
        raise bad_request("题型不合法")
    options = item.options
    if question_type in {QuestionType.SINGLE_CHOICE.value, QuestionType.MULTIPLE_CHOICE.value}:
        options = [str(option).strip() for option in (options or []) if str(option).strip()]
        if len(options) < 2:
            raise bad_request("选择题至少需要 2 个选项")
    elif question_type == QuestionType.JUDGE.value:
        options = options or ["正确", "错误"]
    _validate_reference_answer(question_type, item.reference_answer)
    return options, item.reference_answer


def update_quiz_content(db: Session, *, quiz_id: int, user: User, payload: QuizEditRequest) -> tuple[Quiz, list[QuizQuestion]]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    _assert_quiz_teacher_access(db, quiz=quiz, user=user, require_active=True)
    existing_questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.id)))
    existing_by_id = {item.id: item for item in existing_questions}
    seen_ids: set[int] = set()
    quiz.title = payload.title.strip()
    quiz.description = payload.description.strip() if payload.description else None
    total_score = 0.0
    for item in payload.questions:
        options, reference_answer = _validate_question_payload(item)
        if item.id:
            question = existing_by_id.get(item.id)
            if question is None:
                raise bad_request("题目不属于当前测验")
            seen_ids.add(question.id)
        else:
            question = QuizQuestion(
                quiz_id=quiz.id,
                course_id=quiz.course_id,
                chapter_id=quiz.chapter_id,
                stem=item.stem.strip(),
            )
            db.add(question)
            db.flush()
            seen_ids.add(question.id)
        question.chapter_id = item.chapter_id if item.chapter_id is not None else quiz.chapter_id
        question.knowledge_point_id = item.knowledge_point_id
        question.question_type = item.question_type
        question.stem = item.stem.strip()
        question.options = options
        question.reference_answer = reference_answer
        question.explanation = item.explanation.strip() if item.explanation else None
        question.score = float(item.score)
        question.difficulty = item.difficulty or "standard"
        total_score += float(question.score)
        db.add(question)
    for question in existing_questions:
        if question.id not in seen_ids:
            db.delete(question)
    quiz.total_score = round(total_score, 2)
    metadata = quiz.metadata_json if isinstance(quiz.metadata_json, dict) else {}
    quiz.metadata_json = {**metadata, "edited": True, "edited_at": datetime.now(UTC).isoformat()}
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.id)))
    return quiz, questions


# 错题重练 / 自助练习等学生私有练习类 quiz：即便 PUBLISHED 也仅创建者本人可见/访问。
# #46：PRACTICE 是学生最常自建的练习类型，同样不得被同课程其他学生按 id 探知。
_STUDENT_PRIVATE_QUIZ_TYPES = {QuizType.WRONG_BOOK.value, QuizType.PRACTICE.value}


def _is_student_private_quiz(quiz: Quiz) -> bool:
    return quiz.quiz_type in _STUDENT_PRIVATE_QUIZ_TYPES


def list_quizzes(db: Session, *, course_id: int, user: User) -> list[Quiz]:
    statement = select(Quiz).where(Quiz.course_id == course_id)
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=course_id, user=user)
        statement = statement.where(
            (
                (Quiz.status == QuizStatus.PUBLISHED.value)
                & (Quiz.quiz_type.not_in(_STUDENT_PRIVATE_QUIZ_TYPES))
            )
            | ((Quiz.creator_id == user.id) & (Quiz.quiz_type != QuizType.COURSE.value))
        )
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, course_id)
        _assert_course_owner(course, user)
    return list(db.scalars(statement.order_by(Quiz.created_at.desc())))


def quiz_attempt_summary(db: Session, attempt: QuizAttempt) -> dict:
    total_count = int(db.scalar(select(func.count(QuizAnswer.id)).where(QuizAnswer.attempt_id == attempt.id)) or 0)
    correct_count = int(
        db.scalar(
            select(func.count(QuizAnswer.id)).where(
                QuizAnswer.attempt_id == attempt.id,
                QuizAnswer.is_correct.is_(True),
            )
        )
        or 0
    )
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "user_id": attempt.user_id,
        "score": attempt.score,
        "total_score": attempt.total_score,
        "accuracy": attempt.accuracy,
        "correct_count": correct_count,
        "total_count": total_count,
        "ai_feedback": attempt.ai_feedback,
        "submitted_at": attempt.submitted_at,
        "created_at": attempt.created_at,
        "updated_at": attempt.updated_at,
    }


def list_student_quiz_attempts(db: Session, *, quiz_id: int, user: User) -> list[QuizAttempt]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可查看自己的作答记录")
    _assert_student_course_access(db, course_id=quiz.course_id, user=user)
    return list(
        db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
            .order_by(QuizAttempt.submitted_at.desc(), QuizAttempt.created_at.desc())
        )
    )


def get_student_quiz_attempt(db: Session, *, attempt_id: int, user: User) -> QuizAttempt:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise not_found("作答记录不存在")
    if user.role != UserRole.STUDENT.value or attempt.user_id != user.id:
        raise forbidden("仅可查看自己的作答记录")
    quiz = db.get(Quiz, attempt.quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    _assert_student_course_access(db, course_id=quiz.course_id, user=user)
    return attempt


def _assert_teacher_course_access(db: Session, *, course_id: int, user: User, require_active: bool = False):
    course = _get_course_or_404(db, course_id)
    if user.role == UserRole.ADMIN.value:
        return course
    if user.role != UserRole.TEACHER.value:
        raise forbidden("仅教师可管理薄弱题目")
    _assert_course_owner(course, user, require_active=require_active)
    return course


def _weak_point_rows(db: Session, *, course_id: int) -> list[dict]:
    rows = db.execute(
        select(
            KnowledgePoint.id,
            KnowledgePoint.name,
            KnowledgePoint.description,
            func.sum(WrongQuestion.wrong_count),
            func.count(func.distinct(WrongQuestion.user_id)),
            func.max(WrongQuestion.updated_at),
        )
        .join(WrongQuestion, WrongQuestion.knowledge_point_id == KnowledgePoint.id)
        .where(WrongQuestion.course_id == course_id, KnowledgePoint.course_id == course_id)
        .group_by(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.description)
        .order_by(func.sum(WrongQuestion.wrong_count).desc(), KnowledgePoint.id.asc())
    )
    return [
        {
            "knowledge_point_id": point_id,
            "knowledge_point": name,
            "description": description,
            "wrong_count": int(wrong_count or 0),
            "student_count": int(student_count or 0),
            "last_wrong_at": last_wrong_at,
        }
        for point_id, name, description, wrong_count, student_count, last_wrong_at in rows
    ]


def _quiz_question_type_counts(db: Session, quiz_id: int) -> dict[str, int]:
    rows = db.execute(
        select(QuizQuestion.question_type, func.count(QuizQuestion.id))
        .where(QuizQuestion.quiz_id == quiz_id)
        .group_by(QuizQuestion.question_type)
    )
    return {question_type: int(count or 0) for question_type, count in rows}


def _weak_quiz_summary(db: Session, quiz: Quiz) -> dict:
    attempt_count = int(db.scalar(select(func.count(QuizAttempt.id)).where(QuizAttempt.quiz_id == quiz.id)) or 0)
    avg_score = db.scalar(select(func.avg(QuizAttempt.score)).where(QuizAttempt.quiz_id == quiz.id))
    avg_accuracy = db.scalar(select(func.avg(QuizAttempt.accuracy)).where(QuizAttempt.quiz_id == quiz.id))
    last_attempt_at = db.scalar(select(func.max(QuizAttempt.submitted_at)).where(QuizAttempt.quiz_id == quiz.id))
    question_count = int(db.scalar(select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)) or 0)
    metadata = quiz.metadata_json if isinstance(quiz.metadata_json, dict) else {}
    return {
        "id": quiz.id,
        "course_id": quiz.course_id,
        "chapter_id": quiz.chapter_id,
        "creator_id": quiz.creator_id,
        "title": quiz.title,
        "description": quiz.description,
        "quiz_type": quiz.quiz_type,
        "status": quiz.status,
        "total_score": quiz.total_score,
        "metadata_json": metadata,
        "published_at": quiz.published_at,
        "created_at": quiz.created_at,
        "updated_at": quiz.updated_at,
        "question_count": question_count,
        "question_type_counts": _quiz_question_type_counts(db, quiz.id),
        "attempt_count": attempt_count,
        "average_score": round(float(avg_score or 0), 2),
        "average_accuracy": round(float(avg_accuracy or 0), 2),
        "last_attempt_at": last_attempt_at,
    }


def list_teacher_weak_quizzes(db: Session, *, course_id: int, user: User) -> dict:
    _assert_teacher_course_access(db, course_id=course_id, user=user)
    weak_points = _weak_point_rows(db, course_id=course_id)
    weak_by_id = {item["knowledge_point_id"]: {**item, "quiz_sets": []} for item in weak_points}
    all_sets: list[dict] = []
    quizzes = list(db.scalars(select(Quiz).where(Quiz.course_id == course_id).order_by(Quiz.created_at.desc())))
    for quiz in quizzes:
        metadata = quiz.metadata_json if isinstance(quiz.metadata_json, dict) else {}
        if not metadata.get("weak_quiz"):
            continue
        summary = _weak_quiz_summary(db, quiz)
        scope = metadata.get("weak_quiz_scope")
        point_ids = [int(point_id) for point_id in metadata.get("weak_point_ids", []) if str(point_id).isdigit()]
        if scope == "all":
            all_sets.append(summary)
            continue
        for point_id in point_ids:
            if point_id in weak_by_id:
                weak_by_id[point_id]["quiz_sets"].append(summary)
    return {
        "weak_points": list(weak_by_id.values()),
        "all_sets": all_sets,
        "stats": {
            "weak_point_count": len(weak_points),
            "quiz_set_count": len(all_sets) + sum(len(item["quiz_sets"]) for item in weak_by_id.values()),
            "wrong_count": sum(item["wrong_count"] for item in weak_points),
        },
    }


def generate_teacher_weak_quiz(db: Session, *, user: User, payload: WeakQuizGenerateRequest) -> Quiz:
    course = _assert_teacher_course_access(db, course_id=payload.course_id, user=user, require_active=True)
    if payload.weak_point_id:
        point_ids = [payload.weak_point_id]
        scope = "single"
    elif payload.weak_point_ids:
        point_ids = list(dict.fromkeys(payload.weak_point_ids))
        scope = "all" if payload.all_weak_points or len(point_ids) > 1 else "single"
    else:
        point_ids = [item["knowledge_point_id"] for item in _weak_point_rows(db, course_id=payload.course_id)]
        scope = "all"
    points = _knowledge_points_by_ids(db, course_id=payload.course_id, point_ids=point_ids)
    if not points:
        raise bad_request("暂无可生成题目的薄弱知识点")
    type_counts = _normalize_question_type_counts(payload.question_type_counts)
    if type_counts and sum(type_counts.values()) != payload.question_count:
        raise bad_request("题型数量合计必须等于总题量")
    title = payload.title or (
        f"{points[0].name}薄弱点专项测验" if scope == "single" and len(points) == 1 else "薄弱知识点综合测验"
    )
    quiz = generate_quiz(
        db,
        user=user,
        payload=QuizGenerateRequest(
            course_id=payload.course_id,
            title=title,
            quiz_type=QuizType.COURSE.value,
            question_count=payload.question_count,
            question_type_counts=type_counts,
            prefer_weak_points=True,
            knowledge_point_ids=[point.id for point in points],
        ),
    )
    metadata = quiz.metadata_json if isinstance(quiz.metadata_json, dict) else {}
    quiz.metadata_json = {
        **metadata,
        "weak_quiz": True,
        "weak_quiz_scope": scope,
        "weak_point_ids": [point.id for point in points],
        "weak_point_names": [point.name for point in points],
        "course_name": course.name,
    }
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def enqueue_teacher_weak_quiz(db: Session, *, user: User, payload: WeakQuizGenerateRequest) -> AsyncTaskLog:
    course = _assert_teacher_course_access(db, course_id=payload.course_id, user=user, require_active=True)
    type_counts = _normalize_question_type_counts(payload.question_type_counts)
    if type_counts and sum(type_counts.values()) != payload.question_count:
        raise bad_request("题型数量合计必须等于总题量")
    title = payload.title or ("薄弱知识点综合测验" if payload.all_weak_points else "薄弱点专项测验")
    task = AsyncTaskLog(
        task_name="quiz.teacher_weak.generate",
        target_type="quiz",
        target_id=None,
        status=ProcessStatus.PENDING.value,
        detail=_quiz_generation_task_detail(
            user=user,
            course=course,
            payload={**payload.model_dump(mode="json"), "question_type_counts": type_counts},
            kind="teacher_weak_quiz",
            title=title,
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if not _dispatch_quiz_generation(task.id):
        _mark_quiz_task_dispatch_failed(db, task)
    db.refresh(task)
    return task


def get_teacher_quiz_attempts(db: Session, *, quiz_id: int, user: User) -> dict:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    _assert_teacher_course_access(db, course_id=quiz.course_id, user=user)
    questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.id.asc())))
    question_by_id = {question.id: question for question in questions}
    rows = list(
        db.execute(
            select(QuizAttempt, User)
            .join(User, User.id == QuizAttempt.user_id)
            .where(QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.submitted_at.desc(), QuizAttempt.created_at.desc())
        )
    )
    attempt_ids = [attempt.id for attempt, _student in rows]
    answers_by_attempt: dict[int, list[QuizAnswer]] = {attempt_id: [] for attempt_id in attempt_ids}
    if attempt_ids:
        for answer in db.scalars(select(QuizAnswer).where(QuizAnswer.attempt_id.in_(attempt_ids)).order_by(QuizAnswer.id.asc())):
            answers_by_attempt.setdefault(answer.attempt_id, []).append(answer)
    attempts = []
    for attempt, student in rows:
        answers = answers_by_attempt.get(attempt.id, [])
        correct_count = sum(1 for answer in answers if answer.is_correct)
        attempts.append(
            {
                "id": attempt.id,
                "quiz_id": attempt.quiz_id,
                "user_id": attempt.user_id,
                "student": {
                    "id": student.id,
                    "nickname": student.nickname,
                    "email": student.email,
                    "student_no": student.student_no,
                },
                "score": attempt.score,
                "total_score": attempt.total_score,
                "accuracy": attempt.accuracy,
                "ai_feedback": attempt.ai_feedback,
                "submitted_at": attempt.submitted_at,
                "created_at": attempt.created_at,
                "updated_at": attempt.updated_at,
                "answer_count": len(answers),
                "correct_count": correct_count,
                "answers": [
                    {
                        "id": answer.id,
                        "question_id": answer.question_id,
                        "stem": question_by_id.get(answer.question_id).stem if answer.question_id in question_by_id else "",
                        "question_type": question_by_id.get(answer.question_id).question_type if answer.question_id in question_by_id else "",
                        "user_answer": answer.user_answer,
                        "is_correct": answer.is_correct,
                        "score": answer.score,
                        "feedback": answer.feedback,
                    }
                    for answer in answers
                ],
            }
        )
    return {
        "quiz": _weak_quiz_summary(db, quiz),
        "questions": [
            {
                "id": question.id,
                "question_type": question.question_type,
                "stem": question.stem,
                "score": question.score,
                "difficulty": question.difficulty,
            }
            for question in questions
        ],
        "attempts": attempts,
    }


def get_quiz_detail(db: Session, *, quiz_id: int, user: User) -> tuple[Quiz, list[QuizQuestion]]:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise not_found("测验不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=quiz.course_id, user=user)
        if _is_student_private_quiz(quiz):
            if quiz.creator_id != user.id:
                raise forbidden("测验尚未发布")
        elif quiz.status != QuizStatus.PUBLISHED.value and quiz.creator_id != user.id:
            raise forbidden("测验尚未发布")
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, quiz.course_id)
        _assert_course_owner(course, user)
    questions = list(db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.id)))
    return quiz, questions


def extract_reference_answer_value(reference_answer):
    if isinstance(reference_answer, dict):
        for key in (
            "value",
            "answer",
            "correct_answer",
            "correct",
            "option_index",
            "index",
            "key",
            "text",
            "choice",
            "correct_option",
            "judge",
        ):
            if key in reference_answer:
                return reference_answer[key]
        for key in ("values", "answers", "correct_answers"):
            if key in reference_answer:
                return reference_answer[key]
        for key in ("keywords", "key_points"):
            if key in reference_answer:
                return reference_answer[key]
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
    now = datetime.now(UTC)
    wrong = db.scalar(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user.id,
            WrongQuestion.question_id == source_question_id,
            WrongQuestion.course_id == quiz.course_id,
        )
    )
    if is_correct:
        if wrong is not None:
            wrong.is_resolved = True
            wrong.resolved_at = now
            wrong.last_correct_at = now
            wrong.last_attempt_id = attempt.id
            db.add(wrong)
        return
    if wrong is None:
        wrong = WrongQuestion(
            user_id=user.id,
            question_id=source_question_id,
            course_id=quiz.course_id,
            knowledge_point_id=source_question.knowledge_point_id,
            wrong_count=1,
            last_attempt_id=attempt.id,
            is_resolved=False,
            resolved_at=None,
            last_wrong_at=now,
        )
    else:
        wrong.wrong_count += 1
        wrong.last_attempt_id = attempt.id
        wrong.knowledge_point_id = source_question.knowledge_point_id
        wrong.is_resolved = False
        wrong.resolved_at = None
        wrong.last_wrong_at = now
    db.add(wrong)


# 填空题达到该及格比例即视为通过，不计入错题。
_BLANK_PASS_RATIO = 0.6


def _grade_question(question: QuizQuestion, user_answer, *, db: Session) -> dict:
    """对单题判分，返回 score/is_correct/feedback/count_as_wrong/pending。

    任何会失败的判分（如 AI 主观题评分不可用）都在写库前完成，失败时直接抛出，
    使整次提交不落库（见 #15）。
    """
    is_correct = False
    score = 0.0
    feedback = question.explanation
    pending_review = False
    count_as_wrong = True
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
        expected_values = [item for item in expected_values if item]
        actual_text = str(user_answer or "").lower()
        matched = sum(1 for item in expected_values if item.lower() in actual_text)
        total = len(expected_values)
        is_correct = bool(expected_values) and matched == total
        score = question.score if is_correct else round(question.score * matched / max(total, 1), 2)
        ratio = (matched / total) if total else 0.0
        # #47：给出命中明细，并对达到及格比例的填空题不计入错题。
        if total:
            feedback = f"命中关键词 {matched}/{total}，得 {score}/{question.score} 分。"
            if not is_correct and ratio >= _BLANK_PASS_RATIO:
                feedback += "（达到及格比例，本题不计入错题。）"
                count_as_wrong = False
        else:
            feedback = question.explanation
    else:
        expected_keywords = []
        if isinstance(question.reference_answer, dict):
            expected_keywords = question.reference_answer.get("keywords") or question.reference_answer.get("key_points") or []
        # #28：score 可能为 None，表示无参考关键词且模型未给分，需人工批改。
        raw_score, raw_feedback = ai_service.score_subjective_answer(
            reference_keywords=expected_keywords,
            user_answer=str(user_answer or ""),
            full_score=question.score,
            db=db,
        )
        if raw_score is None:
            pending_review = True
            count_as_wrong = False
            score = 0.0
            is_correct = False
            feedback = (raw_feedback or "").strip() or "该题需教师批改，暂未计入自动总分。"
        else:
            score = float(raw_score)
            feedback = raw_feedback
            is_correct = score >= question.score * 0.6
    return {
        "score": score,
        "is_correct": is_correct,
        "feedback": feedback,
        "pending_review": pending_review,
        "count_as_wrong": count_as_wrong,
    }


def _attempt_ai_feedback(*, score: float, total_score: float, accuracy: float, wrong_count: int, pending_count: int) -> str:
    # 修复 #2：全部题目均为待批改主观题时（无任何已自动判分题），不要套用按正确率分档的文案，
    # 否则会出现"正确率 0%、错题较多（0 道）"的自相矛盾，让学生误以为挂科。
    if total_score <= 0 and pending_count > 0:
        return f"本次共 {pending_count} 道主观题，均需教师批改，待批改完成后给出成绩，请耐心等待。"
    parts: list[str] = [f"系统判分：本次得分 {score}/{total_score}（正确率 {accuracy}%）。"]
    if total_score > 0 and score >= total_score:
        parts.append("全部答对，表现优秀，可挑战更高难度的题目。")
    elif accuracy >= 85:
        parts.append("掌握情况良好，针对个别错题巩固即可。")
    elif accuracy >= 60:
        parts.append(f"还有 {wrong_count} 道错题，建议优先复盘并回看对应知识点。")
    else:
        parts.append(f"错题较多（{wrong_count} 道），建议系统性重学相关知识点后再练习。")
    if pending_count:
        parts.append(f"另有 {pending_count} 道主观题待教师批改，最终成绩以教师批改为准。")
    return "".join(parts)


def submit_quiz(db: Session, *, quiz_id: int, user: User, answers: list[dict]) -> QuizAttempt:
    quiz, questions = get_quiz_detail(db, quiz_id=quiz_id, user=user)
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可提交测验")
    # #14：创建 attempt 前查重拦截，避免 TOCTOU 重复提交、重复计入错题。
    existing_attempt = db.scalar(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.submitted_at.desc(), QuizAttempt.created_at.desc())
    )
    if existing_attempt is not None:
        raise bad_request("该测验已提交，每名学生只能作答一次，请在练习记录中查看解析。")
    answer_map = _answer_map(answers)
    # #15：先把全部判分（含 AI 主观题评分）算完，失败直接抛出，整次提交不落库、不留孤儿。
    graded: list[tuple[QuizQuestion, object, dict]] = []
    try:
        for question in questions:
            user_answer = answer_map.get(question.id)
            graded.append((question, user_answer, _grade_question(question, user_answer, db=db)))
    except Exception:
        db.rollback()
        raise
    total_score = 0.0
    # #M7：正确率/总分分母只统计"已自动判分"的题，排除待人工批改(pending)的主观题，
    # 否则其满分会永久压低正确率。graded_full_score 即已判分题的满分之和。
    graded_full_score = 0.0
    wrong_count = 0
    pending_count = 0
    attempt = QuizAttempt(quiz_id=quiz_id, user_id=user.id, total_score=quiz.total_score, submitted_at=datetime.now(UTC))
    db.add(attempt)
    db.flush()
    db.refresh(attempt)
    for question, user_answer, result in graded:
        if result["pending_review"]:
            # #M7：pending(score is None)的主观题既不计入得分，也不计入满分分母，待教师批改。
            pending_count += 1
        else:
            total_score += float(result["score"])
            graded_full_score += float(question.score)
        db.add(
            QuizAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                user_answer=user_answer,
                is_correct=result["is_correct"],
                score=result["score"],
                feedback=result["feedback"],
                pending_review=bool(result["pending_review"]),
            )
        )
        # #47/#28：达到及格比例的填空题、待人工批改的主观题不计入错题，也不进/出错题本。
        if result["count_as_wrong"]:
            if not result["is_correct"]:
                wrong_count += 1
            _record_answer_to_wrong_book(db, user=user, quiz=quiz, question=question, attempt=attempt, is_correct=result["is_correct"])
    attempt.score = round(total_score, 2)
    # #M7：正确率/总分以"已判分题满分(graded_full_score)"为分母，pending 题不计入，
    # 避免主观题待批改期间正确率被永久低估；若全部题目都待批改则分母兜底为 1 防除零。
    attempt.accuracy = round((total_score / max(graded_full_score, 1)) * 100, 2)
    # 展示口径一致(修复 #3)：persisted total_score 也用 graded 分母，保证 score/total_score
    # 的比例与 accuracy 一致（含 pending 时不再出现"30/100 却显示 75%"的矛盾）。
    attempt.total_score = round(graded_full_score, 2)
    attempt.ai_feedback = _attempt_ai_feedback(
        score=attempt.score,
        total_score=round(graded_full_score, 2),
        accuracy=attempt.accuracy,
        wrong_count=wrong_count,
        pending_count=pending_count,
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        # #14 兜底：并发下唯一约束/竞态导致重复 attempt，回滚并提示已提交。
        db.rollback()
        raise bad_request("该测验已提交，每名学生只能作答一次，请在练习记录中查看解析。")
    db.refresh(attempt)
    return attempt


def list_wrong_questions(db: Session, *, course_id: int, user: User) -> list[tuple[WrongQuestion, QuizQuestion]]:
    _assert_student_course_access(db, course_id=course_id, user=user)
    rows = list(
        db.execute(
            select(WrongQuestion, QuizQuestion)
            .join(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
            .where(
                WrongQuestion.user_id == user.id,
                WrongQuestion.course_id == course_id,
                QuizQuestion.course_id == course_id,
            )
            .order_by(WrongQuestion.updated_at.desc())
        ).all()
    )
    return rows


def generate_wrong_book_practice(db: Session, *, course_id: int, user: User, wrong_question_id: int | None = None) -> Quiz:
    wrong_rows = list_wrong_questions(db, course_id=course_id, user=user)
    if not wrong_rows:
        raise bad_request("暂无错题可重练")
    active_wrong_rows = [(wrong, question) for wrong, question in wrong_rows if not wrong.is_resolved]
    practice_rows = active_wrong_rows or wrong_rows
    # #64：若指定了 wrong_question_id 且属于本课程本人，则确保其被纳入并排在首位，其余按原逻辑补足到上限。
    if wrong_question_id is not None:
        targeted = next((row for row in wrong_rows if row[0].id == wrong_question_id), None)
        if targeted is not None:
            practice_rows = [targeted] + [row for row in practice_rows if row[0].id != targeted[0].id]
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
    for wrong, question in practice_rows[:10]:
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


def enqueue_wrong_book_practice(db: Session, *, course_id: int, user: User, wrong_question_id: int | None = None) -> AsyncTaskLog:
    wrong_rows = list_wrong_questions(db, course_id=course_id, user=user)
    if not wrong_rows:
        raise bad_request("暂无错题可重练")
    course = _get_course_or_404(db, course_id)
    # #64：把定向重练的 wrong_question_id 透传到异步任务 payload。
    payload: dict = {"course_id": course_id}
    if wrong_question_id is not None:
        payload["wrong_question_id"] = wrong_question_id
    task = AsyncTaskLog(
        task_name="quiz.wrong_book.generate",
        target_type="quiz",
        target_id=None,
        status=ProcessStatus.PENDING.value,
        detail=_quiz_generation_task_detail(
            user=user,
            course=course,
            payload=payload,
            kind="wrong_book_practice",
            title="错题重练",
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if not _dispatch_quiz_generation(task.id):
        _mark_quiz_task_dispatch_failed(db, task)
    db.refresh(task)
    return task


def _quiz_generation_success_title(*, user: User, quiz: Quiz, kind: str) -> tuple[str, str]:
    if kind == "teacher_weak_quiz":
        return f"薄弱题目生成完成：{quiz.title}", "题目已进入待审核状态，请检查后发布。"
    if kind == "wrong_book_practice":
        return f"错题重练已生成：{quiz.title}", "新的错题重练已准备好，可以开始练习。"
    if user.role == UserRole.TEACHER.value:
        return f"题目生成完成：{quiz.title}", "测验已进入待审核状态，请检查后发布。"
    return f"练习题已生成：{quiz.title}", "新的练习题已准备好，可以开始练习。"


def _quiz_generation_failure_title(*, kind: str, title: str) -> tuple[str, str]:
    prefix = "薄弱题目" if kind == "teacher_weak_quiz" else "错题重练" if kind == "wrong_book_practice" else "题目"
    return f"{prefix}生成失败：{title}", "AI 生成任务失败，请稍后重试或联系管理员检查模型配置。"


def process_quiz_generation_task(db: Session, task_id: int) -> None:
    task = db.get(AsyncTaskLog, task_id)
    if task is None:
        return
    detail = task.detail if isinstance(task.detail, dict) else {}
    kind = str(detail.get("kind") or "quiz")
    user = db.get(User, int(detail.get("user_id") or 0))
    if user is None:
        task.status = ProcessStatus.FAILED.value
        task.detail = {**detail, "error": "user_not_found"}
        db.add(task)
        db.commit()
        return
    task.status = ProcessStatus.PROCESSING.value
    task.detail = {**detail, "started_at": datetime.now(UTC).isoformat()}
    db.add(task)
    db.commit()
    try:
        payload_data = detail.get("payload") if isinstance(detail.get("payload"), dict) else {}
        if kind == "teacher_weak_quiz":
            quiz = generate_teacher_weak_quiz(db, user=user, payload=WeakQuizGenerateRequest(**payload_data))
        elif kind == "wrong_book_practice":
            raw_wrong_question_id = payload_data.get("wrong_question_id")
            wrong_question_id = int(raw_wrong_question_id) if raw_wrong_question_id is not None else None
            quiz = generate_wrong_book_practice(
                db,
                course_id=int(payload_data.get("course_id") or detail.get("course_id")),
                user=user,
                wrong_question_id=wrong_question_id,
            )
        else:
            quiz = generate_quiz(db, user=user, payload=QuizGenerateRequest(**payload_data))
        question_count = int(db.scalar(select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)) or 0)
        task = db.get(AsyncTaskLog, task_id)
        if task is None:
            return
        title, message = _quiz_generation_success_title(user=user, quiz=quiz, kind=kind)
        push_user_notification(
            db,
            user_id=user.id,
            notification_type="quiz_generated",
            title=title,
            message=message,
            course_id=quiz.course_id,
            course_name=str(detail.get("course_name") or ""),
            resource_type="quiz",
            resource_id=quiz.id,
            task_id=task.id,
        )
        task.status = ProcessStatus.READY.value
        task.target_id = quiz.id
        task.detail = {
            **(task.detail if isinstance(task.detail, dict) else detail),
            "quiz_id": quiz.id,
            "question_count": question_count,
            "completed_at": datetime.now(UTC).isoformat(),
            "notification": {"title": title, "message": message},
        }
        db.add(task)
        db.commit()
    except Exception as exc:
        db.rollback()
        task = db.get(AsyncTaskLog, task_id)
        if task is None:
            return
        title, message = _quiz_generation_failure_title(kind=kind, title=str(detail.get("title") or "题目"))
        push_user_notification(
            db,
            user_id=user.id,
            notification_type="quiz_generation_failed",
            title=title,
            message=f"{message}错误：{str(exc)[:180]}",
            course_id=int(detail.get("course_id") or 0) or None,
            course_name=str(detail.get("course_name") or ""),
            resource_type="quiz",
            resource_id=None,
            task_id=task.id,
        )
        task.status = ProcessStatus.FAILED.value
        task.detail = {
            **(task.detail if isinstance(task.detail, dict) else detail),
            "error": str(exc),
            "failed_at": datetime.now(UTC).isoformat(),
            "notification": {"title": title, "message": message},
        }
        db.add(task)
        db.commit()
        raise


def get_weak_points(db: Session, *, course_id: int, user: User) -> list[dict]:
    rows = list_wrong_questions(db, course_id=course_id, user=user)
    by_point_id: dict[int, dict[str, float | int | str | None]] = {}
    untagged_wrong_count = 0
    for wrong, question in rows:
        point_id = wrong.knowledge_point_id or question.knowledge_point_id
        if point_id:
            point = db.get(KnowledgePoint, point_id)
            name = point.name if point else "未命名知识点"
            entry = by_point_id.setdefault(
                int(point_id),
                {
                    "knowledge_point_id": int(point_id),
                    "knowledge_point": name,
                    "wrong_count": 0,
                    "learning_signal_count": 0,
                    "qa_signal_count": 0,
                    "signal_score": 0.0,
                    "weak_score": 0.0,
                },
            )
            entry["wrong_count"] = int(entry["wrong_count"] or 0) + int(wrong.wrong_count or 0)
        else:
            untagged_wrong_count += int(wrong.wrong_count or 0)

    signal_stats = learning_signal_point_stats(db, course_id=course_id, user_id=user.id)
    for point_id, signal in signal_stats.items():
        point = db.get(KnowledgePoint, point_id)
        if point is None:
            continue
        entry = by_point_id.setdefault(
            point_id,
            {
                "knowledge_point_id": point_id,
                "knowledge_point": point.name,
                "wrong_count": 0,
                "learning_signal_count": 0,
                "qa_signal_count": 0,
                "signal_score": 0.0,
                "weak_score": 0.0,
            },
        )
        entry["learning_signal_count"] = int(signal.get("learning_signal_count") or 0)
        entry["qa_signal_count"] = int(signal.get("qa_signal_count") or 0)
        entry["signal_score"] = float(signal.get("signal_score") or 0)

    items: list[dict] = []
    for entry in by_point_id.values():
        entry["weak_score"] = round(float(entry.get("wrong_count") or 0) + float(entry.get("signal_score") or 0), 2)
        items.append(dict(entry))
    if untagged_wrong_count:
        items.append(
            {
                "knowledge_point_id": None,
                "knowledge_point": "未标注知识点",
                "wrong_count": untagged_wrong_count,
                "learning_signal_count": 0,
                "qa_signal_count": 0,
                "signal_score": 0.0,
                "weak_score": float(untagged_wrong_count),
            }
        )
    return sorted(
        items,
        key=lambda item: (-float(item.get("weak_score") or 0), -int(item.get("wrong_count") or 0), str(item.get("knowledge_point") or "")),
    )[:10]


# 学习任务单次预计时长的合理夹合区间（分钟）。
_ESTIMATED_MINUTES_MIN = 5
_ESTIMATED_MINUTES_MAX = 480


def _coerce_estimated_minutes(value, *, default: int) -> int:
    """防御性解析模型返回的预计分钟数：解析失败回退默认值，并夹合到合理区间（#56）。"""
    try:
        minutes = int(round(float(value)))
    except (TypeError, ValueError):
        minutes = default
    if minutes <= 0:
        minutes = default
    return max(_ESTIMATED_MINUTES_MIN, min(_ESTIMATED_MINUTES_MAX, minutes))


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
    # #18：注入课程真实知识点与该生薄弱点，让 AI 据课程内容生成计划而非空泛模板。
    knowledge_points = [
        point.name
        for point in ensure_knowledge_points(db, course_id=payload.course_id, chapter_id=None)
        if getattr(point, "name", None)
    ]
    weak_points = [
        str(item.get("knowledge_point"))
        for item in get_weak_points(db, course_id=payload.course_id, user=user)
        if item.get("knowledge_point")
    ]
    task_payloads = ai_service.generate_study_plan(
        goal=payload.goal,
        available_days=payload.available_days,
        daily_minutes=payload.daily_minutes,
        course_name=course.name,
        knowledge_points=knowledge_points,
        weak_points=weak_points,
        db=db,
    )
    tasks: list[StudyPlanTask] = []
    for item in task_payloads:
        estimated_minutes = _coerce_estimated_minutes(item.get("estimated_minutes"), default=payload.daily_minutes)
        task = StudyPlanTask(
            plan_id=plan.id,
            title=item["title"],
            task_date=item["task_date"],
            task_type=item["task_type"],
            estimated_minutes=estimated_minutes,
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
    scoped_course_id = _student_course_scope(db, user=user, course_id=course_id)
    if scoped_course_id is None:
        return []
    statement = select(StudyPlan).where(StudyPlan.user_id == user.id)
    statement = statement.where(StudyPlan.course_id == scoped_course_id)
    return list(db.scalars(statement.order_by(StudyPlan.created_at.desc())))


def get_plan_tasks(db: Session, *, plan_id: int, user: User) -> list[StudyPlanTask]:
    plan = db.scalar(select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user.id))
    if plan is None:
        raise not_found("学习计划不存在")
    _assert_student_course_access(db, course_id=plan.course_id, user=user)
    return list(db.scalars(select(StudyPlanTask).where(StudyPlanTask.plan_id == plan_id).order_by(StudyPlanTask.task_date)))


def _parse_task_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def checkin_task(db: Session, *, task_id: int, user: User, notes: str | None) -> StudyCheckin:
    task = db.get(StudyPlanTask, task_id)
    if task is None:
        raise not_found("学习任务不存在")
    plan = db.get(StudyPlan, task.plan_id)
    if plan is None or plan.user_id != user.id:
        raise forbidden("无权限打卡该任务")
    _assert_student_course_access(db, course_id=plan.course_id, user=user)
    # #48：不允许对未来日期的任务打卡。
    task_date = _parse_task_date(task.task_date)
    if task_date is not None and task_date > datetime.now(UTC).date():
        raise bad_request("该任务尚未到打卡日期，不能提前打卡。")
    task.status = TaskStatus.DONE.value
    checkin = db.scalar(select(StudyCheckin).where(StudyCheckin.task_id == task_id, StudyCheckin.user_id == user.id))
    already_checked_in = checkin is not None
    if checkin is None:
        # #48：首次打卡，记录 checked_in_at（模型 default 写入）。
        checkin = StudyCheckin(task_id=task_id, user_id=user.id, notes=notes)
    else:
        # #48：重复打卡保留首次 checked_in_at，仅在提供新备注时更新 notes。
        if notes is not None:
            checkin.notes = notes
    db.add_all([task, checkin])
    try:
        db.commit()
    except IntegrityError:
        # #L18：并发双击/重试打卡时，(task_id,user_id) 唯一约束会让第二个 commit 抛 IntegrityError。
        # 回滚后重新查询既有打卡记录，按"已打卡"幂等返回（保留首次 checked_in_at），不再 500。
        db.rollback()
        existing = db.scalar(select(StudyCheckin).where(StudyCheckin.task_id == task_id, StudyCheckin.user_id == user.id))
        if existing is None:
            raise
        existing.already_checked_in = True
        return existing
    db.refresh(checkin)
    checkin.already_checked_in = already_checked_in
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
