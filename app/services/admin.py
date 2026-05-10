from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import redis
from sqlalchemy import delete, distinct, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import BACKUP_DIR, VECTOR_DIR, get_settings
from app.core.enums import BackupStatus, ConfigScope, CourseStatus, LessonStatus, UserRole, UserStatus
from app.core.errors import bad_request, forbidden, not_found
from app.core.security import decrypt_secret, encrypt_secret, hash_password, mask_secret
from app.db.models import (
    AIUsageLog,
    ApiRequestLog,
    AsyncTaskLog,
    BackupRecord,
    Chapter,
    Course,
    CourseMembership,
    CourseMaterial,
    KnowledgeChunk,
    LearningProgress,
    Lesson,
    LoginLog,
    ModelConfig,
    OperationLog,
    ServiceConfig,
    SystemErrorLog,
    SystemSetting,
    User,
)
from app.services.bootstrap import default_system_settings
from app.services.email import email_service
from app.services.parser import (
    DEFAULT_DOC_PARSER_POLL_INTERVAL_SECONDS,
    DEFAULT_DOC_PARSER_TIMEOUT_SECONDS,
    MAX_DOC_PARSER_TIMEOUT_SECONDS,
)
from app.services.storage import storage_service
from app.services.tts import tts_service
from app.services.vector_store import vector_store


def assert_admin(user: User) -> None:
    if user.role != UserRole.ADMIN.value:
        raise forbidden("仅管理员可执行该操作")


def _model_dict(item) -> dict:
    data = dict(item.__dict__)
    data.pop("_sa_instance_state", None)
    if "preview_url" in data:
        data["preview_url"] = storage_service.normalize_public_url(data["preview_url"])
    if "audio_url" in data:
        data["audio_url"] = storage_service.normalize_public_url(data["audio_url"])
    if "cover_url" in data:
        data["cover_url"] = storage_service.normalize_public_url(data["cover_url"])
    return data


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _week_start() -> datetime:
    now = datetime.now(UTC)
    start = now - timedelta(days=now.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _day_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _storage_usage_bytes() -> int:
    total = 0
    storage_dir = get_settings().storage_dir
    if not storage_dir.exists():
        return 0
    for path in storage_dir.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def list_users(db: Session, *, role: str | None, status: str | None, keyword: str | None) -> list[User]:
    statement = select(User).where(User.deleted_at.is_(None))
    if role:
        statement = statement.where(User.role == role)
    if status:
        statement = statement.where(User.status == status)
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where((User.email.like(like)) | (User.nickname.like(like)))
    return list(db.scalars(statement.order_by(User.created_at.desc())))


def _course_progress_for_user(db: Session, *, course_id: int, user_id: int) -> float:
    progress_rows = list(
        db.scalars(
            select(LearningProgress)
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(LearningProgress.user_id == user_id, Lesson.course_id == course_id)
        )
    )
    lesson_total = int(
        db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id == course_id, Lesson.status == LessonStatus.PUBLISHED.value)) or 0
    )
    return round(sum(item.progress_percent for item in progress_rows) / max(lesson_total, 1), 2) if lesson_total else 0


def _course_student_count(db: Session, course_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(CourseMembership.id)).where(
                CourseMembership.course_id == course_id,
                CourseMembership.role == UserRole.STUDENT.value,
            )
        )
        or 0
    )


def _course_relation_entry(
    db: Session,
    *,
    course: Course,
    user: User,
    relation: str,
    role_label: str,
    joined_at: datetime | None = None,
) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "course_code": course.course_code,
        "term": course.term,
        "status": course.status,
        "teacher_id": course.teacher_id,
        "relation": relation,
        "role": role_label,
        "joined_at": joined_at,
        "student_count": _course_student_count(db, course.id),
        "progress_percent": _course_progress_for_user(db, course_id=course.id, user_id=user.id)
        if relation == "student"
        else None,
    }


def _user_related_courses(db: Session, user: User) -> list[dict]:
    entries: list[dict] = []
    seen: set[tuple[int, str]] = set()
    if user.role == UserRole.TEACHER.value:
        for course in db.scalars(
            select(Course)
            .where(Course.teacher_id == user.id, Course.deleted_at.is_(None))
            .order_by(Course.created_at.desc())
        ):
            entries.append(
                _course_relation_entry(
                    db,
                    course=course,
                    user=user,
                    relation="teacher",
                    role_label="授课教师",
                    joined_at=course.created_at,
                )
            )
            seen.add((course.id, "teacher"))
    memberships = list(
        db.scalars(
            select(CourseMembership)
            .where(CourseMembership.user_id == user.id)
            .order_by(CourseMembership.joined_at.desc(), CourseMembership.created_at.desc())
        )
    )
    for membership in memberships:
        relation = "student" if membership.role == UserRole.STUDENT.value else membership.role
        key = (membership.course_id, relation)
        if key in seen:
            continue
        course = db.get(Course, membership.course_id)
        if course is None or course.deleted_at is not None:
            continue
        role_label = "学生" if membership.role == UserRole.STUDENT.value else membership.role
        entries.append(
            _course_relation_entry(
                db,
                course=course,
                user=user,
                relation=relation,
                role_label=role_label,
                joined_at=membership.joined_at,
            )
        )
        seen.add(key)
    return sorted(entries, key=lambda item: (item.get("joined_at").timestamp() if item.get("joined_at") else 0), reverse=True)


def user_summary_admin(db: Session, user: User) -> dict:
    data = _model_dict(user)
    courses = _user_related_courses(db, user)
    data["course_count"] = len(courses)
    data["courses"] = courses[:3]
    return data


