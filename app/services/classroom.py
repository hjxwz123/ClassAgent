from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import LessonStatus, UserRole
from app.core.errors import forbidden, not_found
from app.db.models import CourseMaterial, CourseMembership, LearningProgress, Lesson, LessonPage, User
from app.services.courses import (
    _assert_course_available_for_student,
    _assert_course_owner,
    _get_course_or_404,
)
from app.services.storage import storage_service


def _assert_student_in_course(db: Session, *, course_id: int, user: User) -> None:
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可访问已加入课程的课时")
    _assert_course_available_for_student(db, course_id)


def list_lessons(db: Session, *, course_id: int, user: User) -> list[Lesson]:
    course = _get_course_or_404(db, course_id)
    statement = select(Lesson).where(Lesson.course_id == course.id)
    if user.role == UserRole.STUDENT.value:
        _assert_student_in_course(db, course_id=course_id, user=user)
        statement = statement.where(Lesson.status == LessonStatus.PUBLISHED.value)
    elif user.role == UserRole.TEACHER.value:
        _assert_course_owner(course, user)
    return list(db.scalars(statement.order_by(Lesson.created_at.desc())))


def get_lesson_detail(db: Session, *, lesson_id: int, user: User) -> tuple[Lesson, list[LessonPage], CourseMaterial | None]:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_in_course(db, course_id=lesson.course_id, user=user)
        if lesson.status != LessonStatus.PUBLISHED.value:
            raise forbidden("课时尚未发布")
    elif user.role == UserRole.TEACHER.value:
        course = _get_course_or_404(db, lesson.course_id)
        _assert_course_owner(course, user)
    pages = list(db.scalars(select(LessonPage).where(LessonPage.lesson_id == lesson_id).order_by(LessonPage.page_number)))
    material = db.get(CourseMaterial, lesson.material_id) if lesson.material_id else None
    if material is not None and material.deleted_at is not None:
        material = None
    if material is not None:
        material.preview_url = storage_service.normalize_public_url(material.preview_url)
    return lesson, pages, material


def publish_lesson(db: Session, *, lesson_id: int, user: User, status: str) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    course = _get_course_or_404(db, lesson.course_id)
    _assert_course_owner(course, user, require_active=True)
    lesson.status = status
    if status == LessonStatus.PUBLISHED.value:
        lesson.published_at = datetime.now(UTC)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# 单课时单日累计学习时长软上限：遏制重复上报 added_seconds 无限刷 total_study_seconds。
# 注意：这是务实硬化而非彻底防伪——精确防伪需服务端浏览/心跳埋点（按真实在线时长计时），
# 当前仅在客户端自报模型下叠加“限流（路由层）+ 单次上界（schema le=3600）+ 本日累计软上限”三重约束。
# 该软上限按 UTC 自然日统计：同一 (lesson, user) 当日累计新增不超过 MAX_DAILY_STUDY_SECONDS。
MAX_DAILY_STUDY_SECONDS = 8 * 3600


def update_learning_progress(
    db: Session,
    *,
    lesson_id: int,
    user: User,
    current_page: int,
    added_seconds: int,
) -> LearningProgress:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_student_in_course(db, course_id=lesson.course_id, user=user)
    if lesson.status != LessonStatus.PUBLISHED.value:
        raise forbidden("课时尚未发布")
    safe_page = min(max(current_page, 1), max(lesson.page_count, 1))
    progress = db.scalar(
        select(LearningProgress).where(LearningProgress.lesson_id == lesson_id, LearningProgress.user_id == user.id)
    )
    if progress is None:
        progress = LearningProgress(
            lesson_id=lesson_id,
            user_id=user.id,
            resumed_from_page=safe_page,
            total_study_seconds=0,
            progress_percent=0,
        )
        db.add(progress)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            progress = db.scalar(
                select(LearningProgress).where(
                    LearningProgress.lesson_id == lesson_id, LearningProgress.user_id == user.id
                )
            )
            if progress is None:
                raise
    # 本日累计软上限：以 updated_at 是否落在“今天(UTC)”判断今日已累计基线。
    # 缺少独立的“当日累计”列，故采用保守近似——若上次更新发生在今天，则把已有的
    # total_study_seconds 视为今日已计入的下界，确保叠加后不超过当日上限；跨日则重新放开。
    now = datetime.now(UTC)
    last_updated = progress.updated_at
    if last_updated is not None and last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=UTC)
    same_utc_day = last_updated is not None and last_updated.date() == now.date()
    today_baseline = progress.total_study_seconds if same_utc_day else 0
    allowed_today = max(0, MAX_DAILY_STUDY_SECONDS - today_baseline)
    bounded_added = max(0, min(added_seconds, allowed_today))

    progress.current_page = safe_page
    progress.total_study_seconds += bounded_added
    progress.progress_percent = round(min(100.0, safe_page / max(lesson.page_count, 1) * 100), 2)
    if safe_page >= lesson.page_count:
        progress.completed_at = now
        progress.progress_percent = 100.0
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def get_learning_progress(db: Session, *, lesson_id: int, user: User) -> LearningProgress | None:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_student_in_course(db, course_id=lesson.course_id, user=user)
    if lesson.status != LessonStatus.PUBLISHED.value:
        raise forbidden("课时尚未发布")
    return db.scalar(select(LearningProgress).where(LearningProgress.lesson_id == lesson_id, LearningProgress.user_id == user.id))
