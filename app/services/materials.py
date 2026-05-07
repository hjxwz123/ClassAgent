from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from threading import Thread
from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete, func, or_, select, update
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
from app.db.models import AsyncTaskLog, Chapter, CourseMaterial, KnowledgeChunk, Lesson, LessonPage, PageNote, PedagogyArtifact, QARecord, User
from app.services.ai import ai_service
from app.services.audit import log_operation
from app.services.courses import _assert_course_owner, _get_course_or_404
from app.services.parser import parse_material
from app.services.pedagogy import generate_material_pedagogy_artifacts
from app.services.runtime_config import get_enabled_service_config
from app.services.storage import storage_service
from app.services.tts import tts_service
from app.services.usage import log_ai_usage
from app.services.vector_store import vector_store


ALLOWED_EXTENSIONS = {
    ".pptx": MaterialType.PPTX.value,
    ".pdf": MaterialType.PDF.value,
    ".docx": MaterialType.DOCX.value,
    ".txt": MaterialType.TXT.value,
    ".md": MaterialType.TXT.value,
    ".markdown": MaterialType.TXT.value,
}

KNOWLEDGE_CHUNK_TARGET_CHARS = 900
KNOWLEDGE_CHUNK_OVERLAP_CHARS = 180
KNOWLEDGE_CHUNK_MIN_TAIL_CHARS = 120


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
        raise bad_request("仅支持 .pptx、.pdf、.docx、.txt、.md、.markdown")
    return material_type


def _lesson_pages(db: Session, lesson_id: int) -> list[LessonPage]:
    return list(db.scalars(select(LessonPage).where(LessonPage.lesson_id == lesson_id).order_by(LessonPage.page_number)))


def _select_material_lesson_with_pages(db: Session, material_id: int) -> tuple[Lesson | None, list[LessonPage]]:
    lessons = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.material_id == material_id)
            .order_by(Lesson.updated_at.desc(), Lesson.id.desc())
        )
    )
    fallback: tuple[Lesson | None, list[LessonPage]] = (lessons[0], []) if lessons else (None, [])
    for lesson in lessons:
        pages = _lesson_pages(db, lesson.id)
        if pages:
            return lesson, pages
    return fallback


def _restore_material_from_existing_pages(
    db: Session,
    *,
    material: CourseMaterial,
    lesson: Lesson | None,
    pages: list[LessonPage],
) -> bool:
    if lesson is None or not pages:
        return False

    changed = False
    if material.parse_status != ProcessStatus.READY.value:
        material.parse_status = ProcessStatus.READY.value
        changed = True
    if not material.extracted_text:
        material.extracted_text = "\n\n".join(page.page_text for page in pages if page.page_text)
        changed = True
    if lesson.page_count != len(pages):
        lesson.page_count = len(pages)
        changed = True
    if lesson.status not in {LessonStatus.READY.value, LessonStatus.PUBLISHED.value}:
        lesson.status = LessonStatus.READY.value
        changed = True
    if changed:
        db.add_all([material, lesson])
    return changed


def repair_materials_with_existing_pages(db: Session, materials: list[CourseMaterial]) -> None:
    changed = False
    for material in materials:
        lesson, pages = _select_material_lesson_with_pages(db, material.id)
        changed = _restore_material_from_existing_pages(db, material=material, lesson=lesson, pages=pages) or changed
    if changed:
        db.commit()


def _synthesize_or_none(script_text: str, db: Session) -> tuple[str | None, float | None, str | None]:
    try:
        audio_url, duration = tts_service.synthesize(script_text, db=db)
        return audio_url, duration, None
    except Exception as exc:
        return None, None, str(exc)


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
    storage_path, size_bytes = storage_service.save_upload(upload, folder=f"course_{course_id}", db=db)
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
        preview_url=storage_service.public_url(storage_path, db=db),
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
    materials = list(db.scalars(statement.order_by(CourseMaterial.created_at.desc())).unique())
    repair_materials_with_existing_pages(db, materials)
    return materials