def list_user_summaries_admin(db: Session, *, role: str | None, status: str | None, keyword: str | None) -> list[dict]:
    return [user_summary_admin(db, user) for user in list_users(db, role=role, status=status, keyword=keyword)]


def get_user_stats(db: Session) -> dict:
    week_start = _week_start()
    counts = {
        role: count
        for role, count in db.execute(
            select(User.role, func.count(User.id)).where(User.deleted_at.is_(None)).group_by(User.role)
        )
    }
    total = sum(int(count or 0) for count in counts.values())
    weekly_new = db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None), User.created_at >= week_start)) or 0
    return {
        "total": int(total),
        "teachers": int(counts.get(UserRole.TEACHER.value, 0) or 0),
        "students": int(counts.get(UserRole.STUDENT.value, 0) or 0),
        "admins": int(counts.get(UserRole.ADMIN.value, 0) or 0),
        "weekly_new": int(weekly_new),
    }


def get_user_detail_admin(db: Session, *, user_id: int) -> dict:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found("用户不存在")
    recent_logs = list(db.scalars(select(OperationLog).where(OperationLog.user_id == user_id).order_by(OperationLog.created_at.desc()).limit(5)))
    return {
        "user": _model_dict(user),
        "courses": _user_related_courses(db, user),
        "logs": [_model_dict(item) for item in recent_logs],
    }


def create_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    nickname: str,
    role: str = UserRole.ADMIN.value,
    student_no: str | None = None,
    employee_no: str | None = None,
) -> User:
    if role not in {item.value for item in UserRole}:
        raise bad_request("角色不合法")
    if role == UserRole.STUDENT.value and not student_no:
        raise bad_request("学生账号必须提供学号")
    if role == UserRole.TEACHER.value and not employee_no:
        raise bad_request("教师账号必须提供工号")
    if role != UserRole.STUDENT.value:
        student_no = None
    if role != UserRole.TEACHER.value:
        employee_no = None
    conditions = [User.email == email]
    if student_no:
        conditions.append(User.student_no == student_no)
    if employee_no:
        conditions.append(User.employee_no == employee_no)
    exists = db.scalar(select(User).where(or_(*conditions), User.deleted_at.is_(None)))
    if exists is not None:
        raise bad_request("邮箱、学号或工号已存在")
    created_user = User(
        email=email,
        password_hash=hash_password(password),
        nickname=nickname,
        role=role,
        status=UserStatus.ACTIVE.value,
        student_no=student_no,
        employee_no=employee_no,
    )
    db.add(created_user)
    db.commit()
    db.refresh(created_user)
    return created_user


def update_user(db: Session, *, user_id: int, status: str | None, role: str | None) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found("用户不存在")
    if status is not None:
        if status not in {item.value for item in UserStatus}:
            raise bad_request("用户状态不合法")
        user.status = status
    if role is not None:
        if role not in {item.value for item in UserRole}:
            raise bad_request("角色不合法")
        if role != user.role:
            raise bad_request("用户角色创建后不可更改")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, *, user_id: int, new_password: str) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found("用户不存在")
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, *, user_id: int) -> None:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found("用户不存在")
    user.deleted_at = datetime.now(UTC)
    db.add(user)
    db.commit()


def list_courses_admin(db: Session, *, keyword: str | None, status: str | None) -> list[Course]:
    statement = select(Course).where(Course.deleted_at.is_(None))
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where((Course.name.like(like)) | (Course.course_code.like(like)))
    if status:
        statement = statement.where(Course.status == status)
    return list(db.scalars(statement.order_by(Course.created_at.desc())))


def get_course_stats(db: Session) -> dict:
    month_start = _month_start()
    total = db.scalar(select(func.count(Course.id)).where(Course.deleted_at.is_(None))) or 0
    active = db.scalar(select(func.count(Course.id)).where(Course.deleted_at.is_(None), Course.status == CourseStatus.ACTIVE.value)) or 0
    monthly_new = db.scalar(select(func.count(Course.id)).where(Course.deleted_at.is_(None), Course.created_at >= month_start)) or 0
    pending_materials = db.scalar(
        select(func.count(CourseMaterial.id)).where(
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status.in_(["pending", "processing", "failed"]),
        )
    ) or 0
    return {
        "total": int(total),
        "active": int(active),
        "pending_materials": int(pending_materials),
        "monthly_new": int(monthly_new),
    }


def course_summary_admin(db: Session, course: Course) -> dict:
    teacher = db.get(User, course.teacher_id)
    student_count = db.scalar(
        select(func.count(CourseMembership.id)).where(CourseMembership.course_id == course.id, CourseMembership.role == UserRole.STUDENT.value)
    ) or 0
    material_count = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.course_id == course.id, CourseMaterial.deleted_at.is_(None))
    ) or 0
    chapter_count = db.scalar(select(func.count(Chapter.id)).where(Chapter.course_id == course.id)) or 0
    lesson_count = db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id == course.id)) or 0
    data = _model_dict(course)
    data.update(
        {
            "teacher_name": teacher.nickname if teacher else "-",
            "student_count": int(student_count),
            "material_count": int(material_count),
            "chapter_count": int(chapter_count),
            "lesson_count": int(lesson_count),
        }
    )
    return data


