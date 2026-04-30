from sqlalchemy.orm import Session

from app.db.models import LoginLog, OperationLog


def log_operation(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    target_type: str,
    target_id: int | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        OperationLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


def log_login(
    db: Session,
    *,
    user_id: int,
    login_ip: str | None,
    user_agent: str | None,
    success: bool = True,
) -> None:
    db.add(
        LoginLog(
            user_id=user_id,
            login_ip=login_ip,
            user_agent=user_agent,
            success=success,
        )
    )
