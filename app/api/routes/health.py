from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.responses import success_response
from app.db.session import SessionLocal


router = APIRouter()


@router.get("")
def health_check():
    settings = get_settings()
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return success_response(
        data={
            "service": settings.app_name,
            "environment": settings.app_env,
            "time": datetime.now(UTC).isoformat(),
        }
    )
