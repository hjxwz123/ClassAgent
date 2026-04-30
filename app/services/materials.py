from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    CourseStatus,
    LessonStatus,
    MaterialCategory,
    MaterialType,
    ProcessStatus,
    UserRole,
)
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import AsyncTaskLog, Chapter, CourseMaterial, KnowledgeChunk, Lesson, LessonPage, User
from app.services.ai import ai_service
from app.services.audit import log_operation
from app.services.courses import _assert_course_owner, _get_course_or_404
from app.services.parser import parse_material
from app.services.storage import storage_service
from app.services.tts import tts_service


ALLOWED_EXTENSIONS = {
    ".pptx": MaterialType.PPTX.value,
    ".pdf": MaterialType.PDF.value,
    ".docx": MaterialType.DOCX.value,
    ".txt": MaterialType.TXT.value,
}


def _assert_material_owner(db: Session, material: CourseMaterial, user: User) -> None:
    course = _get_course_or_404(db, material.course_id)
    _assert_course_owner(course, user)


def _assert_material_access(db: Session, material: CourseMaterial, user: User) -> None:
    if material.deleted_at is not None:
        raise not_found("资料不存在")
    if user.role == UserRole.ADMIN.value:
        return
    if user.role == UserRole.TEACHER.value:
        _assert_material_owner(db, material, user)
        return
    from app.db.models import CourseMembership

    membership = db.scalar(
        select(CourseMembership.id).where(
            CourseMembership.course_id == material.course_id,
            CourseMembership.user_id == user.id,
        )
    )
    if membership is None:
        raise forbidden("仅可访问已加入课程的资料")


def _validate_material_payload(course_id: int, category: str, chapter_id: int | None, user: User, db: Session) -> None:
    course = _get_course_or_404(db, course_id)
    if course.status != CourseStatus.ACTIVE.value:
        raise bad_request("课程已停用，无法上传资料")
    _assert_course_owner(course, user)
    if category not in {item.value for item in MaterialCategory}:
        raise bad_request("资料分类不合法")
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None or chapter.course_id != course_id:
            raise bad_request("章节不存在或不属于当前课程")


def _detect_material_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    material_type = ALLOWED_EXTENSIONS.get(suffix)
    if material_type is None:
        raise bad_request("仅支持 .pptx、.pdf、.docx、.txt")
    return material_type


