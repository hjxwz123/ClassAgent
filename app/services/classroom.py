from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import LessonStatus, UserRole
from app.core.errors import forbidden, not_found
from app.db.models import CourseMembership, LearningProgress, Lesson, LessonPage, User
from app.services.courses import _assert_course_owner, _get_course_or_404


def _assert_student_in_course(db: Session, *, course_id: int, user: User) -> None:
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可访问已加入课程的课堂")


def list_lessons(db: Session, *, course_id: int, user: User) -> list[Lesson]:
    course = _get_course_or_404(db, course_id)
    statement = select(Lesson).where(Lesson.course_id == course.id)
    if user.role == UserRole.STUDENT.value:
        _assert_student_in_course(db, course_id=course_id, user=user)
        statement = statement.where(Lesson.status == LessonStatus.PUBLISHED.value)
    elif user.role == UserRole.TEACHER.value:
        _assert_course_owner(course, user)
    return list(db.scalars(statement.order_by(Lesson.created_at.desc())))


def get_lesson_detail(db: Session, *, lesson_id: int, user: User) -> tuple[Lesson, list[LessonPage]]:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课堂不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_in_course(db, course_id=lesson.course_id, user=user)
        if lesson.status != LessonStatus.PUBLISHED.value:
            raise forbidden("课堂尚未发布")
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, lesson.course_id)
        _assert_course_owner(course, user)
    pages = list(db.scalars(select(LessonPage).where(LessonPage.lesson_id == lesson_id).order_by(LessonPage.page_number)))
    return lesson, pages


def publish_lesson(db: Session, *, lesson_id: int, user: User, status: str) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课堂不存在")
    course = _get_course_or_404(db, lesson.course_id)
    _assert_course_owner(course, user)
    lesson.status = status
    if status == LessonStatus.PUBLISHED.value:
        lesson.published_at = datetime.now(UTC)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def update_learning_progress(
    db: Session,
    *,
    lesson_id: int,
    user: User,
    current_page: int,
    added_seconds: int,
    completed: bool,
) -> LearningProgress:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课堂不存在")
    _assert_student_in_course(db, course_id=lesson.course_id, user=user)
    progress = db.scalar(
        select(LearningProgress).where(LearningProgress.lesson_id == lesson_id, LearningProgress.user_id == user.id)
    )
    if progress is None:
        progress = LearningProgress(
            lesson_id=lesson_id,
            user_id=user.id,
            resumed_from_page=current_page,
            total_study_seconds=0,
            progress_percent=0,
        )
    progress.current_page = current_page
    progress.total_study_seconds += added_seconds
    progress.progress_percent = round(min(100.0, current_page / max(lesson.page_count, 1) * 100), 2)
    if completed or current_page >= lesson.page_count:
        progress.completed_at = datetime.now(UTC)
        progress.progress_percent = 100.0
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def get_learning_progress(db: Session, *, lesson_id: int, user: User) -> LearningProgress | None:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课堂不存在")
    _assert_student_in_course(db, course_id=lesson.course_id, user=user)
    return db.scalar(select(LearningProgress).where(LearningProgress.lesson_id == lesson_id, LearningProgress.user_id == user.id))
