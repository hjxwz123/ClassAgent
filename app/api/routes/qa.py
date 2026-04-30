from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.qa import QAAskRequest, QAFeedbackRequest, QAFavoriteRequest, QAHistoryItem, QAResponse
from app.services.qa import ask_question, list_history, update_favorite, update_feedback


router = APIRouter()


@router.post("/ask")
def ask_question_endpoint(
    payload: QAAskRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    record = ask_question(db, user=user, payload=payload)
    response = QAResponse(
        conversation_id=record.conversation_id,
        record_id=record.id,
        question=record.question,
        answer=record.answer,
        is_out_of_scope=record.is_out_of_scope,
        sources=record.sources or [],
    )
    return success_response(data=response.model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/history")
def get_history_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    items = [QAHistoryItem.model_validate(item).model_dump(mode="json") for item in list_history(db, user=user, course_id=course_id, keyword=keyword)]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/{record_id}/favorite")
def favorite_endpoint(
    record_id: int,
    payload: QAFavoriteRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    record = update_favorite(db, record_id=record_id, user=user, is_favorite=payload.is_favorite)
    return success_response(data=QAHistoryItem.model_validate(record).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/{record_id}/feedback")
def feedback_endpoint(
    record_id: int,
    payload: QAFeedbackRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    record = update_feedback(
        db,
        record_id=record_id,
        user=user,
        feedback=payload.feedback,
        feedback_comment=payload.feedback_comment,
    )
    return success_response(data=QAHistoryItem.model_validate(record).model_dump(mode="json"), request_id=request.state.request_id)
