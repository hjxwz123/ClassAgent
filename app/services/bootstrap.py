from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.db.models import SystemSetting, User


def default_system_settings() -> dict[str, tuple[object, str, str]]:
    settings = get_settings()
    return {
        "upload.max_size_mb": (settings.default_upload_limit_mb, "单文件上传上限，单位 MB", "upload"),
        "upload.allowed_types": (["ppt", "pptx", "pdf", "doc", "docx", "txt"], "允许上传的资料格式", "upload"),
        "upload.max_files_once": (5, "单次最多上传文件数量", "upload"),
        "course.material.max_count": (settings.max_course_materials, "单课程资料数量上限", "upload"),
        "qa.context.turn_limit": (settings.qa_context_turn_limit, "问答多轮上下文轮数", "ai"),
        "qa.out_of_scope_policy": ("answer_with_notice", "超出课程范围时的回答策略", "ai"),
        "qa.max_answer_tokens": (2048, "问答回答最大 Token 数", "ai"),
        "qa.source_limit": (3, "问答引用来源最多条数", "ai"),
        "tutoring.default_release_level": (settings.tutoring_default_release_level, "题目辅导默认开放级别", "ai"),
        "lesson.script.max_length": (settings.script_max_length, "课堂讲解脚本最大长度", "classroom"),
        "tts.default_voice": (settings.default_tts_voice, "默认 TTS 音色", "classroom"),
        "tts.default_rate": (settings.default_tts_rate, "默认 TTS 语速", "classroom"),
        "tts.default_volume": (settings.default_tts_volume, "默认 TTS 音量", "classroom"),
        "subtitle.sync_tolerance_ms": (200, "字幕同步延迟容忍毫秒数", "classroom"),
        "quiz.default_question_count": (settings.quiz_default_question_count, "默认测验题量", "quiz"),
        "quiz.question_ratio": ({"choice": 50, "judge": 30, "short": 20}, "默认题型比例", "quiz"),
        "quiz.practice_show_answer": (True, "练习模式作答后是否立即显示答案", "quiz"),
        "quiz.exam_show_answer": (True, "测验交卷后是否显示答案", "quiz"),
        "system.announcement": ("", "系统公告内容", "interface"),
        "system.announcement_enabled": (False, "是否启用系统公告", "interface"),
        "system.announcement_scope": ("all", "公告展示对象", "interface"),
        "system.logo_url": ("", "平台 Logo 地址", "interface"),
        "backup.schedule": ({"enabled": False, "frequency": "daily", "time": "03:00", "retention": 30}, "数据库定期备份计划", "backup"),
        "backup.notify_email": ("", "备份失败通知邮箱", "backup"),
    }


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
    default_settings = default_system_settings()
    existing = {
        item.setting_key: item
        for item in db.scalars(select(SystemSetting).where(SystemSetting.setting_key.in_(default_settings.keys())))
    }
    for key, (value, description, category) in default_settings.items():
        setting = existing.get(key)
        if setting is not None:
            if setting.description in {None, "", "系统初始化默认参数"}:
                setting.description = description
            if setting.category in {None, "", "system"}:
                setting.category = category
            db.add(setting)
            continue
        db.add(SystemSetting(setting_key=key, setting_value=value, description=description, category=category))
    db.commit()
