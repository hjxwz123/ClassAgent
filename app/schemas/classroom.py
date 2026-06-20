from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.material import MaterialResponse
from app.schemas.material import LessonPageResponse


class LessonResponse(ORMModel):
    id: int
    course_id: int
    chapter_id: int | None
    material_id: int | None
    title: str
    summary: str | None
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class LessonDetailResponse(BaseModel):
    lesson: LessonResponse
    material: MaterialResponse | None = None
    pages: list[LessonPageResponse]


class ProgressUpdateRequest(BaseModel):
    current_page: int = Field(ge=1)
    added_seconds: int = Field(default=0, ge=0, le=3600)
    # 注意：完成与否由服务层根据 current_page>=page_count 判定，客户端无法直接声明已完成，
    # 因此此处不再接收 `completed` 字段（旧字段从不被服务层读取，属契约误导，已移除）。


class LearningProgressResponse(ORMModel):
    id: int
    lesson_id: int
    user_id: int
    current_page: int
    progress_percent: float
    total_study_seconds: int
    completed_at: datetime | None
    resumed_from_page: int | None
    created_at: datetime
    updated_at: datetime
