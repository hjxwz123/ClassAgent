from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BACKUP_DIR, get_settings
from app.core.enums import BackupStatus, ConfigScope, CourseStatus, UserRole, UserStatus
from app.core.errors import bad_request, forbidden, not_found
from app.core.security import decrypt_secret, encrypt_secret, hash_password, mask_secret
from app.db.models import (
    AIUsageLog,
    ApiRequestLog,
    AsyncTaskLog,
    BackupRecord,
    Course,
    CourseMaterial,
    LoginLog,
    ModelConfig,
    OperationLog,
    ServiceConfig,
    SystemErrorLog,
    SystemSetting,
    User,
)


def assert_admin(user: User) -> None:
    if user.role != UserRole.ADMIN.value:
        raise forbidden("仅管理员可执行该操作")


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


def create_admin_user(db: Session, *, email: str, password: str, nickname: str) -> User:
    exists = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if exists is not None:
        raise bad_request("邮箱已存在")
    admin = User(
        email=email,
        password_hash=hash_password(password),
        nickname=nickname,
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


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
        user.role = role
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


def get_course_detail_admin(db: Session, *, course_id: int) -> dict:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("课程不存在")
    material_count = db.scalar(select(func.count(CourseMaterial.id)).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))) or 0
    from app.db.models import CourseMembership

    student_count = db.scalar(
        select(func.count(CourseMembership.id)).where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
    ) or 0
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


def list_materials_admin(db: Session, *, category: str | None, keyword: str | None) -> list[CourseMaterial]:
    statement = select(CourseMaterial).where(CourseMaterial.deleted_at.is_(None))
    if category:
        statement = statement.where(CourseMaterial.category == category)
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where((CourseMaterial.title.like(like)) | (CourseMaterial.original_filename.like(like)))
    return list(db.scalars(statement.order_by(CourseMaterial.created_at.desc())))


def get_material_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None))) or 0
    by_category = {}
    for category, count in db.execute(
        select(CourseMaterial.category, func.count(CourseMaterial.id))
        .where(CourseMaterial.deleted_at.is_(None))
        .group_by(CourseMaterial.category)
    ):
        by_category[category] = count
    return {"total": int(total), "by_category": by_category}


def remove_material_admin(db: Session, *, material_id: int) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
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
    endpoint = config.endpoint.rstrip("/")
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


def test_service_config(db: Session, *, config_id: int) -> dict:
    record = db.get(ServiceConfig, config_id)
    if record is None or record.deleted_at is not None:
        raise not_found("服务配置不存在")
    config = json.loads(decrypt_secret(record.config_encrypted))
    if record.provider == "mock":
        return {"success": True, "message": "mock 服务配置可用"}
    if record.service_type == "storage" and record.provider == "local":
        return {"success": True, "message": "本地存储可用"}
    required_keys = {
        "oss": ["access_key_id", "access_key_secret", "endpoint", "bucket"],
        "ocr": ["access_key_id", "access_key_secret", "endpoint", "region"],
        "tts": ["appkey", "token", "url", "voice"],
    }.get(record.service_type, [])
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        return {"success": False, "message": f"缺少字段: {', '.join(missing)}"}
    if record.service_type == "oss":
        try:
            import oss2

            region = config.get("region")
            if region and config.get("signature_version", "v4") != "v1":
                auth = oss2.AuthV4(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, config["endpoint"], config["bucket"], region=region)
            else:
                auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, config["endpoint"], config["bucket"])
            bucket.get_bucket_info()
        except Exception as exc:
            return {"success": False, "message": f"OSS 连接失败: {exc}"}
        return {"success": True, "message": "OSS 配置可用"}
    return {"success": True, "message": "配置字段完整"}


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


def get_monitoring_overview(db: Session) -> dict:
    since = datetime.now(UTC) - timedelta(minutes=30)
    online_users = db.scalar(select(func.count(User.id)).where(User.last_seen_at >= since, User.deleted_at.is_(None))) or 0
    api_call_count = db.scalar(select(func.count(ApiRequestLog.id)).where(ApiRequestLog.created_at >= since)) or 0
    ai_calls = db.scalar(select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= since)) or 0
    ai_failures = db.scalar(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.created_at >= since, AIUsageLog.success.is_(False))
    ) or 0
    queue_pending = db.scalar(
        select(func.count(AsyncTaskLog.id)).where(AsyncTaskLog.status.in_(["pending", "processing"]))
    ) or 0
    return {
        "online_users": int(online_users),
        "api_call_count_30m": int(api_call_count),
        "ai_call_count_30m": int(ai_calls),
        "ai_failure_count_30m": int(ai_failures),
        "async_queue_pending": int(queue_pending),
        "database_status": "ok",
        "cache_status": "configured" if get_settings().redis_url else "not_configured",
    }


def list_login_logs(db: Session, *, limit: int = 100) -> list[LoginLog]:
    return list(db.scalars(select(LoginLog).order_by(LoginLog.created_at.desc()).limit(limit)))


def list_operation_logs(db: Session, *, limit: int = 100) -> list[OperationLog]:
    return list(db.scalars(select(OperationLog).order_by(OperationLog.created_at.desc()).limit(limit)))


def list_error_logs(db: Session, *, limit: int = 100) -> list[SystemErrorLog]:
    return list(db.scalars(select(SystemErrorLog).order_by(SystemErrorLog.created_at.desc()).limit(limit)))


def create_backup(db: Session, *, trigger_user_id: int | None) -> BackupRecord:
    record = BackupRecord(trigger_user_id=trigger_user_id, status=BackupStatus.PENDING.value)
    db.add(record)
    db.commit()
    db.refresh(record)
    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        database_url = db.get_bind().url.render_as_string(hide_password=False)
        if database_url.startswith("sqlite:///"):
            source = Path(database_url.removeprefix("sqlite:///"))
            target = BACKUP_DIR / f"backup_{timestamp}.db"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            record.file_path = target.as_posix()
        else:
            target = BACKUP_DIR / f"backup_{timestamp}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"database_url": database_url}), encoding="utf-8")
            record.file_path = target.as_posix()
        record.status = BackupStatus.SUCCESS.value
    except Exception as exc:
        record.status = BackupStatus.FAILED.value
        record.detail = {"error": str(exc)}
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_backups(db: Session) -> list[BackupRecord]:
    return list(db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc())))
