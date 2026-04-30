from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import QuizStatus, QuizType, QuestionType, TaskStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import (
    CourseMembership,
    KnowledgePoint,
    QARecord,
    ProblemRecord,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizQuestion,
    Lesson,
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


def _source_text_for_quiz(points: list[KnowledgePoint]) -> str:
    pieces: list[str] = []
    for point in points:
        content = point.content_by_level or {}
        standard = content.get("standard", {})
        if isinstance(standard, dict):
            pieces.append(" ".join(str(item) for item in standard.values()))
    return "\n".join(pieces)


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
    points = ensure_knowledge_points(db, course_id=payload.course_id, chapter_id=payload.chapter_id)
    quiz = Quiz(
        course_id=payload.course_id,
        chapter_id=payload.chapter_id,
        creator_id=user.id,
        title=payload.title,
        description=f"基于课程内容自动生成：{payload.title}",
        quiz_type=payload.quiz_type,
        status=QuizStatus.REVIEW.value if payload.quiz_type == QuizType.COURSE.value and user.role != UserRole.STUDENT.value else QuizStatus.PUBLISHED.value,
        metadata_json={"generated": True},
        total_score=0,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    source_text = _source_text_for_quiz(points) or payload.title
    question_dicts = ai_service.generate_quiz_questions(
        topic=payload.title,
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
            chapter_id=payload.chapter_id,
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


def submit_quiz(db: Session, *, quiz_id: int, user: User, answers: list[dict]) -> QuizAttempt:
    quiz, questions = get_quiz_detail(db, quiz_id=quiz_id, user=user)
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可提交测验")
    question_map = {question.id: question for question in questions}
    attempt = QuizAttempt(quiz_id=quiz_id, user_id=user.id, total_score=quiz.total_score, submitted_at=datetime.now(UTC))
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    total_score = 0.0
    for answer_payload in answers:
        question = question_map.get(answer_payload["question_id"])
        if question is None:
            continue
        user_answer = answer_payload.get("answer")
        is_correct = False
        score = 0.0
        feedback = question.explanation
        if question.question_type in {QuestionType.SINGLE_CHOICE.value, QuestionType.JUDGE.value}:
            expected = question.reference_answer["value"] if isinstance(question.reference_answer, dict) else question.reference_answer
            is_correct = user_answer == expected
            score = question.score if is_correct else 0.0
        elif question.question_type == QuestionType.MULTIPLE_CHOICE.value:
            expected = question.reference_answer["value"] if isinstance(question.reference_answer, dict) else question.reference_answer
            expected_values = sorted(str(item) for item in (expected or []))
            actual_values = sorted(str(item) for item in (user_answer or []))
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
            actual_text = str(user_answer or "")
            matched = sum(1 for item in expected_values if item and item in actual_text)
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
        if not is_correct:
            wrong = db.scalar(
                select(WrongQuestion).where(WrongQuestion.user_id == user.id, WrongQuestion.question_id == question.id)
            )
            if wrong is None:
                wrong = WrongQuestion(
                    user_id=user.id,
                    question_id=question.id,
                    course_id=quiz.course_id,
                    knowledge_point_id=question.knowledge_point_id,
                    wrong_count=1,
                    last_attempt_id=attempt.id,
                )
            else:
                wrong.wrong_count += 1
                wrong.last_attempt_id = attempt.id
            db.add(wrong)
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
    quiz = Quiz(
        course_id=course_id,
        chapter_id=None,
        creator_id=user.id,
        title="错题重练",
        description="基于错题本自动生成",
        quiz_type=QuizType.WRONG_BOOK.value,
        status=QuizStatus.PUBLISHED.value,
        metadata_json={"generated": True},
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    total_score = 0.0
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
    quiz.total_score = total_score
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
