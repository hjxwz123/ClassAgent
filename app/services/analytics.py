from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.errors import forbidden
from app.db.models import (
    CourseMembership,
    KnowledgePoint,
    LearningProgress,
    Lesson,
    ProblemRecord,
    QARecord,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    User,
    WrongQuestion,
)
from app.services.ai import ai_service
from app.services.courses import _assert_course_owner, _get_course_or_404


def _assert_teacher_access(db: Session, *, course_id: int, user: User) -> None:
    course = _get_course_or_404(db, course_id)
    if user.role == UserRole.ADMIN.value:
        return
    if user.role != UserRole.TEACHER.value:
        raise forbidden("仅教师或管理员可查看教学分析")
    _assert_course_owner(course, user)


def get_course_analytics(db: Session, *, course_id: int, user: User, days: int = 30) -> dict:
    _assert_teacher_access(db, course_id=course_id, user=user)
    since = datetime.now(UTC) - timedelta(days=days)

    qa_records = list(
        db.scalars(select(QARecord).where(QARecord.course_id == course_id, QARecord.created_at >= since))
    )
    question_counter = Counter(record.question for record in qa_records)
    high_frequency_questions = [
        {"question": question, "count": count} for question, count in question_counter.most_common(10)
    ]

    weak_counter: Counter[str] = Counter()
    wrong_rows = list(
        db.execute(
            select(WrongQuestion, QuizQuestion)
            .join(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
            .where(WrongQuestion.course_id == course_id, WrongQuestion.updated_at >= since)
        ).all()
    )
    for wrong, question in wrong_rows:
        if question.knowledge_point_id:
            point = db.get(KnowledgePoint, question.knowledge_point_id)
            weak_counter[point.name if point else "未命名知识点"] += wrong.wrong_count
        else:
            weak_counter["未标注知识点"] += wrong.wrong_count
    weak_points = [{"knowledge_point": name, "wrong_count": count} for name, count in weak_counter.most_common(10)]

    student_ids = [
        row[0]
        for row in db.execute(
            select(CourseMembership.user_id).where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
        )
    ]
    active_students: set[int] = set()
    for student_id in student_ids:
        progress_active = db.scalar(
            select(LearningProgress.id)
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(
                LearningProgress.user_id == student_id,
                Lesson.course_id == course_id,
                LearningProgress.updated_at >= since,
            )
        )
        qa_active = db.scalar(select(QARecord.id).where(QARecord.user_id == student_id, QARecord.course_id == course_id, QARecord.created_at >= since))
        problem_active = db.scalar(
            select(ProblemRecord.id).where(ProblemRecord.user_id == student_id, ProblemRecord.course_id == course_id, ProblemRecord.created_at >= since)
        )
        attempt_active = db.scalar(
            select(QuizAttempt.id)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(QuizAttempt.user_id == student_id, Quiz.course_id == course_id, QuizAttempt.created_at >= since)
        )
        if progress_active or qa_active or problem_active or attempt_active:
            active_students.add(student_id)
    inactive_students = [
        {"user_id": student_id, "status": "inactive"}
        for student_id in student_ids
        if student_id not in active_students
    ]

    attempts = list(
        db.scalars(
            select(QuizAttempt)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(Quiz.course_id == course_id, QuizAttempt.created_at >= since)
        )
    )
    distribution = defaultdict(int)
    for attempt in attempts:
        accuracy = attempt.accuracy
        if accuracy < 60:
            distribution["0-59"] += 1
        elif accuracy < 70:
            distribution["60-69"] += 1
        elif accuracy < 80:
            distribution["70-79"] += 1
        elif accuracy < 90:
            distribution["80-89"] += 1
        else:
            distribution["90-100"] += 1
    score_distribution = [{"range": key, "count": value} for key, value in distribution.items()]

    published_lessons = list(
        db.scalars(select(Lesson).where(Lesson.course_id == course_id, Lesson.status == "published"))
    )
    total_required = max(len(published_lessons) * len(student_ids), 1)
    completed_count = 0
    if published_lessons and student_ids:
        lesson_ids = [lesson.id for lesson in published_lessons]
        completed_count = db.scalar(
            select(func.count(LearningProgress.id)).where(
                LearningProgress.lesson_id.in_(lesson_ids),
                LearningProgress.user_id.in_(student_ids),
                LearningProgress.completed_at.is_not(None),
            )
        ) or 0
    completion_rate = round(completed_count / total_required * 100, 2) if student_ids and published_lessons else 0.0

    suggestion = ai_service.generate_teaching_suggestion(
        high_frequency_questions=len(high_frequency_questions),
        weak_points=[item["knowledge_point"] for item in weak_points],
        inactive_students=len(inactive_students),
    )
    return {
        "high_frequency_questions": high_frequency_questions,
        "weak_points": weak_points,
        "inactive_students": inactive_students,
        "score_distribution": score_distribution,
        "completion_rate": completion_rate,
        "suggestion": suggestion,
    }