def get_material_detail(db: Session, material_id: int, user: User) -> tuple[CourseMaterial, Lesson | None, list[LessonPage]]:
    material = db.get(CourseMaterial, material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_access(db, material, user)
    lesson, pages = _select_material_lesson_with_pages(db, material.id)
    if _restore_material_from_existing_pages(db, material=material, lesson=lesson, pages=pages):
        db.commit()
        db.refresh(material)
        if lesson is not None:
            db.refresh(lesson)
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
    metadata_changed = title is not None or chapter_id_provided
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
    chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.material_id == material.id))) if metadata_changed else []
    artifacts = list(db.scalars(select(PedagogyArtifact).where(PedagogyArtifact.material_id == material.id))) if metadata_changed else []
    if metadata_changed and chunks:
        for chunk in chunks:
            chunk.chapter_id = material.chapter_id
            source_meta = dict(chunk.source_meta or {})
            source_meta["material_title"] = material.title
            source_meta["chapter_id"] = material.chapter_id
            chunk.source_meta = source_meta
            db.add(chunk)
        vector_store.upsert_chunks(db, chunks=chunks)
    if metadata_changed and artifacts:
        for artifact in artifacts:
            artifact.chapter_id = material.chapter_id
            if isinstance(artifact.payload, dict):
                artifact.payload = {**artifact.payload, "material_title": material.title, "chapter_id": material.chapter_id}
            db.add(artifact)
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

    vector_store.delete_material(db, course_id=material.course_id, material_id=material.id)
    db.execute(delete(PedagogyArtifact).where(PedagogyArtifact.material_id == material.id))
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
        raise not_found("课时不存在")
    material = db.get(CourseMaterial, lesson.material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    audio_url, duration, error_message = _synthesize_or_none(script_text, db)
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
        detail={"tts_warning": error_message} if error_message else None,
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
        raise not_found("课时不存在")
    material = db.get(CourseMaterial, lesson.material_id)
    if material is None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    script_text = ai_service.generate_page_script(title=page.page_title, content=page.page_text, db=db)
    audio_url, duration, error_message = _synthesize_or_none(script_text, db)
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
        detail={"tts_warning": error_message} if error_message else None,
    )
    db.commit()
    db.refresh(page)
    return page


def _tokenize(content: str) -> list[str]:
    return ai_service.extract_keywords(content, limit=20)