def get_course_detail_admin(db: Session, *, course_id: int) -> dict:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    material_count = db.scalar(select(func.count(CourseMaterial.id)).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))) or 0
    from app.db.models import CourseMembership

    student_count = db.scalar(
        select(func.count(CourseMembership.id)).where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
    ) or 0
    students = [
        {
            "membership_id": membership.id,
            "user": _model_dict(student),
            "joined_at": membership.joined_at,
        }
        for membership, student in db.execute(
            select(CourseMembership, User)
            .join(User, User.id == CourseMembership.user_id)
            .where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
            .order_by(CourseMembership.joined_at.desc())
            .limit(20)
        )
    ]
    materials = [_model_dict(item) for item in db.scalars(select(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None)).order_by(CourseMaterial.created_at.desc()).limit(20))]
    lessons = [_model_dict(item) for item in db.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.created_at.desc()).limit(20))]
    operations = [
        _model_dict(item)
        for item in db.scalars(
            select(OperationLog)
            .where(OperationLog.target_type == "course", OperationLog.target_id == course_id)
            .order_by(OperationLog.created_at.desc())
            .limit(10)
        )
    ]
    return {
        "course": {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "term": course.term,
            "course_code": course.course_code,
            "teacher_id": course.teacher_id,
            "status": course.status,
        },
        "material_count": int(material_count),
        "student_count": int(student_count),
        "students": students,
        "materials": materials,
        "lessons": lessons,
        "operations": operations,
    }


def takeover_course(db: Session, *, course_id: int, teacher_id: int) -> Course:
    course = db.get(Course, course_id)
    teacher = db.get(User, teacher_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    if teacher is None or teacher.deleted_at is not None or teacher.role not in {UserRole.TEACHER.value, UserRole.ADMIN.value}:
        raise bad_request("新负责教师不存在或角色不合法")
    course.teacher_id = teacher_id
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def deactivate_course_admin(db: Session, *, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    course.status = CourseStatus.INACTIVE.value
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def activate_course_admin(db: Session, *, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    course.status = CourseStatus.ACTIVE.value
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_materials_admin(
    db: Session,
    *,
    category: str | None,
    keyword: str | None,
    material_type: str | None = None,
    teacher_id: int | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[CourseMaterial]:
    statement = select(CourseMaterial).where(CourseMaterial.deleted_at.is_(None))
    if category:
        statement = statement.where(CourseMaterial.category == category)
    if material_type:
        statement = statement.where(CourseMaterial.material_type == material_type)
    if teacher_id is not None:
        statement = statement.where(CourseMaterial.uploader_id == teacher_id)
    if start_at is not None:
        statement = statement.where(CourseMaterial.created_at >= start_at)
    if end_at is not None:
        statement = statement.where(CourseMaterial.created_at <= end_at)
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where((CourseMaterial.title.like(like)) | (CourseMaterial.original_filename.like(like)))
    return list(db.scalars(statement.order_by(CourseMaterial.created_at.desc())))


def material_summary_admin(db: Session, material: CourseMaterial) -> dict:
    course = db.get(Course, material.course_id)
    teacher = db.get(User, material.uploader_id)
    data = _model_dict(material)
    data.update(
        {
            "course_name": course.name if course else "-",
            "teacher_name": teacher.nickname if teacher else "-",
            "size_label": _human_size(material.size_bytes or 0),
        }
    )
    return data


def get_material_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None))) or 0
    ready = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None), CourseMaterial.parse_status == "ready")
    ) or 0
    failed = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None), CourseMaterial.parse_status == "failed")
    ) or 0
    by_category = {}
    for category, count in db.execute(
        select(CourseMaterial.category, func.count(CourseMaterial.id))
        .where(CourseMaterial.deleted_at.is_(None))
        .group_by(CourseMaterial.category)
    ):
        by_category[category] = count
    by_type = {
        material_type: count
        for material_type, count in db.execute(
            select(CourseMaterial.material_type, func.count(CourseMaterial.id))
            .where(CourseMaterial.deleted_at.is_(None))
            .group_by(CourseMaterial.material_type)
        )
    }
    by_teacher = {
        str(teacher_id): count
        for teacher_id, count in db.execute(
            select(CourseMaterial.uploader_id, func.count(CourseMaterial.id))
            .where(CourseMaterial.deleted_at.is_(None))
            .group_by(CourseMaterial.uploader_id)
        )
    }
    date_expr = func.date(CourseMaterial.created_at)
    by_day = {
        str(day): count
        for day, count in db.execute(
            select(date_expr, func.count(CourseMaterial.id))
            .where(CourseMaterial.deleted_at.is_(None))
            .group_by(date_expr)
            .order_by(date_expr.desc())
            .limit(30)
        )
    }
    month_start = _month_start()
    monthly_new = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None), CourseMaterial.created_at >= month_start)
    ) or 0
    storage_used = db.scalar(select(func.sum(CourseMaterial.size_bytes)).where(CourseMaterial.deleted_at.is_(None))) or 0
    local_used = _storage_usage_bytes()
    return {
        "total": int(total),
        "ready": int(ready),
        "failed": int(failed),
        "monthly_new": int(monthly_new),
        "storage_used_bytes": int(storage_used),
        "local_storage_used_bytes": int(local_used),
        "storage_used_label": _human_size(int(storage_used)),
        "storage_quota_bytes": 100 * 1024 * 1024 * 1024,
        "by_category": by_category,
        "by_type": by_type,
        "by_teacher": by_teacher,
        "by_day": by_day,
    }


def remove_material_admin(db: Session, *, material_id: int) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    vector_store.delete_material(db, course_id=material.course_id, material_id=material.id)
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.material_id == material.id))
    material.deleted_at = datetime.now(UTC)
    db.add(material)
    db.commit()


def _mask_service_config(config: dict) -> dict:
    masked = {}
    for key, value in config.items():
        if any(secret_key in key.lower() for secret_key in ["secret", "token", "key", "password"]):
            masked[key] = mask_secret(str(value))
        else:
            masked[key] = value
    return masked


