import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimitRule, limit_request
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.qa import QAAskRequest, QAFeedbackRequest, QAFavoriteRequest, QAHistoryConversation, QAHistoryItem, QAResponse
from app.services.qa import ask_question, ask_question_stream, list_conversation_records, list_history, update_favorite, update_feedback, upload_qa_image


router = APIRouter()
QA_ASK_RULE = RateLimitRule(limit=60, window_seconds=300)
QA_UPLOAD_RULE = RateLimitRule(limit=30, window_seconds=300)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data), ensure_ascii=False)}\n\n"


@router.post("/ask")
def ask_question_endpoint(
    payload: QAAskRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "qa-ask", user.id, payload.course_id, rule=QA_ASK_RULE)
    record = ask_question(db, user=user, payload=payload)
    response = QAResponse(
        conversation_id=record.conversation_id,
        record_id=record.id,
        question=record.question,
        answer=record.answer,
        thinking_process=record.thinking_process,
        is_out_of_scope=record.is_out_of_scope,
        sources=record.sources or [],
        attachments=record.attachments or [],
    )
    return success_response(data=response.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/ask/stream")
def ask_question_stream_endpoint(
    payload: QAAskRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "qa-ask-stream", user.id, payload.course_id, rule=QA_ASK_RULE)
    def event_stream():
        yield _sse("ready", {"request_id": request.state.request_id})
        try:
            for item in ask_question_stream(db, user=user, payload=payload):
                yield _sse(item["event"], item["data"])
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/attachments/image")
def upload_qa_image_endpoint(
    request: Request,
    course_id: Annotated[int, Form(...)],
    file: UploadFile = File(...),
    user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    limit_request(request, "qa-image-upload", user.id, course_id, rule=QA_UPLOAD_RULE)
    attachment = upload_qa_image(db, user=user, course_id=course_id, upload=file)
    return success_response(data=attachment, request_id=request.state.request_id)


@router.get("/history")
def get_history_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = Query(default=None),
    lesson_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    items = [
        QAHistoryConversation.model_validate(item).model_dump(mode="json")
        for item in list_history(db, user=user, course_id=course_id, lesson_id=lesson_id, keyword=keyword)
    ]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/conversations/{conversation_id}")
def get_conversation_endpoint(
    conversation_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    records = list_conversation_records(db, user=user, conversation_id=conversation_id)
    items = [QAHistoryItem.model_validate(item).model_dump(mode="json") for item in records]
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