def _compact_knowledge_text(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _chunk_end_at_boundary(text: str, *, start: int, hard_end: int, target_chars: int) -> int:
    if hard_end >= len(text):
        return len(text)
    lower_bound = start + max(int(target_chars * 0.65), 1)
    for separator in ("\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", "，", ",", " "):
        index = text.rfind(separator, lower_bound, hard_end)
        if index >= lower_bound:
            return index + len(separator)
    return hard_end


def _split_knowledge_text(
    text: str,
    *,
    target_chars: int = KNOWLEDGE_CHUNK_TARGET_CHARS,
    overlap_chars: int = KNOWLEDGE_CHUNK_OVERLAP_CHARS,
) -> list[str]:
    clean = _compact_knowledge_text(text)
    if not clean:
        return []
    target_chars = max(300, int(target_chars))
    overlap_chars = max(0, min(int(overlap_chars), target_chars // 3))
    if len(clean) <= target_chars:
        return [clean]

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        hard_end = min(len(clean), start + target_chars)
        end = _chunk_end_at_boundary(clean, start=start, hard_end=hard_end, target_chars=target_chars)
        chunk = clean[start:end].strip()
        if chunk:
            if chunks and len(chunk) < KNOWLEDGE_CHUNK_MIN_TAIL_CHARS:
                chunks[-1] = f"{chunks[-1]}\n{chunk}".strip()
            else:
                chunks.append(chunk)
        if end >= len(clean):
            break
        next_start = max(end - overlap_chars, start + 1)
        start = next_start
    return chunks


def _page_knowledge_text(*, material: CourseMaterial, page: LessonPage) -> str:
    page_text = _compact_knowledge_text(page.page_text)
    script_text = _compact_knowledge_text(page.script_text or "")
    parts = [
        f"资料：{material.title}",
        f"页码：第{page.page_number}页",
    ]
    if page.page_title:
        parts.append(f"页面标题：{page.page_title}")
    if page_text:
        parts.append(f"页面内容：\n{page_text}")
    if script_text and script_text != page_text:
        parts.append(f"讲解文稿：\n{script_text}")
    return "\n\n".join(parts)


def _build_page_knowledge_chunks(*, material: CourseMaterial, page: LessonPage) -> list[KnowledgeChunk]:
    windows = _split_knowledge_text(_page_knowledge_text(material=material, page=page))
    if not windows:
        windows = [f"资料：{material.title}\n页码：第{page.page_number}页\n本页未提取到有效文字内容。"]
    chunk_count = len(windows)
    chunks: list[KnowledgeChunk] = []
    for index, content in enumerate(windows, start=1):
        page_title = page.page_title or f"第{page.page_number}页"
        title = page_title if chunk_count == 1 else f"{page_title} · 片段{index}/{chunk_count}"
        chunks.append(
            KnowledgeChunk(
                course_id=material.course_id,
                material_id=material.id,
                lesson_page_id=page.id,
                chapter_id=material.chapter_id,
                title=title,
                content=content,
                tokens=_tokenize(content),
                source_meta={
                    "material_id": material.id,
                    "material_title": material.title,
                    "page_number": page.page_number,
                    "chapter_id": material.chapter_id,
                    "lesson_id": page.lesson_id,
                    "lesson_page_id": page.id,
                    "chunk_index": index,
                    "chunk_count": chunk_count,
                    "chunk_target_chars": KNOWLEDGE_CHUNK_TARGET_CHARS,
                    "chunk_overlap_chars": KNOWLEDGE_CHUNK_OVERLAP_CHARS if chunk_count > 1 else 0,
                },
            )
        )
    return chunks


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
        warnings: list[str] = []
        artifact_count = 0
        pages = parse_material(
            storage_service.absolute_path(material.storage_path),
            material.material_type,
            db=db,
            filename=material.original_filename,
        )
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
            page_ids = list(db.scalars(select(LessonPage.id).where(LessonPage.lesson_id == lesson.id)))
            vector_store.delete_material(db, course_id=material.course_id, material_id=material.id)
            if page_ids:
                db.execute(
                    delete(KnowledgeChunk).where(
                        or_(KnowledgeChunk.material_id == material.id, KnowledgeChunk.lesson_page_id.in_(page_ids))
                    )
                )
                db.execute(
                    delete(PedagogyArtifact).where(
                        or_(PedagogyArtifact.material_id == material.id, PedagogyArtifact.lesson_page_id.in_(page_ids))
                    )
                )
                db.execute(delete(PageNote).where(PageNote.lesson_page_id.in_(page_ids)))
                db.execute(update(QARecord).where(QARecord.lesson_page_id.in_(page_ids)).values(lesson_page_id=None))
            else:
                db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.material_id == material.id))
                db.execute(delete(PedagogyArtifact).where(PedagogyArtifact.material_id == material.id))
            db.execute(delete(LessonPage).where(LessonPage.lesson_id == lesson.id))
            db.commit()
        lesson.title = material.title
        lesson.chapter_id = material.chapter_id
        lesson.page_count = len(pages)
        lesson.summary = ai_service.summarize_lesson(material.title, [page["page_text"] for page in pages], db=db)
        lesson.status = LessonStatus.READY.value
        db.add(lesson)
        db.commit()

        created_pages: list[LessonPage] = []
        for page_data in pages:
            script_text = ai_service.generate_page_script(title=page_data.get("page_title"), content=page_data["page_text"], db=db)
            audio_url, duration, error_message = _synthesize_or_none(script_text, db)
            if error_message:
                warnings.append(f"第{page_data['page_number']}页语音合成失败: {error_message}")
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

        created_chunks: list[KnowledgeChunk] = []
        for page in created_pages:
            page_chunks = _build_page_knowledge_chunks(material=material, page=page)
            for chunk in page_chunks:
                db.add(chunk)
            created_chunks.extend(page_chunks)
        db.flush()
        try:
            vector_store.upsert_chunks(db, chunks=created_chunks)
            material.vector_status = ProcessStatus.READY.value
        except Exception as exc:
            material.vector_status = ProcessStatus.FAILED.value
            warnings.append(f"向量索引写入失败: {exc}")
        try:
            artifacts = generate_material_pedagogy_artifacts(db, material=material, lesson=lesson, pages=created_pages)
            artifact_count = len(artifacts)
        except Exception as exc:
            warnings.append(f"教学结构生成失败: {exc}")
        material.parse_status = ProcessStatus.READY.value
        db.add(material)
        log_ai_usage(
            db,
            module="material_pipeline",
            user_id=material.uploader_id,
            course_id=material.course_id,
            prompt_chars=len(material.extracted_text or ""),
            completion_chars=sum(len(page.script_text or "") for page in created_pages),
            success=not warnings,
            error_message="；".join(warnings)[:500] if warnings else None,
        )
        task.status = ProcessStatus.READY.value
        task.detail = {"page_count": len(created_pages), "pedagogy_artifact_count": artifact_count, "warnings": warnings}
        db.add(task)
        db.commit()
    except Exception as exc:
        material.parse_status = ProcessStatus.FAILED.value
        material.vector_status = ProcessStatus.FAILED.value
        task.status = ProcessStatus.FAILED.value
        task.detail = {"error": str(exc)}
        db.add_all([material, task])
        log_ai_usage(
            db,
            module="material_pipeline",
            user_id=material.uploader_id,
            course_id=material.course_id,
            success=False,
            error_message=str(exc),
        )
        db.commit()
        raise


def dispatch_material_processing(material_id: int) -> None:
    from app.tasks.materials import process_material_task

    settings = get_settings()
    if settings.celery_task_always_eager:
        from app.db import session as db_session

        with db_session.SessionLocal() as db:
            parser_config = get_enabled_service_config(db, "doc_parser")
        if parser_config is not None and parser_config.provider != "mock":
            Thread(target=_process_material_in_background, args=(material_id,), daemon=True).start()
            return

    try:
        process_material_task.delay(material_id)
    except Exception:
        # In eager mode the processing task runs inside the upload request. The
        # pipeline records failed status itself, so upload should still return
        # the created material instead of converting processing failure to 500.
        return


def _process_material_in_background(material_id: int) -> None:
    from app.db import session as db_session

    with db_session.SessionLocal() as db:
        try:
            process_material_pipeline(db, material_id)
        except Exception:
            return


def recover_stale_material_processing_tasks(db: Session, *, max_age_minutes: int = 60) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
    tasks = list(
        db.scalars(
            select(AsyncTaskLog)
            .where(
                AsyncTaskLog.task_name == "material.process",
                AsyncTaskLog.target_type == "material",
                AsyncTaskLog.status == ProcessStatus.PROCESSING.value,
                AsyncTaskLog.updated_at < cutoff,
            )
            .order_by(AsyncTaskLog.updated_at.asc(), AsyncTaskLog.id.asc())
        )
    )
    recovered = 0
    for task in tasks:
        material = db.get(CourseMaterial, task.target_id) if task.target_id else None
        if material is not None and material.deleted_at is None:
            if material.parse_status == ProcessStatus.PROCESSING.value:
                lesson = db.scalar(select(Lesson).where(Lesson.material_id == material.id))
                page_count = (
                    db.scalar(select(func.count(LessonPage.id)).where(LessonPage.lesson_id == lesson.id))
                    if lesson is not None
                    else 0
                )
                material.parse_status = ProcessStatus.READY.value if page_count and material.extracted_text else ProcessStatus.FAILED.value
            if material.vector_status == ProcessStatus.PROCESSING.value:
                material.vector_status = ProcessStatus.FAILED.value
            db.add(material)
        task.status = ProcessStatus.FAILED.value
        task.detail = {
            **(task.detail or {}),
            "error": "后台资料处理任务中断或超时，请重新解析。",
            "recovered_at": datetime.now(UTC).isoformat(),
            "stale_after_minutes": max_age_minutes,
        }
        db.add(task)
        recovered += 1
    if recovered:
        db.commit()
    return recovered


def reprocess_material(db: Session, *, material_id: int, user: User) -> CourseMaterial:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_owner(db, material, user)
    dispatch_material_processing(material.id)
    db.refresh(material)
    return material
