from sqlalchemy.orm import Session

from app.db.models import AIUsageLog
from app.services.runtime_config import get_default_model_config


MODULE_PURPOSE_MAP = {
    "material_pipeline": "script",
    "qa": "qa",
    "tutoring_analysis": "tutoring",
    "tutoring_guidance": "tutoring",
    "quiz_generation": "quiz",
    "study_plan": "study_plan",
    "teaching_analysis": "analysis",
}


def log_ai_usage(
    db: Session,
    *,
    module: str,
    user_id: int | None = None,
    course_id: int | None = None,
    prompt_chars: int = 0,
    completion_chars: int = 0,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    purpose = MODULE_PURPOSE_MAP.get(module, "general")
    model_config = get_default_model_config(db, purpose)
    db.add(
        AIUsageLog(
            user_id=user_id,
            course_id=course_id,
            module=module,
            provider=model_config.provider if model_config else "local",
            model_name=model_config.model_name if model_config else "fallback",
            prompt_tokens=max(1, prompt_chars // 4) if prompt_chars else 0,
            completion_tokens=max(1, completion_chars // 4) if completion_chars else 0,
            estimated_cost=0,
            success=success,
            error_message=error_message,
        )
    )