def list_model_configs(db: Session) -> list[dict]:
    configs = list(db.scalars(select(ModelConfig).where(ModelConfig.deleted_at.is_(None)).order_by(ModelConfig.created_at.desc())))
    items = []
    for config in configs:
        items.append(
            {
                "id": config.id,
                "provider": config.provider,
                "model_name": config.model_name,
                "purpose": config.purpose,
                "endpoint": config.endpoint,
                "api_key": mask_secret(decrypt_secret(config.api_key_encrypted)) if config.api_key_encrypted else None,
                "is_default": config.is_default,
                "extra_config": config.extra_config,
            }
        )
    return items


def save_model_config(
    db: Session,
    *,
    config_id: int | None,
    provider: str,
    model_name: str,
    purpose: str,
    endpoint: str | None,
    api_key: str | None,
    is_default: bool,
    extra_config: dict | None,
) -> ModelConfig:
    config = db.get(ModelConfig, config_id) if config_id else ModelConfig()
    if config is None:
        raise not_found("模型配置不存在")
    config.provider = provider
    config.model_name = model_name
    config.purpose = purpose
    config.endpoint = endpoint
    config.api_key_encrypted = encrypt_secret(api_key) if api_key else config.api_key_encrypted
    config.is_default = is_default
    config.extra_config = extra_config
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def delete_model_config(db: Session, *, config_id: int) -> None:
    config = db.get(ModelConfig, config_id)
    if config is None or config.deleted_at is not None:
        raise not_found("模型配置不存在")
    config.deleted_at = datetime.now(UTC)
    db.add(config)
    db.commit()


