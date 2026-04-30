from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.services.analytics import get_course_analytics


router = APIRouter()


@router.get("/courses/{course_id}")
def get_course_analytics_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    payload = get_course_analytics(db, course_id=course_id, user=user, days=days)
    return success_response(data=payload, request_id=request.state.request_id)
