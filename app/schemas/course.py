from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UserSummary


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    term: str = Field(min_length=2, max_length=64)
    cover_color: str | None = Field(default=None, max_length=32)


class CourseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    term: str | None = Field(default=None, min_length=2, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    cover_url: str | None = Field(default=None, max_length=500)
    cover_color: str | None = Field(default=None, max_length=32)


class JoinCourseRequest(BaseModel):
    course_code: str = Field(min_length=6, max_length=12)


class ChapterCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    order_index: int = Field(default=1, ge=1)


class ChapterResponse(ORMModel):
    id: int
    course_id: int
    title: str
    description: str | None
    order_index: int
    created_at: datetime
    updated_at: datetime


class CourseResponse(ORMModel):
    id: int
    name: str
    description: str | None
    term: str
    course_code: str
    teacher_id: int
    status: str
    cover_url: str | None = None
    cover_color: str | None = None
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(BaseModel):
    course: CourseResponse
    teacher: UserSummary
    chapters: list[ChapterResponse]
    student_count: int


class CourseMemberResponse(BaseModel):
    id: int
    user: UserSummary
    joined_at: datetime