def test_model_config(db: Session, *, config_id: int) -> dict:
    config = db.get(ModelConfig, config_id)
    if config is None or config.deleted_at is not None:
        raise not_found("模型配置不存在")
    if config.provider == "mock":
        return {"success": True, "message": "mock 模型配置可用"}
    if not config.endpoint:
        return {"success": False, "message": "缺少 endpoint"}
    headers = {"Content-Type": "application/json"}
    api_key = decrypt_secret(config.api_key_encrypted) if config.api_key_encrypted else None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    headers.update((config.extra_config or {}).get("headers") or {})
    endpoint = config.endpoint.rstrip("/")
    if config.purpose == "embedding":
        if not endpoint.endswith("/embeddings"):
            endpoint = f"{endpoint}/embeddings"
        payload = {"model": config.model_name, "input": ["连接测试"]}
        if (config.extra_config or {}).get("dimensions"):
            payload["dimensions"] = (config.extra_config or {})["dimensions"]
    else:
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"
        payload = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": "请回复 ok"}],
            "temperature": 0,
            "max_tokens": 8,
        }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(endpoint, headers=headers, json=payload)
        if response.status_code >= 400:
            return {"success": False, "message": f"HTTP {response.status_code}: {response.text[:200]}"}
        body = response.json()
        if config.purpose == "embedding":
            data = body.get("data") or []
            if not data or not isinstance(data[0].get("embedding") if isinstance(data[0], dict) else None, list):
                return {"success": False, "message": "响应中没有 embedding"}
        else:
            choices = body.get("choices") or []
            if not choices:
                return {"success": False, "message": "响应中没有 choices"}
        return {"success": True, "message": "模型配置可用"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def get_model_usage_stats(db: Session) -> dict:
    rows = list(
        db.execute(
            select(
                AIUsageLog.provider,
                func.count(AIUsageLog.id),
                func.sum(AIUsageLog.prompt_tokens),
                func.sum(AIUsageLog.completion_tokens),
                func.sum(AIUsageLog.estimated_cost),
            ).group_by(AIUsageLog.provider)
        ).all()
    )
    return {
        "items": [
            {
                "provider": provider,
                "call_count": call_count,
                "prompt_tokens": int(prompt_tokens or 0),
                "completion_tokens": int(completion_tokens or 0),
                "estimated_cost": float(estimated_cost or 0),
            }
            for provider, call_count, prompt_tokens, completion_tokens, estimated_cost in rows
        ]
    }


def list_service_configs(db: Session) -> list[dict]:
    configs = list(db.scalars(select(ServiceConfig).where(ServiceConfig.deleted_at.is_(None)).order_by(ServiceConfig.created_at.desc())))
    items = []
    for config in configs:
        raw = json.loads(decrypt_secret(config.config_encrypted))
        items.append(
            {
                "id": config.id,
                "scope": config.scope,
                "service_type": config.service_type,
                "provider": config.provider,
                "name": config.name,
                "is_enabled": config.is_enabled,
                "config": _mask_service_config(raw),
            }
        )
    return items


def save_service_config(
    db: Session,
    *,
    config_id: int | None,
    service_type: str,
    provider: str,
    name: str,
    config: dict,
    is_enabled: bool,
) -> ServiceConfig:
    record = db.get(ServiceConfig, config_id) if config_id else ServiceConfig()
    if record is None:
        raise not_found("服务配置不存在")
    normalized_config: dict = {}
    for key, value in config.items():
        if isinstance(value, str):
            value = value.strip()
        normalized_config[key] = value
    config = normalized_config
    if config_id and record.config_encrypted:
        existing = json.loads(decrypt_secret(record.config_encrypted))
        merged = dict(existing)
        for key, value in config.items():
            if value in {None, ""}:
                continue
            if isinstance(value, str) and "*" in value and key in existing:
                continue
            merged[key] = value
        config = merged
    if service_type == "oss" and provider in {"local", "mock"}:
        config = {
            key: value
            for key, value in config.items()
            if key in {"url_expire_hours"}
        }
    if provider == "aliyun":
        sdk_managed_keys = {
            "oss": {"endpoint"},
            "ocr": {"endpoint"},
            "doc_parser": {"endpoint"},
            "tts": {"token", "url"},
        }.get(service_type, set())
        for key in sdk_managed_keys:
            config.pop(key, None)
    if service_type == "doc_parser" and provider == "aliyun":
        try:
            timeout_seconds = int(config.get("timeout_seconds") or config.get("timeout") or DEFAULT_DOC_PARSER_TIMEOUT_SECONDS)
        except (TypeError, ValueError):
            timeout_seconds = DEFAULT_DOC_PARSER_TIMEOUT_SECONDS
        config["timeout_seconds"] = max(DEFAULT_DOC_PARSER_TIMEOUT_SECONDS, min(MAX_DOC_PARSER_TIMEOUT_SECONDS, timeout_seconds))
        try:
            poll_interval_seconds = int(config.get("poll_interval_seconds") or DEFAULT_DOC_PARSER_POLL_INTERVAL_SECONDS)
        except (TypeError, ValueError):
            poll_interval_seconds = DEFAULT_DOC_PARSER_POLL_INTERVAL_SECONDS
        config["poll_interval_seconds"] = max(1, min(60, poll_interval_seconds))
    record.scope = ConfigScope.SERVICE.value
    record.service_type = service_type
    record.provider = provider
    record.name = name
    record.is_enabled = is_enabled
    record.config_encrypted = encrypt_secret(json.dumps(config, ensure_ascii=False))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_service_config(db: Session, *, config_id: int) -> None:
    record = db.get(ServiceConfig, config_id)
    if record is None or record.deleted_at is not None:
        raise not_found("服务配置不存在")
    record.deleted_at = datetime.now(UTC)
    db.add(record)
    db.commit()


def test_service_config(db: Session, *, config_id: int) -> dict:
    record = db.get(ServiceConfig, config_id)
    if record is None or record.deleted_at is not None:
        raise not_found("服务配置不存在")
    config = json.loads(decrypt_secret(record.config_encrypted))
    if record.provider == "mock":
        return {"success": True, "message": "mock 服务配置可用"}
    if record.provider == "local":
        return {"success": True, "message": "本地存储可用"}
    required_keys = {
        "oss": ["access_key_id", "access_key_secret", "bucket"],
        "ocr": ["access_key_id", "access_key_secret"],
        "doc_parser": ["access_key_id", "access_key_secret"],
        "tts": ["access_key_id", "access_key_secret", "appkey", "voice"],
        "email": ["host", "port", "sender"],
    }.get(record.service_type, [])
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        return {"success": False, "message": f"缺少字段: {', '.join(missing)}"}
    if record.service_type == "oss":
        try:
            import oss2

            region = config.get("region")
            endpoint = storage_service._oss_endpoint(config)
            if region and config.get("signature_version", "v4") != "v1":
                auth = oss2.AuthV4(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"], region=region)
            else:
                auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"])
            bucket.get_bucket_info()
        except Exception as exc:
            return {"success": False, "message": f"OSS 连接失败: {exc}"}
        return {"success": True, "message": "OSS 配置可用"}
    if record.service_type == "email":
        return email_service.test_config(config)
    if record.service_type == "doc_parser":
        try:
            from alibabacloud_docmind_api20220711.client import Client as DocMindClient
            from alibabacloud_tea_openapi import models as openapi_models

            DocMindClient(
                openapi_models.Config(
                    access_key_id=config["access_key_id"],
                    access_key_secret=config["access_key_secret"],
                    endpoint="docmind-api.cn-hangzhou.aliyuncs.com",
                    region_id=config.get("region") or "cn-hangzhou",
                    type="access_key",
                )
            )
        except Exception as exc:
            return {"success": False, "message": f"文档解析 SDK 初始化失败: {exc}"}
        return {"success": True, "message": "文档解析配置字段完整"}
    if record.service_type == "tts":
        return tts_service.test_config(config)
    return {"success": True, "message": "配置字段完整"}


def get_service_health(db: Session) -> dict:
    settings = get_settings()
    items: list[dict] = []
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
        database_detail = "连接正常"
    except Exception as exc:
        database_status = "down"
        database_detail = str(exc)
    items.append({"key": "mysql", "name": "MySQL 数据库", "status": database_status, "metric": "SQL", "detail": database_detail})

    try:
        cache_client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        cache_client.ping()
        redis_status = "ok"
        redis_detail = "连接正常"
    except Exception as exc:
        redis_status = "down"
        redis_detail = str(exc)
    items.append({"key": "redis", "name": "Redis 缓存", "status": redis_status, "metric": "缓存", "detail": redis_detail})

    active_chunk_statement = (
        select(KnowledgeChunk.id)
        .outerjoin(CourseMaterial, CourseMaterial.id == KnowledgeChunk.material_id)
        .where(or_(KnowledgeChunk.material_id.is_(None), CourseMaterial.deleted_at.is_(None)))
    )
    active_chunk_ids = set(db.scalars(active_chunk_statement))
    chunk_count = len(active_chunk_ids)
    try:
        vector_ready = len(active_chunk_ids & vector_store.indexed_chunk_ids(db))
    except Exception:
        vector_ready = 0
    if not VECTOR_DIR.exists():
        vector_status = "down"
    elif chunk_count and vector_ready < chunk_count:
        vector_status = "processing"
    else:
        vector_status = "ok"
    items.append({"key": "vector", "name": "向量数据库", "status": vector_status, "metric": f"{vector_ready}/{chunk_count}", "detail": "Chroma"})

    try:
        broker_client = redis.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=2, socket_timeout=2)
        broker_client.ping()
        queue_length = int(broker_client.llen("celery"))
        celery_status = "processing" if queue_length > 50 else "ok"
        celery_detail = f"队列 {queue_length}"
    except Exception as exc:
        queue_length = None
        celery_status = "not_configured"
        celery_detail = str(exc)
    items.append({"key": "celery", "name": "Celery 队列", "status": celery_status, "metric": queue_length, "detail": celery_detail})

    service_by_type = {
        item.service_type: item
        for item in db.scalars(select(ServiceConfig).where(ServiceConfig.deleted_at.is_(None), ServiceConfig.is_enabled.is_(True)))
    }
    for service_type, name in [
        ("oss", "阿里云 OSS"),
        ("tts", "阿里云 TTS"),
        ("ocr", "阿里云 OCR"),
        ("doc_parser", "阿里云文档解析"),
        ("email", "邮件服务"),
    ]:
        config = service_by_type.get(service_type)
        if config is None:
            status = "not_configured"
            detail = "未配置"
            metric = "-"
        else:
            status = "ok" if config.provider in {"mock", "local"} else "configured"
            detail = config.name
            metric = config.provider
        items.append({"key": service_type, "name": name, "status": status, "metric": metric, "detail": detail})

    llm = db.scalar(
        select(ModelConfig)
        .where(ModelConfig.deleted_at.is_(None), ModelConfig.purpose != "embedding")
        .order_by(ModelConfig.is_default.desc(), ModelConfig.updated_at.desc())
    )
    items.append(
        {
            "key": "llm",
            "name": "当前 LLM",
            "status": "ok" if llm else "not_configured",
            "metric": llm.provider if llm else "-",
            "detail": llm.model_name if llm else "未配置",
        }
    )
    unhealthy = [item for item in items if item["status"] in {"down", "not_configured"} and item["key"] not in {"email"}]
    return {"status": "ok" if not unhealthy else "warning", "items": items, "checked_at": datetime.now(UTC).isoformat()}


def test_all_services(db: Session) -> dict:
    results = []
    for config in db.scalars(select(ServiceConfig).where(ServiceConfig.deleted_at.is_(None), ServiceConfig.is_enabled.is_(True))):
        result = test_service_config(db, config_id=config.id)
        results.append({"type": config.service_type, "name": config.name, **result})
    for config in db.scalars(select(ModelConfig).where(ModelConfig.deleted_at.is_(None), ModelConfig.is_default.is_(True))):
        result = test_model_config(db, config_id=config.id)
        results.append({"type": f"model:{config.purpose}", "name": config.model_name, **result})
    return {"success": all(item["success"] for item in results) if results else False, "items": results, "checked_at": datetime.now(UTC).isoformat()}


def list_system_settings(db: Session) -> list[dict]:
    return [
        {
            "id": item.id,
            "category": item.category,
            "setting_key": item.setting_key,
            "setting_value": item.setting_value,
            "description": item.description,
        }
        for item in db.scalars(select(SystemSetting).order_by(SystemSetting.setting_key))
    ]


def update_system_setting(db: Session, *, key: str, value) -> SystemSetting:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == key))
    if setting is None:
        setting = SystemSetting(setting_key=key)
    setting.setting_value = value
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def restore_default_system_settings(db: Session) -> list[dict]:
    defaults = default_system_settings()
    for key, (value, description, category) in defaults.items():
        setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == key))
        if setting is None:
            setting = SystemSetting(setting_key=key)
        setting.setting_value = value
        setting.description = description
        setting.category = category
        db.add(setting)
    db.commit()
    return list_system_settings(db)


