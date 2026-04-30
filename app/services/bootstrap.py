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
        "upload.max_size_mb": (settings.default_upload_limit_mb, "单文件上传上限，单位 MB"),
        "course.material.max_count": (settings.max_course_materials, "单课程资料数量上限"),
        "lesson.script.max_length": (settings.script_max_length, "课堂讲解脚本最大长度"),
        "qa.context.turn_limit": (settings.qa_context_turn_limit, "问答多轮上下文轮数"),
        "quiz.default_question_count": (settings.quiz_default_question_count, "默认测验题量"),
        "tutoring.default_release_level": (settings.tutoring_default_release_level, "题目辅导默认开放级别"),
        "tts.default_voice": (settings.default_tts_voice, "默认 TTS 音色"),
        "tts.default_rate": (settings.default_tts_rate, "默认 TTS 语速"),
        "tts.default_volume": (settings.default_tts_volume, "默认 TTS 音量"),
        "system.announcement": ("", "系统公告内容"),
        "backup.schedule": ({"enabled": False, "cron": "0 3 * * *"}, "数据库定期备份计划"),
    }
    existing = {
        item.setting_key: item
        for item in db.scalars(select(SystemSetting).where(SystemSetting.setting_key.in_(default_settings.keys())))
    }
    for key, (value, description) in default_settings.items():
        setting = existing.get(key)
        if setting is not None:
            if setting.description in {None, "", "系统初始化默认参数"}:
                setting.description = description
                db.add(setting)
            continue
        db.add(SystemSetting(setting_key=key, setting_value=value, description=description))
    db.commit()
