from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProblemTextRequest(BaseModel):
    course_id: int
    text: str = Field(min_length=2, max_length=5000)


class ProblemConfirmRequest(BaseModel):
    corrected_text: str = Field(min_length=2, max_length=5000)


class ProblemResponse(ORMModel):
    id: int
    course_id: int
    user_id: int
    source_type: str
    image_path: str | None
    raw_text: str | None
    ocr_text: str | None
    corrected_text: str | None
    knowledge_points: list | None
    common_mistakes: list | None
    created_at: datetime
    updated_at: datetime


class ProblemGuidanceResponse(ORMModel):
    id: int
    problem_id: int
    level: int
    content: str
    similar_questions: list | None
    created_at: datetime
    updated_at: datetime