def get_monitoring_overview(db: Session) -> dict:
    since = datetime.now(UTC) - timedelta(minutes=30)
    online_users = db.scalar(select(func.count(User.id)).where(User.last_seen_at >= since, User.deleted_at.is_(None))) or 0
    api_call_count = db.scalar(select(func.count(ApiRequestLog.id)).where(ApiRequestLog.created_at >= since)) or 0
    ai_calls = db.scalar(select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= since)) or 0
    ai_failures = db.scalar(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= since, AIUsageLog.success.is_(False))
    ) or 0
    queue_pending = db.scalar(select(func.count(AsyncTaskLog.id)).where(AsyncTaskLog.status.in_(["pending", "processing"]))) or 0
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "down"
    cache_status = "not_configured"
    celery_queue_length: int | None = None
    settings = get_settings()
    try:
        cache_client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        cache_client.ping()
        cache_status = "ok"
    except Exception:
        cache_status = "down"
    try:
        broker_client = redis.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=2, socket_timeout=2)
        broker_client.ping()
        celery_queue_length = int(broker_client.llen("celery"))
    except Exception:
        celery_queue_length = None
    return {
        "online_users": int(online_users),
        "api_call_count_30m": int(api_call_count),
        "ai_call_count_30m": int(ai_calls),
        "ai_failure_count_30m": int(ai_failures),
        "async_queue_pending": int(queue_pending),
        "celery_queue_length": celery_queue_length,
        "database_status": database_status,
        "cache_status": cache_status,
    }


def get_monitoring_timeseries(db: Session) -> dict:
    now = datetime.now(UTC)
    points = []
    for index in range(29, -1, -1):
        start = now - timedelta(minutes=index + 1)
        end = now - timedelta(minutes=index)
        online = db.scalar(select(func.count(distinct(LoginLog.user_id))).where(LoginLog.created_at >= start, LoginLog.created_at < end)) or 0
        api_calls = db.scalar(select(func.count(ApiRequestLog.id)).where(ApiRequestLog.created_at >= start, ApiRequestLog.created_at < end)) or 0
        ai_calls = db.scalar(select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= start, AIUsageLog.created_at < end)) or 0
        ai_failures = db.scalar(
            select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= start, AIUsageLog.created_at < end, AIUsageLog.success.is_(False))
        ) or 0
        points.append(
            {
                "time": end.strftime("%H:%M"),
                "online_users": int(online),
                "api_calls": int(api_calls),
                "ai_calls": int(ai_calls),
                "ai_failure_rate": round((int(ai_failures) / int(ai_calls) * 100) if ai_calls else 0, 2),
            }
        )
    return {"points": points}


