from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.schemas.common import ORMModel
from app.services.parser import sanitize_temporary_docmind_images
from app.services.storage import storage_service


class MaterialUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=32)
    chapter_id: int | None = Field(default=None, ge=1)


class ScriptUpdateRequest(BaseModel):
    script_text: str = Field(min_length=1, max_length=5000)


class LessonPageResponse(ORMModel):
    id: int
    lesson_id: int
    page_number: int
    page_title: str | None
    page_text: str
    script_text: str | None
    script_status: str
    audio_url: str | None
    audio_duration_seconds: float | None
    subtitle_text: str | None
    pedagogy: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_serializer("audio_url")
    def serialize_audio_url(self, value: str | None):
        return storage_service.normalize_public_url(value)

    @field_serializer("page_text", "script_text", "subtitle_text")
    def serialize_content_text(self, value: str | None):
        return sanitize_temporary_docmind_images(value)


class MaterialResponse(ORMModel):
    id: int
    course_id: int
    chapter_id: int | None
    uploader_id: int
    title: str
    category: str
    material_type: str
    size_bytes: int
    original_filename: str
    preview_url: str | None
    extracted_text: str | None
    parse_status: str
    vector_status: str
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("preview_url")
    def serialize_preview_url(self, value: str | None):
        return storage_service.normalize_public_url(value)

    @field_serializer("extracted_text")
    def serialize_extracted_text(self, value: str | None):
        return sanitize_temporary_docmind_images(value)


class MaterialDetailResponse(BaseModel):
    material: MaterialResponse
    lesson_id: int | None
    lesson_status: str | None
    lesson_page_count: int
    pages: list[LessonPageResponse]
