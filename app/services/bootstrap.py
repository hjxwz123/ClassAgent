from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.db.models import SystemSetting, User


def ensure_default_admin(db: Session) -> None:
    settings = get_settings()
    admin = db.scalar(select(User).where(User.email == settings.admin_default_email))
    if admin is not None:
        return
    admin = User(
        email=settings.admin_default_email,
        password_hash=hash_password(settings.admin_default_password),
        nickname=settings.admin_default_name,
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(admin)
    db.commit()


def ensure_system_settings(db: Session) -> None:
    settings = get_settings()
    default_settings = {
        "upload.max_size_mb": settings.default_upload_limit_mb,
        "course.material.max_count": settings.max_course_materials,
        "lesson.script.max_length": settings.script_max_length,
        "qa.context.turn_limit": settings.qa_context_turn_limit,
        "quiz.default_question_count": settings.quiz_default_question_count,
        "tutoring.default_release_level": settings.tutoring_default_release_level,
        "tts.default_voice": settings.default_tts_voice,
        "tts.default_rate": settings.default_tts_rate,
        "tts.default_volume": settings.default_tts_volume,
        "system.announcement": "",
        "backup.schedule": {"enabled": False, "cron": "0 3 * * *"},
    }
    existing_keys = {
        row[0]
        for row in db.execute(select(SystemSetting.setting_key).where(SystemSetting.setting_key.in_(default_settings.keys())))
    }
    for key, value in default_settings.items():
        if key in existing_keys:
            continue
        db.add(SystemSetting(setting_key=key, setting_value=value, description="系统初始化默认参数"))
    db.commit()