def get_admin_dashboard(db: Session, activity_days: int = 30) -> dict:
    activity_days = 90 if activity_days == 90 else 7 if activity_days == 7 else 30
    day_start = _day_start()
    users_total = db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0
    active_courses = db.scalar(select(func.count(Course.id)).where(Course.deleted_at.is_(None), Course.status == CourseStatus.ACTIVE.value)) or 0
    today_ai_calls = db.scalar(select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= day_start)) or 0
    queue_pending = db.scalar(select(func.count(AsyncTaskLog.id)).where(AsyncTaskLog.status.in_(["pending", "processing"]))) or 0

    activity = []
    now = datetime.now(UTC)
    for offset in range(activity_days - 1, -1, -1):
        start = (now - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        active_users = db.scalar(select(func.count(distinct(LoginLog.user_id))).where(LoginLog.created_at >= start, LoginLog.created_at < end)) or 0
        ai_calls = db.scalar(select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= start, AIUsageLog.created_at < end)) or 0
        activity.append({"date": start.strftime("%m-%d"), "active_users": int(active_users), "ai_calls": int(ai_calls)})

    ai_distribution = [
        {"module": module or "unknown", "count": int(count)}
        for module, count in db.execute(select(AIUsageLog.module, func.count(AIUsageLog.id)).group_by(AIUsageLog.module))
    ]
    course_ranking = [
        {"course_id": course_id, "name": name, "active_users": int(count)}
        for course_id, name, count in db.execute(
            select(Course.id, Course.name, func.count(CourseMembership.id))
            .join(CourseMembership, CourseMembership.course_id == Course.id, isouter=True)
            .where(Course.deleted_at.is_(None))
            .group_by(Course.id, Course.name)
            .order_by(func.count(CourseMembership.id).desc())
            .limit(5)
        )
    ]
    recent_users = [_model_dict(item) for item in db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).limit(5))]
    recent_operations = [_model_dict(item) for item in db.scalars(select(OperationLog).order_by(OperationLog.created_at.desc()).limit(8))]
    pending_tasks = []
    pending_materials = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None), CourseMaterial.parse_status.in_(["pending", "processing", "failed"]))
    ) or 0
    if pending_materials:
        pending_tasks.append({"type": "warning", "title": f"资料处理 {int(pending_materials)} 条", "level": "高"})
    if queue_pending:
        pending_tasks.append({"type": "warning", "title": f"队列积压 {int(queue_pending)} 条", "level": "中"})
    return {
        "stats": {
            "users_total": int(users_total),
            "active_courses": int(active_courses),
            "today_ai_calls": int(today_ai_calls),
            "async_pending": int(queue_pending),
        },
        "activity_trend": activity,
        "ai_distribution": ai_distribution,
        "service_health": get_service_health(db),
        "recent_operations": recent_operations,
        "course_ranking": course_ranking,
        "recent_users": recent_users,
        "pending_tasks": pending_tasks,
    }


