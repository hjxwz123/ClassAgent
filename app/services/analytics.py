from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.enums import LessonStatus, UserRole
from app.core.errors import forbidden
from app.db.models import (
    CourseMembership,
    KnowledgePoint,
    LearningProgress,
    Lesson,
    PedagogyArtifact,
    ProblemRecord,
    QARecord,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizQuestion,
    User,
)
from app.services.courses import _assert_course_owner, _get_course_or_404
from app.services.pedagogy import ARTIFACT_MISCONCEPTION_CARD, ARTIFACT_PROBLEM_TEMPLATE, ARTIFACT_TYPE_LABELS
from app.services.retrieval import score_text_for_query


def _assert_teacher_access(db: Session, *, course_id: int, user: User) -> None:
    course = _get_course_or_404(db, course_id)
    if user.role == UserRole.ADMIN.value:
        return
    if user.role != UserRole.TEACHER.value:
        raise forbidden("仅教师或管理员可查看教学分析")
    _assert_course_owner(course, user)


def _artifact_page_number(artifact: PedagogyArtifact) -> int | None:
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    try:
        return int(payload.get("page_number") or 0) or None
    except (TypeError, ValueError):
        return None


def _artifact_ref(artifact: PedagogyArtifact) -> dict[str, Any]:
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    page_number = _artifact_page_number(artifact)
    return {
        "artifact_id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "artifact_label": ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, artifact.artifact_type),
        "title": artifact.title,
        "lesson_id": artifact.lesson_id,
        "lesson_page_id": artifact.lesson_page_id,
        "page_number": page_number,
        "material_id": artifact.material_id,
        "material_title": payload.get("material_title") or "",
    }


def _weak_point_artifact_refs(db: Session, *, course_id: int, weak_points: list[dict]) -> None:
    if not weak_points:
        return
    artifacts = list(
        db.scalars(
            select(PedagogyArtifact)
            .where(PedagogyArtifact.course_id == course_id)
            .order_by(PedagogyArtifact.lesson_id, PedagogyArtifact.lesson_page_id, PedagogyArtifact.order_index)
            .limit(700)
        )
    )
    if not artifacts:
        return
    for point in weak_points:
        query = str(point.get("knowledge_point") or "").strip()
        if not query:
            continue
        ranked: list[tuple[int, PedagogyArtifact]] = []
        for artifact in artifacts:
            payload = artifact.payload if isinstance(artifact.payload, dict) else {}
            text = "\n".join(
                part
                for part in [
                    artifact.summary or "",
                    artifact.content or "",
                    " ".join(str(item) for item in artifact.keywords or []),
                    " ".join(str(value) for value in payload.values() if isinstance(value, (str, int, float))),
                ]
                if part
            )
            score = score_text_for_query(
                title=artifact.title,
                text=text,
                page_number=_artifact_page_number(artifact),
                query=query,
                term_limit=12,
            )
            if query.lower() in f"{artifact.title}\n{text}".lower():
                score += 30
            if score > 0:
                ranked.append((score, artifact))
        ranked.sort(key=lambda item: (item[0], -item[1].order_index), reverse=True)
        related_pages: list[dict[str, Any]] = []
        related_templates: list[dict[str, Any]] = []
        related_misconceptions: list[dict[str, Any]] = []
        seen_pages: set[tuple[int | None, int | None]] = set()
        seen_artifacts: set[int] = set()
        for _, artifact in ranked[:18]:
            ref = _artifact_ref(artifact)
            page_key = (ref.get("lesson_page_id"), ref.get("page_number"))
            if ref.get("page_number") and page_key not in seen_pages:
                seen_pages.add(page_key)
                related_pages.append(ref)
            if artifact.id not in seen_artifacts and artifact.artifact_type == ARTIFACT_PROBLEM_TEMPLATE:
                seen_artifacts.add(artifact.id)
                related_templates.append(ref)
            if artifact.id not in seen_artifacts and artifact.artifact_type == ARTIFACT_MISCONCEPTION_CARD:
                seen_artifacts.add(artifact.id)
                related_misconceptions.append(ref)
        point["related_pages"] = related_pages[:6]
        point["related_problem_templates"] = related_templates[:5]
        point["related_misconceptions"] = related_misconceptions[:5]