def create_material(
    db: Session,
    *,
    user: User,
    course_id: int,
    title: str,
    category: str,
    chapter_id: int | None,
    upload: UploadFile,
) -> CourseMaterial:
    settings = get_settings()
    _validate_material_payload(course_id, category, chapter_id, user, db)
    material_type = _detect_material_type(upload.filename or "")
    storage_path, size_bytes = storage_service.save_upload(upload, folder=f"course_{course_id}")
    if size_bytes > settings.default_upload_limit_mb * 1024 * 1024:
        absolute_path = storage_service.absolute_path(storage_path)
        absolute_path.unlink(missing_ok=True)
        raise bad_request(f"文件大小不能超过 {settings.default_upload_limit_mb}MB")
    material = CourseMaterial(
        course_id=course_id,
        chapter_id=chapter_id,
        uploader_id=user.id,
        title=title,
        category=category,
        material_type=material_type,
        size_bytes=size_bytes,
        original_filename=upload.filename or "unknown",
        storage_path=storage_path,
        preview_url=storage_service.public_url(storage_path),
        parse_status=ProcessStatus.PENDING.value,
        vector_status=ProcessStatus.PENDING.value,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    log_operation(
        db,
        user_id=user.id,
        action="material.create",
        target_type="material",
        target_id=material.id,
        detail={"course_id": course_id, "chapter_id": chapter_id, "type": material_type},
    )
    db.commit()
    return material


def list_materials(
    db: Session,
    *,
    user: User,
    course_id: int | None = None,
    chapter_id: int | None = None,
    keyword: str | None = None,
    category: str | None = None,
) -> list[CourseMaterial]:
    statement = select(CourseMaterial).where(CourseMaterial.deleted_at.is_(None))
    if course_id is not None:
        statement = statement.where(CourseMaterial.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(CourseMaterial.chapter_id == chapter_id)
    if category:
        statement = statement.where(CourseMaterial.category == category)
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where(or_(CourseMaterial.title.like(like), CourseMaterial.extracted_text.like(like)))
    if user.role == UserRole.TEACHER.value:
        from app.db.models import Course

        statement = statement.join(Course, Course.id == CourseMaterial.course_id).where(Course.teacher_id == user.id)
    elif user.role == UserRole.STUDENT.value:
        from app.db.models import CourseMembership

        statement = statement.join(CourseMembership, CourseMembership.course_id == CourseMaterial.course_id).where(
            CourseMembership.user_id == user.id
        )
    return list(db.scalars(statement.order_by(CourseMaterial.created_at.desc())).unique())


def get_material_detail(db: Session, material_id: int, user: User) -> tuple[CourseMaterial, Lesson | None, list[LessonPage]]:
    material = db.get(CourseMaterial, material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_access(db, material, user)
    lesson = db.scalar(select(Lesson).where(Lesson.material_id == material.id))
    pages: list[LessonPage] = []
    if lesson is not None:
        pages = list(db.scalars(select(LessonPage).where(LessonPage.lesson_id == lesson.id).order_by(LessonPage.page_number)))
    return material, lesson, pages


def update_material(
    db: Session,
    *,
    material_id: int,
    user: User,
    title: str | None,
    category: str | None,
    chapter_id: int | None,
    chapter_id_provided: bool,
) -> CourseMaterial:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    if title is not None:
        material.title = title
    if category is not None:
        if category not in {item.value for item in MaterialCategory}:
            raise bad_request("资料分类不合法")
        material.category = category
    if chapter_id_provided:
        if chapter_id is not None:
            chapter = db.get(Chapter, chapter_id)
            if chapter is None or chapter.course_id != material.course_id:
                raise bad_request("章节不存在或不属于当前课程")
        material.chapter_id = chapter_id
    db.add(material)
    log_operation(
        db,
        user_id=user.id,
        action="material.update",
        target_type="material",
        target_id=material.id,
    )
    db.commit()
    db.refresh(material)
    return material


def delete_material(db: Session, *, material_id: int, user: User) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    from datetime import UTC, datetime

    material.deleted_at = datetime.now(UTC)
    db.add(material)
    log_operation(
        db,
        user_id=user.id,
        action="material.delete",
        target_type="material",
        target_id=material.id,
    )
    db.commit()


def update_page_script(db: Session, *, page_id: int, user: User, script_text: str) -> LessonPage:
    page = db.get(LessonPage, page_id)
    if page is None:
        raise not_found("页面不存在")
    lesson = db.get(Lesson, page.lesson_id)
    if lesson is None or lesson.material_id is None:
        raise not_found("课堂不存在")
    material = db.get(CourseMaterial, lesson.material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    audio_url, duration = tts_service.synthesize(script_text)
    page.script_text = script_text
    page.subtitle_text = script_text
    page.script_status = ProcessStatus.READY.value
    page.audio_url = audio_url
    page.audio_duration_seconds = duration
    db.add(page)
    log_operation(
        db,
        user_id=user.id,
        action="material.page.script.update",
        target_type="lesson_page",
        target_id=page.id,
    )
    db.commit()
    db.refresh(page)
    return page


def regenerate_page_script(db: Session, *, page_id: int, user: User) -> LessonPage:
    page = db.get(LessonPage, page_id)
    if page is None:
        raise not_found("页面不存在")
    lesson = db.get(Lesson, page.lesson_id)
    if lesson is None or lesson.material_id is None:
        raise not_found("课堂不存在")
    material = db.get(CourseMaterial, lesson.material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    script_text = ai_service.generate_page_script(title=page.page_title, content=page.page_text)
    audio_url, duration = tts_service.synthesize(script_text)
    page.script_text = script_text
    page.subtitle_text = script_text
    page.script_status = ProcessStatus.READY.value
    page.audio_url = audio_url
    page.audio_duration_seconds = duration
    db.add(page)
    log_operation(
        db,
        user_id=user.id,
        action="material.page.script.regenerate",
        target_type="lesson_page",
        target_id=page.id,
    )
    db.commit()
    db.refresh(page)
    return page


def _tokenize(content: str) -> list[str]:
    return ai_service.extract_keywords(content, limit=20)


def process_material_pipeline(db: Session, material_id: int) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    task = AsyncTaskLog(task_name="material.process", target_type="material", target_id=material_id, status=ProcessStatus.PROCESSING.value)
    db.add(task)
    material.parse_status = ProcessStatus.PROCESSING.value
    material.vector_status = ProcessStatus.PROCESSING.value
    db.add(material)
    db.commit()
    try:
        pages = parse_material(storage_service.absolute_path(material.storage_path), material.material_type)
        if not pages:
            pages = [{"page_number": 1, "page_title": material.title, "page_text": "未提取到资料内容。"}]
        material.extracted_text = "\n\n".join(page["page_text"] for page in pages)
        lesson = db.scalar(select(Lesson).where(Lesson.material_id == material.id))
        if lesson is None:
            lesson = Lesson(course_id=material.course_id, chapter_id=material.chapter_id, material_id=material.id, title=material.title)
            db.add(lesson)
            db.commit()
            db.refresh(lesson)
        else:
            db.execute(delete(LessonPage).where(LessonPage.lesson_id == lesson.id))
            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.material_id == material.id))
            db.commit()
        lesson.title = material.title
        lesson.chapter_id = material.chapter_id
        lesson.page_count = len(pages)
        lesson.summary = ai_service.summarize_lesson(material.title, [page["page_text"] for page in pages])
        lesson.status = LessonStatus.READY.value
        db.add(lesson)
        db.commit()

        created_pages: list[LessonPage] = []
        for page_data in pages:
            script_text = ai_service.generate_page_script(title=page_data.get("page_title"), content=page_data["page_text"])
            audio_url, duration = tts_service.synthesize(script_text)
            page = LessonPage(
                lesson_id=lesson.id,
                page_number=page_data["page_number"],
                page_title=page_data.get("page_title"),
                page_text=page_data["page_text"],
                script_text=script_text,
                script_status=ProcessStatus.READY.value,
                audio_url=audio_url,
                audio_duration_seconds=duration,
                subtitle_text=script_text,
            )
            db.add(page)
            db.flush()
            created_pages.append(page)
        db.commit()

        for page in created_pages:
            chunk = KnowledgeChunk(
                course_id=material.course_id,
                material_id=material.id,
                lesson_page_id=page.id,
                chapter_id=material.chapter_id,
                title=page.page_title or f"第{page.page_number}页",
                content=page.page_text,
                tokens=_tokenize(page.page_text),
                source_meta={
                    "material_id": material.id,
                    "material_title": material.title,
                    "page_number": page.page_number,
                    "chapter_id": material.chapter_id,
                },
            )
            db.add(chunk)
        material.parse_status = ProcessStatus.READY.value
        material.vector_status = ProcessStatus.READY.value
        db.add(material)
        task.status = ProcessStatus.READY.value
        task.detail = {"page_count": len(created_pages)}
        db.add(task)
        db.commit()
    except Exception as exc:
        material.parse_status = ProcessStatus.FAILED.value
        material.vector_status = ProcessStatus.FAILED.value
        task.status = ProcessStatus.FAILED.value
        task.detail = {"error": str(exc)}
        db.add_all([material, task])
        db.commit()
        raise


def dispatch_material_processing(material_id: int) -> None:
    from app.tasks.materials import process_material_task

    process_material_task.delay(material_id)


def reprocess_material(db: Session, *, material_id: int, user: User) -> CourseMaterial:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    dispatch_material_processing(material.id)
    db.refresh(material)
    return material