def list_login_logs(
    db: Session,
    *,
    limit: int = 100,
    user_id: int | None = None,
    success: bool | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[LoginLog]:
    statement = select(LoginLog)
    if user_id is not None:
        statement = statement.where(LoginLog.user_id == user_id)
    if success is not None:
        statement = statement.where(LoginLog.success.is_(success))
    if start_at is not None:
        statement = statement.where(LoginLog.created_at >= start_at)
    if end_at is not None:
        statement = statement.where(LoginLog.created_at <= end_at)
    return list(db.scalars(statement.order_by(LoginLog.created_at.desc()).limit(limit)))


def list_operation_logs(
    db: Session,
    *,
    limit: int = 100,
    user_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[OperationLog]:
    statement = select(OperationLog)
    if user_id is not None:
        statement = statement.where(OperationLog.user_id == user_id)
    if action:
        statement = statement.where(OperationLog.action == action)
    if target_type:
        statement = statement.where(OperationLog.target_type == target_type)
    if start_at is not None:
        statement = statement.where(OperationLog.created_at >= start_at)
    if end_at is not None:
        statement = statement.where(OperationLog.created_at <= end_at)
    return list(db.scalars(statement.order_by(OperationLog.created_at.desc()).limit(limit)))


def list_error_logs(
    db: Session,
    *,
    limit: int = 100,
    level: str | None = None,
    source: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[SystemErrorLog]:
    statement = select(SystemErrorLog)
    statement = statement.where(SystemErrorLog.detail["resolved"].as_boolean().is_not(True))
    if level:
        statement = statement.where(SystemErrorLog.level == level)
    if source:
        like = f"%{source}%"
        statement = statement.where(SystemErrorLog.source.like(like))
    if start_at is not None:
        statement = statement.where(SystemErrorLog.created_at >= start_at)
    if end_at is not None:
        statement = statement.where(SystemErrorLog.created_at <= end_at)
    return list(db.scalars(statement.order_by(SystemErrorLog.created_at.desc()).limit(limit)))


def _database_path_from_sqlite_url(database_url: str) -> Path:
    if database_url.startswith("sqlite:////"):
        return Path(database_url.removeprefix("sqlite:///"))
    return Path(database_url.removeprefix("sqlite:///"))


def _copy_vectors(target_dir: Path) -> None:
    if VECTOR_DIR.exists():
        shutil.copytree(VECTOR_DIR, target_dir / "vectors", dirs_exist_ok=True)


def _make_zip(source_dir: Path, target_zip: Path) -> Path:
    archive_base = target_zip.with_suffix("")
    archive_path = shutil.make_archive(archive_base.as_posix(), "zip", source_dir)
    return Path(archive_path)


def _mysql_command_args(url, command: str) -> list[str]:
    args = [command]
    if url.host:
        args.extend(["-h", url.host])
    if url.port:
        args.extend(["-P", str(url.port)])
    if url.username:
        args.extend(["-u", url.username])
    if url.password:
        args.append(f"-p{url.password}")
    if url.database:
        args.append(url.database)
    return args


def create_backup(db: Session, *, trigger_user_id: int | None) -> BackupRecord:
    record = BackupRecord(trigger_user_id=trigger_user_id, status=BackupStatus.PENDING.value)
    db.add(record)
    db.commit()
    db.refresh(record)
    temp_root: Path | None = None
    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        bind_url = db.get_bind().url
        database_url = bind_url.render_as_string(hide_password=False)
        temp_root = Path(tempfile.mkdtemp(prefix=f"backup_{timestamp}_", dir=BACKUP_DIR))
        if database_url.startswith("sqlite:///"):
            source = _database_path_from_sqlite_url(database_url)
            shutil.copy2(source, temp_root / "database.db")
        else:
            dump_target = temp_root / "database.sql"
            with dump_target.open("wb") as output:
                subprocess.run(_mysql_command_args(bind_url, "mysqldump"), stdout=output, check=True, timeout=300)
        (temp_root / "metadata.json").write_text(
            json.dumps({"database": "sqlite" if database_url.startswith("sqlite:///") else "mysql"}, ensure_ascii=False),
            encoding="utf-8",
        )
        _copy_vectors(temp_root)
        target = _make_zip(temp_root, BACKUP_DIR / f"backup_{timestamp}.zip")
        shutil.rmtree(temp_root, ignore_errors=True)
        record.file_path = target.as_posix()
        record.status = BackupStatus.SUCCESS.value
    except Exception as exc:
        record.status = BackupStatus.FAILED.value
        record.detail = {"error": str(exc)}
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_backups(db: Session) -> list[BackupRecord]:
    return list(db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc())))


def get_backup_summary(db: Session) -> dict:
    backups = list_backups(db)
    total_size = 0
    for item in backups:
        if item.file_path and Path(item.file_path).exists():
            total_size += Path(item.file_path).stat().st_size
    last = backups[0] if backups else None
    return {
        "last_backup": _model_dict(last) if last else None,
        "backup_count": len(backups),
        "total_size_bytes": total_size,
        "total_size_label": _human_size(total_size),
        "oldest_at": backups[-1].created_at if backups else None,
    }


def verify_backup(db: Session, *, backup_id: int) -> dict:
    record = db.get(BackupRecord, backup_id)
    if record is None:
        raise not_found("备份不存在")
    ok = bool(record.file_path and Path(record.file_path).exists())
    if ok and str(record.file_path).endswith(".zip"):
        try:
            with zipfile.ZipFile(record.file_path) as archive:
                bad = archive.testzip()
            ok = bad is None
        except Exception:
            ok = False
    record.detail = {**(record.detail or {}), "verified_at": datetime.now(UTC).isoformat(), "verified": ok}
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": ok, "message": "备份正常" if ok else "备份损坏或缺失", "id": record.id}


def delete_backup(db: Session, *, backup_id: int) -> None:
    record = db.get(BackupRecord, backup_id)
    if record is None:
        raise not_found("备份不存在")
    if record.file_path:
        Path(record.file_path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()


def mark_error_log_resolved(db: Session, *, error_id: int, resolved: bool = True) -> dict:
    record = db.get(SystemErrorLog, error_id)
    if record is None:
        raise not_found("错误日志不存在")
    record.detail = {**(record.detail or {}), "resolved": resolved, "resolved_at": datetime.now(UTC).isoformat() if resolved else None}
    db.add(record)
    db.commit()
    db.refresh(record)
    payload = _model_dict(record)
    if resolved:
        db.delete(record)
        db.commit()
    return payload


def restore_backup(db: Session, *, backup_id: int) -> dict:
    record = db.get(BackupRecord, backup_id)
    if record is None or not record.file_path:
        raise not_found("备份不存在")
    backup_path = Path(record.file_path)
    if not backup_path.exists():
        raise not_found("备份文件不存在")
    bind_url = db.get_bind().url
    database_url = bind_url.render_as_string(hide_password=False)
    temp_root = Path(tempfile.mkdtemp(prefix=f"restore_{record.id}_", dir=BACKUP_DIR))
    try:
        if backup_path.suffix == ".zip":
            with zipfile.ZipFile(backup_path) as archive:
                archive.extractall(temp_root)
            sqlite_backup = temp_root / "database.db"
            mysql_backup = temp_root / "database.sql"
            vector_backup = temp_root / "vectors"
            if database_url.startswith("sqlite:///") and sqlite_backup.exists():
                shutil.copy2(sqlite_backup, _database_path_from_sqlite_url(database_url))
            elif mysql_backup.exists():
                with mysql_backup.open("rb") as input_file:
                    subprocess.run(_mysql_command_args(bind_url, "mysql"), stdin=input_file, check=True, timeout=300)
            else:
                raise bad_request("备份文件与当前数据库类型不匹配")
            if vector_backup.exists():
                if VECTOR_DIR.exists():
                    shutil.rmtree(VECTOR_DIR)
                shutil.copytree(vector_backup, VECTOR_DIR)
        elif database_url.startswith("sqlite:///") and backup_path.suffix == ".db":
            shutil.copy2(backup_path, _database_path_from_sqlite_url(database_url))
        else:
            raise bad_request("不支持的备份文件格式")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return {"success": True, "message": "备份已恢复，请重启 API 与 Celery 服务使连接重新加载"}
