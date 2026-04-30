from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class UserSummary(ORMModel):
    id: int
    email: str
    role: str
    status: str
    nickname: str
    avatar_url: str | None = None
    student_no: str | None = None
    employee_no: str | None = None
    bio: str | None = None
    created_at: datetime
    updated_at: datetime
