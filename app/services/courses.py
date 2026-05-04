from datetime import UTC, datetime
from random import choices
from string import ascii_uppercase, digits

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import CourseStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import Chapter, Course, CourseMembership, User
from app.schemas.course import ChapterCreateRequest, CourseCreateRequest, CourseUpdateRequest
from app.services.audit import log_operation
from app.services.storage import storage_service


COURSE_CODE_CHARS = ascii_uppercase + digits


def _generate_course_code(db: Session, length: int = 6) -> str:
    while True:
        code = "".join(choices(COURSE_CODE_CHARS, k=length))
        exists = db.scalar(select(Course.id).where(Course.course_code == code))
        if exists is None:
            return code


def _ensure_teacher_or_admin(user: User) -> None:
    if user.role not in {UserRole.TEACHER.value, UserRole.ADMIN.value}:
        raise forbidden("仅教师或管理员可执行该操作")


def _ensure_student(user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可执行该操作")


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    return course


def _assert_course_owner(course: Course, user: User) -> None:
    if user.role == UserRole.ADMIN.value:
        return
    if course.teacher_id != user.id:
        raise forbidden("仅课程负责人可管理该课程")


def create_course(db: Session, user: User, payload: CourseCreateRequest) -> Course:
    _ensure_teacher_or_admin(user)
    course = Course(
        name=payload.name,
        description=payload.description,
        term=payload.term,
        course_code=_generate_course_code(db),
        teacher_id=user.id,
        status=CourseStatus.ACTIVE.value,
        cover_color=payload.cover_color,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    log_operation(
        db,
        user_id=user.id,
        action="course.create",
        target_type="course",
        target_id=course.id,
        detail={"course_code": course.course_code},
    )
    db.commit()
    return course


def update_course(db: Session, user: User, course_id: int, payload: CourseUpdateRequest) -> Course:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description
    if payload.term is not None:
        course.term = payload.term
    if payload.status is not None:
        course.status = payload.status
    if payload.cover_url is not None:
        course.cover_url = payload.cover_url or None
    if payload.cover_color is not None:
        course.cover_color = payload.cover_color or None
    db.add(course)
    log_operation(
        db,
        user_id=user.id,
        action="course.update",
        target_type="course",
        target_id=course.id,
    )
    db.commit()
    db.refresh(course)
    return course


def upload_course_cover(db: Session, user: User, course_id: int, upload: UploadFile) -> Course:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    suffix = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else ""
    content_type = (upload.content_type or "").lower()
    if not content_type.startswith("image/") and suffix not in {"jpg", "jpeg", "png", "webp", "gif"}:
        raise bad_request("课程封面仅支持图片文件")
    storage_path, size_bytes = storage_service.save_upload(upload, folder=f"course_covers/course_{course_id}", db=db)
    if size_bytes > 8 * 1024 * 1024:
        raise bad_request("课程封面不能超过 8MB")
    course.cover_url = storage_service.public_url(storage_path, db=db)
    db.add(course)
    log_operation(
        db,
        user_id=user.id,
        action="course.cover.upload",
        target_type="course",
        target_id=course.id,
        detail={"filename": upload.filename, "size_bytes": size_bytes},
    )
    db.commit()
    db.refresh(course)
    return course


def create_chapter(db: Session, user: User, course_id: int, payload: ChapterCreateRequest) -> Chapter:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    chapter = Chapter(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
    )
    db.add(chapter)
    log_operation(
        db,
        user_id=user.id,
        action="course.chapter.create",
        target_type="chapter",
    )
    db.commit()
    db.refresh(chapter)
    return chapter


def list_course_chapters(db: Session, course_id: int) -> list[Chapter]:
    return list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))


def list_teaching_courses(db: Session, user: User) -> list[Course]:
    _ensure_teacher_or_admin(user)
    statement = select(Course).where(Course.deleted_at.is_(None))
    if user.role != UserRole.ADMIN.value:
        statement = statement.where(Course.teacher_id == user.id)
    return list(db.scalars(statement.order_by(Course.created_at.desc())))


def list_joined_courses(db: Session, user: User) -> list[Course]:
    _ensure_student(user)
    statement = (
        select(Course)
        .join(CourseMembership, CourseMembership.course_id == Course.id)
        .where(
            CourseMembership.user_id == user.id,
            Course.deleted_at.is_(None),
        )
        .order_by(Course.created_at.desc())
    )
    return list(db.scalars(statement))


def join_course(db: Session, user: User, course_code: str) -> Course:
    _ensure_student(user)
    course = db.scalar(select(Course).where(Course.course_code == course_code, Course.deleted_at.is_(None)))
    if course is None or course.status != CourseStatus.ACTIVE.value:
        raise not_found("课程不存在或已停用")
    exists = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course.id, CourseMembership.user_id == user.id)
    )
    if exists is not None:
        raise bad_request("你已加入该课程")
    membership = CourseMembership(course_id=course.id, user_id=user.id, role=UserRole.STUDENT.value)
    db.add(membership)
    log_operation(
        db,
        user_id=user.id,
        action="course.join",
        target_type="course",
        target_id=course.id,
    )
    db.commit()
    return course


def leave_course(db: Session, user: User, course_id: int) -> None:
    _ensure_student(user)
    membership = db.scalar(
        select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise not_found("未加入该课程")
    db.delete(membership)
    log_operation(
        db,
        user_id=user.id,
        action="course.leave",
        target_type="course",
        target_id=course_id,
    )
    db.commit()


def get_course_detail(db: Session, user: User, course_id: int) -> tuple[Course, User, list[Chapter], int]:
    course = _get_course_or_404(db, course_id)
    teacher = db.get(User, course.teacher_id)
    if teacher is None:
        raise not_found("课程教师不存在")
    if user.role == UserRole.STUDENT.value:
        membership = db.scalar(
            select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
        )
        if membership is None:
            raise forbidden("仅可查看已加入课程")
    elif user.role == UserRole.TEACHER.value:
        _assert_course_owner(course, user)
    chapters = list_course_chapters(db, course_id)
    student_count = db.scalar(
        select(func.count(CourseMembership.id)).where(
            CourseMembership.course_id == course_id,
            CourseMembership.role == UserRole.STUDENT.value,
        )
    )
    return course, teacher, chapters, int(student_count or 0)


def list_course_members(db: Session, user: User, course_id: int) -> list[tuple[CourseMembership, User]]:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    statement = (
        select(CourseMembership, User)
        .join(User, User.id == CourseMembership.user_id)
        .where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
        .order_by(CourseMembership.joined_at.asc())
    )
    return list(db.execute(statement).all())


def deactivate_course(db: Session, user: User, course_id: int) -> Course:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    course.status = CourseStatus.INACTIVE.value
    db.add(course)
    log_operation(
        db,
        user_id=user.id,
        action="course.deactivate",
        target_type="course",
        target_id=course.id,
        detail={"deactivated_at": datetime.now(UTC).isoformat()},
    )
    db.commit()
    db.refresh(course)
    return course
