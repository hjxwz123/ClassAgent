from sqlalchemy.orm import Session

from app.db.models import AIUsageLog


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
    db.add(
        AIUsageLog(
            user_id=user_id,
            course_id=course_id,
            module=module,
            provider="mock",
            model_name="mock-v1",
            prompt_tokens=max(1, prompt_chars // 4) if prompt_chars else 0,
            completion_tokens=max(1, completion_chars // 4) if completion_chars else 0,
            estimated_cost=0,
            success=success,
            error_message=error_message,
        )
    )
