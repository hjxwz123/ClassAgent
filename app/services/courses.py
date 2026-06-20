from datetime import UTC, datetime
from random import choices
from string import ascii_uppercase, digits
from urllib.parse import urlsplit

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import CourseStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.core.upload_validation import validate_image_upload
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


def _assert_course_available_for_student(db: Session, course_id: int) -> Course:
    course = _get_course_or_404(db, course_id)
    if course.status != CourseStatus.ACTIVE.value:
        raise forbidden("课程已下架，暂时无法访问")
    return course


def _trusted_cover_hosts(db: Session) -> set[str]:
    # #42：可信封面 host = 本站对外地址 + 当前存储（本地/OSS/CDN）实际会产出的 host。
    # 用一个探针相对路径让 storage_service 按当前配置生成真实 public_url，取其 host，
    # 从而覆盖本地 public_base_url、OSS public_base_url/cdn_domain、bucket 虚拟主机等所有情况。
    hosts: set[str] = set()
    base_url = str(get_settings().public_base_url or "").strip()
    if base_url:
        host = urlsplit(base_url).hostname
        if host:
            hosts.add(host.lower())
    try:
        # 探针须带 public/ 前缀，否则 storage.public_url 对非 public 路径短路返回 ""（见 storage.py），
        # 导致 OSS/CDN 实际 host 永远进不了白名单、误拒平台自有 https 封面。
        probe = storage_service.public_url("public/course_covers/_cover_host_probe.png", db=db)
    except Exception:
        probe = None
    if probe:
        probe_host = urlsplit(probe).hostname
        if probe_host:
            hosts.add(probe_host.lower())
    return hosts


def _validate_cover_url(cover_url: str, db: Session) -> str:
    candidate = cover_url.strip()
    if candidate.startswith("//"):
        raise bad_request("封面地址不合法")
    if candidate.startswith("/"):
        # 本站相对路径（如 /static/... 或 /api/v1/media/...）始终允许。
        return candidate
    if candidate.startswith("https://"):
        # #42：仅允许指向本平台存储/CDN 的 https 封面，拒绝任意外部站点（防外链追踪/IP 泄露）。
        host = (urlsplit(candidate).hostname or "").lower()
        if host and host in _trusted_cover_hosts(db):
            return candidate
        raise bad_request("封面地址必须使用平台上传的封面，请通过上传封面功能设置")
    raise bad_request("封面地址不合法")


def _assert_course_active_for_teacher(course: Course, user: User, message: str = "课程已下架，无法执行该操作") -> None:
    if user.role == UserRole.TEACHER.value and course.status != CourseStatus.ACTIVE.value:
        raise forbidden(message)


def _assert_course_owner(course: Course, user: User, *, require_active: bool = False) -> None:
    if user.role == UserRole.ADMIN.value:
        return
    if course.teacher_id != user.id:
        raise forbidden("仅课程负责人可管理该课程")
    if require_active:
        _assert_course_active_for_teacher(course, user)


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
        allow_general_ai_answer=bool(payload.allow_general_ai_answer),
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
    _assert_course_owner(course, user, require_active=True)
    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description
    if payload.term is not None:
        course.term = payload.term
    if payload.status is not None:
        if user.role != UserRole.ADMIN.value:
            raise forbidden("请使用课程上架/下架操作修改状态")
        if payload.status not in {item.value for item in CourseStatus}:
            raise bad_request("课程状态不合法")
        course.status = payload.status
    if payload.cover_url is not None:
        course.cover_url = _validate_cover_url(payload.cover_url, db) if payload.cover_url else None
    if payload.cover_color is not None:
        course.cover_color = payload.cover_color or None
    if payload.allow_general_ai_answer is not None:
        course.allow_general_ai_answer = bool(payload.allow_general_ai_answer)
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
    _assert_course_owner(course, user, require_active=True)
    validated = validate_image_upload(upload, max_bytes=8 * 1024 * 1024, label="课程封面")
    storage_path, size_bytes = storage_service.save_upload_bytes(
        validated.content,
        folder=f"course_covers/course_{course_id}",
        suffix=validated.suffix,
        db=db,
        public=True,
    )
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
    _assert_course_owner(course, user, require_active=True)
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


def activate_course(db: Session, user: User, course_id: int) -> Course:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user)
    course.status = CourseStatus.ACTIVE.value
    db.add(course)
    log_operation(
        db,
        user_id=user.id,
        action="course.activate",
        target_type="course",
        target_id=course.id,
        detail={"activated_at": datetime.now(UTC).isoformat()},
    )
    db.commit()
    db.refresh(course)
    return course