def get_course_analytics(db: Session, *, course_id: int, user: User, days: int = 30) -> dict:
    _assert_teacher_access(db, course_id=course_id, user=user)
    since = datetime.now(UTC) - timedelta(days=days)

    # 仅统计在册学生：移除学生后其派生数据（问答/错题/学习时长）不再计入。
    student_ids = list(
        db.scalars(
            select(CourseMembership.user_id).where(
                CourseMembership.course_id == course_id,
                CourseMembership.role == UserRole.STUDENT.value,
            )
        )
    )

    high_frequency_questions = (
        [
            {"question": question, "count": int(count or 0)}
            for question, count in db.execute(
                select(QARecord.question, func.count(QARecord.id))
                .where(QARecord.course_id == course_id, QARecord.created_at >= since, QARecord.user_id.in_(student_ids))
                .group_by(QARecord.question)
                .order_by(func.count(QARecord.id).desc(), func.max(QARecord.created_at).desc())
                .limit(10)
            )
        ]
        if student_ids
        else []
    )

    # #M8：薄弱点采用"窗口内实际发生的错误事件数"口径，而非对错题本(WrongQuestion)的历史
    # 累计 wrong_count 求和——后者会把老错题的全部历史错误次数计入本期，导致区间统计系统性偏高。
    # 这里直接统计 since 之后真实落库的错误作答事件：QuizAnswer.is_correct=False，
    # 时间字段用 QuizAnswer.created_at（作答记录在提交时一次性创建，反映错误实际发生时间），
    # 经 QuizAttempt 取 user_id、经 QuizQuestion 取 course_id 与 knowledge_point_id 归因到知识点。
    point_id = QuizQuestion.knowledge_point_id
    point_name = func.coalesce(KnowledgePoint.name, "未标注知识点")
    weak_points = (
        [
            {"knowledge_point_id": point_id_value, "knowledge_point": name, "wrong_count": int(count or 0)}
            for point_id_value, name, count in db.execute(
                select(point_id, point_name, func.count(QuizAnswer.id))
                .select_from(QuizAnswer)
                .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
                .join(QuizQuestion, QuizQuestion.id == QuizAnswer.question_id)
                .outerjoin(
                    KnowledgePoint,
                    KnowledgePoint.id == point_id,
                )
                .where(
                    QuizQuestion.course_id == course_id,
                    QuizAnswer.is_correct.is_(False),
                    # 修复 #1：排除"待人工批改"的主观题——它以 is_correct=False 落库但并非真正答错，
                    # 否则会把待批改题误计为该知识点的错误事件，虚高薄弱点排名、误导教师布置专项练习。
                    QuizAnswer.pending_review.is_(False),
                    QuizAnswer.created_at >= since,
                    QuizAttempt.user_id.in_(student_ids),
                )
                .group_by(point_id, point_name)
                .order_by(func.count(QuizAnswer.id).desc(), point_name.asc())
                .limit(10)
            )
        ]
        if student_ids
        else []
    )
    _weak_point_artifact_refs(db, course_id=course_id, weak_points=weak_points)
    active_students: set[int] = set()
    if student_ids:
        active_students.update(
            int(student_id)
            for student_id in db.scalars(
                select(LearningProgress.user_id)
                .join(Lesson, Lesson.id == LearningProgress.lesson_id)
                .where(
                    LearningProgress.user_id.in_(student_ids),
                    Lesson.course_id == course_id,
                    LearningProgress.updated_at >= since,
                )
                .distinct()
            )
        )
        active_students.update(
            int(student_id)
            for student_id in db.scalars(
                select(QARecord.user_id)
                .where(
                    QARecord.user_id.in_(student_ids),
                    QARecord.course_id == course_id,
                    QARecord.created_at >= since,
                )
                .distinct()
            )
        )
        active_students.update(
            int(student_id)
            for student_id in db.scalars(
                select(ProblemRecord.user_id)
                .where(
                    ProblemRecord.user_id.in_(student_ids),
                    ProblemRecord.course_id == course_id,
                    ProblemRecord.created_at >= since,
                )
                .distinct()
            )
        )
        active_students.update(
            int(student_id)
            for student_id in db.scalars(
                select(QuizAttempt.user_id)
                .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
                .where(
                    QuizAttempt.user_id.in_(student_ids),
                    Quiz.course_id == course_id,
                    QuizAttempt.created_at >= since,
                )
                .distinct()
            )
        )
    inactive_students = [
        {"user_id": student_id, "status": "inactive"}
        for student_id in student_ids
        if student_id not in active_students
    ]

    score_bucket = case(
        (QuizAttempt.accuracy < 60, "0-59"),
        (QuizAttempt.accuracy < 70, "60-69"),
        (QuizAttempt.accuracy < 80, "70-79"),
        (QuizAttempt.accuracy < 90, "80-89"),
        else_="90-100",
    )
    score_distribution_map = {
        str(bucket): int(count or 0)
        for bucket, count in (
            db.execute(
                select(score_bucket, func.count(QuizAttempt.id))
                .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
                .where(Quiz.course_id == course_id, QuizAttempt.created_at >= since, QuizAttempt.user_id.in_(student_ids))
                .group_by(score_bucket)
            )
            if student_ids
            else []
        )
    }
    score_distribution = [
        {"range": label, "count": score_distribution_map.get(label, 0)}
        for label in ["0-59", "60-69", "70-79", "80-89", "90-100"]
    ]

    published_lesson_ids = list(
        db.scalars(select(Lesson.id).where(Lesson.course_id == course_id, Lesson.status == LessonStatus.PUBLISHED.value))
    )
    total_required = max(len(published_lesson_ids) * len(student_ids), 1)
    completed_count = 0
    if published_lesson_ids and student_ids:
        completed_count = int(
            db.scalar(
                select(func.count(LearningProgress.id)).where(
                    LearningProgress.lesson_id.in_(published_lesson_ids),
                    LearningProgress.user_id.in_(student_ids),
                    LearningProgress.completed_at.is_not(None),
                )
            )
            or 0
        )
    completion_rate = round(completed_count / total_required * 100, 2) if student_ids and published_lesson_ids else 0.0

    total_study_seconds = int(
        db.scalar(
            select(func.coalesce(func.sum(LearningProgress.total_study_seconds), 0))
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(Lesson.course_id == course_id, LearningProgress.user_id.in_(student_ids))
        )
        or 0
    ) if student_ids else 0
    period_study_seconds = int(
        db.scalar(
            select(func.coalesce(func.sum(LearningProgress.total_study_seconds), 0))
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(Lesson.course_id == course_id, LearningProgress.updated_at >= since, LearningProgress.user_id.in_(student_ids))
        )
        or 0
    ) if student_ids else 0
    day_count = min(max(days, 1), 30)
    day_start = (datetime.now(UTC) - timedelta(days=day_count - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_seconds: dict[str, int] = {}
    for index in range(day_count):
        day = day_start + timedelta(days=index)
        daily_seconds[day.date().isoformat()] = 0
    daily_rows = (
        db.execute(
            select(func.date(LearningProgress.updated_at), func.coalesce(func.sum(LearningProgress.total_study_seconds), 0))
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(Lesson.course_id == course_id, LearningProgress.updated_at >= day_start, LearningProgress.user_id.in_(student_ids))
            .group_by(func.date(LearningProgress.updated_at))
        )
        if student_ids
        else []
    )
    for day_value, seconds in daily_rows:
        key = day_value.isoformat() if hasattr(day_value, "isoformat") else str(day_value)
        if key in daily_seconds:
            daily_seconds[key] = int(seconds or 0)
    study_time_series = [
        {
            "date": key,
            "label": datetime.fromisoformat(key).strftime("%m/%d"),
            "minutes": round(seconds / 60, 2),
            "seconds": seconds,
        }
        for key, seconds in daily_seconds.items()
    ]
    if weak_points:
        suggestion = f"优先处理“{weak_points[0]['knowledge_point']}”等薄弱点，并发布一组专项练习。"
    elif inactive_students:
        suggestion = f"有 {len(inactive_students)} 名学生近期未活跃，建议发送学习提醒并安排低门槛复习任务。"
    elif high_frequency_questions:
        suggestion = "高频问题较集中，建议补充一段课堂讲解或整理答疑材料。"
    else:
        suggestion = "当前课程数据平稳，可继续保持课时发布与练习反馈节奏。"
    return {
        "high_frequency_questions": high_frequency_questions,
        "weak_points": weak_points,
        "inactive_students": inactive_students,
        "score_distribution": score_distribution,
        "completion_rate": completion_rate,
        "study_seconds": total_study_seconds,
        "period_study_seconds": period_study_seconds,
        "study_time_series": study_time_series,
        "suggestion": suggestion,
    }
