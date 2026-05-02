from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class QAAttachment(BaseModel):
    type: str = Field(default="image", max_length=32)
    url: str = Field(max_length=1000)
    filename: str | None = Field(default=None, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    ocr_text: str | None = Field(default=None, max_length=4000)


class QAAskRequest(BaseModel):
    course_id: int
    question: str = Field(min_length=2, max_length=4000)
    conversation_id: int | None = None
    lesson_page_id: int | None = None
    chapter_id: int | None = None
    attachments: list[QAAttachment] = Field(default_factory=list, max_length=3)


class QAResponse(BaseModel):
    conversation_id: int
    record_id: int
    question: str
    answer: str
    thinking_process: str | None = None
    is_out_of_scope: bool
    sources: list[dict]
    attachments: list[dict] = Field(default_factory=list)


class QAHistoryItem(ORMModel):
    id: int
    conversation_id: int
    course_id: int
    user_id: int
    lesson_page_id: int | None
    question: str
    answer: str
    thinking_process: str | None = None
    is_out_of_scope: bool
    sources: list | None
    attachments: list | None = None
    keywords: list | None
    is_favorite: bool
    feedback: str
    feedback_comment: str | None
    created_at: datetime
    updated_at: datetime


class QAFavoriteRequest(BaseModel):
    is_favorite: bool


class QAFeedbackRequest(BaseModel):
    feedback: str
    feedback_comment: str | None = Field(default=None, max_length=2000)
