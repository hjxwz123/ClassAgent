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
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import BACKUP_DIR, VECTOR_DIR, get_settings
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
from app.services.email import email_service
from app.services.vector_store import vector_store


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


def get_material_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(CourseMaterial.id)).where(CourseMaterial.deleted_at.is_(None))) or 0
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
    return {"total": int(total), "by_category": by_category, "by_type": by_type, "by_teacher": by_teacher, "by_day": by_day}


def remove_material_admin(db: Session, *, material_id: int) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    vector_store.delete_material(db, course_id=material.course_id, material_id=material.id)
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
        "email": ["host", "port", "sender"],
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
    if record.service_type == "email":
        return email_service.test_config(config)
    if record.service_type == "tts":
        try:
            payload = {
                "appkey": config["appkey"],
                "token": config["token"],
                "text": "连接测试",
                "format": str(config.get("format") or "wav").lower(),
                "sample_rate": int(config.get("sample_rate") or 16000),
                "voice": config.get("voice") or get_settings().default_tts_voice,
                "speech_rate": int(config.get("speech_rate", get_settings().default_tts_rate)),
                "volume": int(config.get("volume", get_settings().default_tts_volume)),
            }
            with httpx.Client(timeout=get_settings().external_service_timeout_seconds) as client:
                if str(config.get("method", "GET")).upper() == "POST":
                    response = client.post(str(config["url"]), json=payload)
                else:
                    response = client.get(str(config["url"]), params=payload)
            content_type = response.headers.get("content-type", "")
            if response.status_code >= 400 or "json" in content_type.lower():
                return {"success": False, "message": f"TTS 连接失败: {response.text[:200]}"}
        except Exception as exc:
            return {"success": False, "message": f"TTS 连接失败: {exc}"}
        return {"success": True, "message": "TTS 配置可用"}
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


def delete_backup(db: Session, *, backup_id: int) -> None:
    record = db.get(BackupRecord, backup_id)
    if record is None:
        raise not_found("备份不存在")
    if record.file_path:
        Path(record.file_path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()


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
