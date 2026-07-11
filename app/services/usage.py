import logging

from sqlalchemy.orm import Session

from app.db.models import AIUsageLog
from app.services.runtime_config import get_default_model_config

logger = logging.getLogger(__name__)


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
    # AI 使用日志纯属分析/计量用途，绝不能因它写失败（表缺失、瞬时 DB 错误等）拖垮已完成的
    # 主操作（出题/问答/资料处理等）。用【独立 session】写入并单独提交：
    #  1) 与调用方事务完全解耦——不 flush 调用方 db 的待写对象（调用方 autoflush=False，
    #     很多流程刻意把 INSERT 推迟到自己的 commit 处理并发唯一约束，如题目辅导的并发插入回退；
    #     若在这里提前 flush 会窃取那个 IntegrityError 并把 session 打成 pending-rollback）；
    #  2) 写失败只影响这条日志，捕获后记告警即可。
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as log_db:
            purpose = MODULE_PURPOSE_MAP.get(module, "general")
            model_config = get_default_model_config(log_db, purpose)
            log_db.add(
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
            log_db.commit()
    except Exception:
        logger.warning("AI 使用日志写入失败（已忽略，不影响主流程）module=%s", module, exc_info=True)
