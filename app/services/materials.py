from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Queue
import re
from threading import BoundedSemaphore, Lock, Thread
from time import sleep
from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    LessonStatus,
    MaterialCategory,
    MaterialType,
    ProcessStatus,
    UserRole,
)
from app.core.errors import bad_request, forbidden, not_found
from app.core.upload_validation import validate_material_upload
from app.db.models import AsyncTaskLog, Chapter, CourseMaterial, KnowledgeChunk, Lesson, LessonPage, PageNote, PedagogyArtifact, QARecord, User
from app.services.ai import ai_service
from app.services.audit import log_operation
from app.services.courses import _assert_course_active_for_teacher, _assert_course_owner, _get_course_or_404
from app.services.knowledge import pre_generate_knowledge_points
from app.services.parser import parse_material
from app.services.pedagogy import generate_material_pedagogy_artifacts
from app.services.runtime_config import get_enabled_service_config
from app.services.runtime_settings import runtime_setting_int
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
    # 修复 DEF-02：FR-11 要求支持图片格式课程资料，图片经 OCR 抽取文本后生成课时页。
    ".png": MaterialType.IMAGE.value,
    ".jpg": MaterialType.IMAGE.value,
    ".jpeg": MaterialType.IMAGE.value,
    ".webp": MaterialType.IMAGE.value,
}

KNOWLEDGE_CHUNK_TARGET_CHARS = 900
KNOWLEDGE_CHUNK_OVERLAP_CHARS = 180
KNOWLEDGE_CHUNK_MIN_TAIL_CHARS = 120
_material_processing_queue: Queue[int] = Queue()
_material_processing_worker_lock = Lock()
_material_processing_worker_count_started = 0
_material_processing_supervisor_lock = Lock()
_material_processing_supervisor_started = False
_material_processing_enqueued_lock = Lock()
_material_processing_enqueued_ids: set[int] = set()
MATERIAL_PROCESS_TASK_NAME = "material.process"
DOC_PARSER_CACHE_KEY = "doc_parser_cache"
REPROCESS_OPTIONS_KEY = "reprocess_options"
REUSE_CACHED_PARSE_KEY = "reuse_cached_parse"
_settings = get_settings()
_doc_parser_limiter = BoundedSemaphore(max(1, int(_settings.doc_parser_max_concurrency)))
_material_ai_limiter = BoundedSemaphore(max(1, int(_settings.material_ai_max_concurrency)))
_tts_limiter = BoundedSemaphore(max(1, int(_settings.tts_max_concurrency)))


def _assert_material_owner(db: Session, material: CourseMaterial, user: User, *, require_active: bool = False) -> None:
    course = _get_course_or_404(db, material.course_id)
    _assert_course_owner(course, user, require_active=require_active)


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
    _assert_course_owner(course, user)
    _assert_course_active_for_teacher(course, user, "课程已下架，无法上传资料")
    if category not in {item.value for item in MaterialCategory}:
        raise bad_request("资料分类不合法")
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None or chapter.course_id != course_id:
            raise bad_request("章节不存在或不属于当前课程")
    # 单课程资料数量上限：每条资料都会触发 DocMind 解析 + 多页 AI 脚本 + TTS + 向量入库（重计费链路），
    # 必须有硬上限防止资源耗尽 / 第三方 API 计费放大。上限由管理端「单课程资料数」实时控制。
    max_count = runtime_setting_int(db, "course.material.max_count", get_settings().max_course_materials, minimum=1, maximum=100000)
    existing = db.scalar(
        select(func.count(CourseMaterial.id)).where(
            CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None)
        )
    ) or 0
    if existing >= max_count:
        raise bad_request(f"该课程资料数量已达上限（{max_count} 条），请先删除部分资料再上传")


def _detect_material_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    material_type = ALLOWED_EXTENSIONS.get(suffix)
    if material_type is None:
        raise bad_request("仅支持 .pptx、.pdf、.docx、.txt、.md、.markdown 或 .png、.jpg、.jpeg、.webp 图片")
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
    active_processing = _material_has_active_processing_task(db, material_id=material.id)
    if material.parse_status != ProcessStatus.READY.value and not active_processing:
        material.parse_status = ProcessStatus.READY.value
        changed = True
    if not material.extracted_text:
        material.extracted_text = "\n\n".join(page.page_text for page in pages if page.page_text)
        changed = True
    if lesson.page_count != len(pages):
        lesson.page_count = len(pages)
        changed = True
    if lesson.status not in {LessonStatus.READY.value, LessonStatus.PUBLISHED.value} and not active_processing:
        lesson.status = LessonStatus.READY.value
        changed = True
    if changed:
        db.add_all([material, lesson])
    return changed


def _material_metadata_dict(material: CourseMaterial) -> dict[str, Any]:
    return dict(material.metadata_json) if isinstance(material.metadata_json, dict) else {}


def _apply_material_metadata(material: CourseMaterial, metadata: dict[str, Any]) -> None:
    material.metadata_json = metadata or None


def _normalize_parsed_page(page: Any, default_page_number: int) -> dict[str, Any] | None:
    if not isinstance(page, dict):
        return None
    try:
        page_number = int(page.get("page_number") or default_page_number)
    except (TypeError, ValueError):
        page_number = default_page_number
    page_number = page_number if page_number > 0 else default_page_number
    page_title = str(page.get("page_title") or "").strip() or None
    page_text = str(page.get("page_text") or "").strip() or "本页未提取到有效文字内容。"
    return {
        "page_number": page_number,
        "page_title": page_title,
        "page_text": page_text,
    }


def _normalize_parsed_pages(pages: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        item = _normalize_parsed_page(page, index)
        if item is not None:
            normalized.append(item)
    normalized.sort(key=lambda item: (int(item["page_number"]), str(item.get("page_title") or "")))
    return normalized


def _cached_material_pages(material: CourseMaterial) -> list[dict[str, Any]]:
    metadata = _material_metadata_dict(material)
    cache = metadata.get(DOC_PARSER_CACHE_KEY)
    if not isinstance(cache, dict):
        return []
    pages = cache.get("pages")
    if not isinstance(pages, list):
        return []
    return _normalize_parsed_pages(pages)


def _cached_pages_from_lesson_pages(pages: list[LessonPage]) -> list[dict[str, Any]]:
    return _normalize_parsed_pages(
        [
            {
                "page_number": page.page_number,
                "page_title": page.page_title,
                "page_text": page.page_text,
            }
            for page in pages
        ]
    )


def _material_local_parsed_pages(db: Session, *, material: CourseMaterial) -> list[dict[str, Any]]:
    cached = _cached_material_pages(material)
    if cached:
        return cached
    _lesson, pages = _select_material_lesson_with_pages(db, material.id)
    if not pages:
        return []
    return _cached_pages_from_lesson_pages(pages)


def _store_material_parsed_pages(
    material: CourseMaterial,
    pages: list[Any],
    *,
    source: str,
) -> list[dict[str, Any]]:
    normalized = _normalize_parsed_pages(pages)
    metadata = _material_metadata_dict(material)
    metadata[DOC_PARSER_CACHE_KEY] = {
        "version": 1,
        "source": source,
        "page_count": len(normalized),
        "cached_at": datetime.now(UTC).isoformat(),
        "pages": normalized,
    }
    _apply_material_metadata(material, metadata)
    return normalized


def _set_reuse_cached_parse(material: CourseMaterial, enabled: bool) -> None:
    metadata = _material_metadata_dict(material)
    options = metadata.get(REPROCESS_OPTIONS_KEY)
    options_dict = dict(options) if isinstance(options, dict) else {}
    if enabled:
        options_dict[REUSE_CACHED_PARSE_KEY] = True
        options_dict["requested_at"] = datetime.now(UTC).isoformat()
        metadata[REPROCESS_OPTIONS_KEY] = options_dict
    else:
        options_dict.pop(REUSE_CACHED_PARSE_KEY, None)
        options_dict.pop("requested_at", None)
        if options_dict:
            metadata[REPROCESS_OPTIONS_KEY] = options_dict
        else:
            metadata.pop(REPROCESS_OPTIONS_KEY, None)
    _apply_material_metadata(material, metadata)


def _consume_reuse_cached_parse(material: CourseMaterial) -> bool:
    metadata = _material_metadata_dict(material)
    options = metadata.get(REPROCESS_OPTIONS_KEY)
    if not isinstance(options, dict) or not options.get(REUSE_CACHED_PARSE_KEY):
        return False
    options_dict = dict(options)
    options_dict.pop(REUSE_CACHED_PARSE_KEY, None)
    options_dict.pop("requested_at", None)
    if options_dict:
        metadata[REPROCESS_OPTIONS_KEY] = options_dict
    else:
        metadata.pop(REPROCESS_OPTIONS_KEY, None)
    _apply_material_metadata(material, metadata)
    return True


def _as_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def repair_materials_with_existing_pages(db: Session, materials: list[CourseMaterial]) -> None:
    changed = False
    for material in materials:
        lesson, pages = _select_material_lesson_with_pages(db, material.id)
        changed = _restore_material_from_existing_pages(db, material=material, lesson=lesson, pages=pages) or changed
    if changed:
        db.commit()


def _synthesize_or_none(script_text: str, db: Session) -> tuple[str | None, float | None, str | None]:
    try:
        with _tts_limiter:
            audio_url, duration = tts_service.synthesize(script_text, db=db)
        return audio_url, duration, None
    except Exception as exc:
        return None, None, str(exc)


# 降级标记前缀：明确告知该文本因模型未配置/调用失败而以模板兜底，不是真实 AI 产物。
_DEGRADED_SUMMARY_PREFIX = "【未生成AI摘要】"
_DEGRADED_SCRIPT_PREFIX = "【未生成AI讲解稿】"


def _fallback_lesson_summary(*, title: str, pages: list[dict[str, Any]]) -> str:
    merged = " ".join(str(page.get("page_text") or "").strip() for page in pages if str(page.get("page_text") or "").strip())
    return f"{_DEGRADED_SUMMARY_PREFIX}{title}：摘要因未配置模型或模型调用失败未生成，以下为页面原文片段供参考：{merged[:160] or '该资料已解析出课件页面，可继续补充讲解脚本。'}"


def _fallback_page_script(page_data: dict[str, Any]) -> str:
    heading = str(page_data.get("page_title") or "本页内容").strip() or "本页内容"
    content = re.sub(r"\s+", " ", str(page_data.get("page_text") or "")).strip()
    summary = content[:220] if len(content) > 220 else content
    return (
        f"{_DEGRADED_SCRIPT_PREFIX}{heading}：讲解稿因未配置模型或模型调用失败未生成，以下为页面原文片段供参考：\n"
        f"{summary or '本页暂无可提取文字。'}"
    )


def _summarize_lesson_with_limit(db: Session, *, title: str, pages: list[dict[str, Any]]) -> tuple[str, str | None]:
    """返回 (摘要, 降级原因)；降级原因非空表示用了模板兜底，需上层记入 warnings。"""
    try:
        with _material_ai_limiter:
            result = ai_service.summarize_lesson(title, [page["page_text"] for page in pages], db=db)
        if result and result.strip():
            return result.strip(), None
        return _fallback_lesson_summary(title=title, pages=pages), "模型未返回有效摘要"
    except Exception as exc:
        return _fallback_lesson_summary(title=title, pages=pages), str(exc) or "模型调用失败"


def _generate_page_script_with_new_session(page_data: dict[str, Any]) -> tuple[str, str | None]:
    """返回 (讲解稿, 降级原因)；降级原因非空表示用了模板兜底，需上层记入 warnings。"""
    from app.db import session as db_session

    with db_session.SessionLocal() as task_db:
        try:
            with _material_ai_limiter:
                result = ai_service.generate_page_script(
                    title=page_data.get("page_title"),
                    content=page_data["page_text"],
                    db=task_db,
                )
            if result and result.strip():
                return result.strip(), None
            return _fallback_page_script(page_data), "模型未返回有效讲解稿"
        except Exception as exc:
            return _fallback_page_script(page_data), str(exc) or "模型调用失败"


def _generate_page_scripts(
    pages: list[dict[str, Any]],
    *,
    on_progress: Any | None = None,
) -> tuple[list[str], list[str | None]]:
    """返回 (讲解稿列表, 每页降级原因列表)；降级原因为 None 表示该页为真实 AI 讲解稿。"""
    if not pages:
        return [], []
    max_workers = min(len(pages), max(1, int(_settings.material_ai_max_concurrency)))
    if max_workers <= 1:
        scripts: list[str] = []
        reasons: list[str | None] = []
        for index, page_data in enumerate(pages, start=1):
            script, reason = _generate_page_script_with_new_session(page_data)
            scripts.append(script)
            reasons.append(reason)
            if callable(on_progress):
                on_progress(index, len(pages), page_data)
        return scripts, reasons
    results: list[tuple[str, str | None] | None] = [None] * len(pages)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="material-script") as executor:
        future_map = {
            executor.submit(_generate_page_script_with_new_session, page_data): index
            for index, page_data in enumerate(pages)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            results[index] = future.result()
            completed += 1
            if callable(on_progress):
                on_progress(completed, len(pages), pages[index])
    scripts = [str((item or ("", None))[0] or "") for item in results]
    reasons = [(item or ("", None))[1] for item in results]
    return scripts, reasons


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
    # title 显式校验：避免空白脏数据，并防止超长在 MySQL 严格模式触发未捕获 500（应返回干净 400）
    title = (title or "").strip()
    if not title:
        raise bad_request("资料标题不能为空")
    if len(title) > 255:
        raise bad_request("资料标题不能超过 255 个字符")
    _validate_material_payload(course_id, category, chapter_id, user, db)
    material_type = _detect_material_type(upload.filename or "")
    validated = validate_material_upload(upload, max_bytes=settings.default_upload_limit_mb * 1024 * 1024)
    storage_path, size_bytes = storage_service.save_upload_bytes(
        validated.content,
        folder=f"course_{course_id}",
        suffix=validated.suffix,
        db=db,
    )
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
        preview_url=None,
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


def get_material_status(db: Session, material_id: int, user: User) -> dict[str, Any]:
    """轻量处理状态：供前端/自动化持续轮询，不携带页面全文（详情接口 50KB+ 不适合轮询）。

    parse_status 语义是"整条流水线状态"（解析→摘要→讲稿→TTS→向量→教学产物，最后才 ready）；
    课时在 TTS 完成后即 ready 可用，故单独给出 lesson_status/page_count 供"课时可用"级别的判断，
    并透出流水线任务的 stage/progress，让调用方能直接看到当前卡在哪一步。
    """
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_access(db, material, user)
    lesson = db.scalar(
        select(Lesson).where(Lesson.material_id == material.id).order_by(Lesson.id.desc()).limit(1)
    )
    first_page_id = (
        db.scalar(
            select(LessonPage.id).where(LessonPage.lesson_id == lesson.id).order_by(LessonPage.page_number).limit(1)
        )
        if lesson is not None
        else None
    )
    task = db.scalar(_material_process_task_statement(material_id=material_id).order_by(AsyncTaskLog.id.desc()).limit(1))
    detail = _task_detail(task) if task is not None else {}
    return {
        "material_id": material.id,
        "parse_status": material.parse_status,
        "vector_status": material.vector_status,
        "lesson_id": lesson.id if lesson else None,
        "lesson_status": lesson.status if lesson else None,
        "page_count": lesson.page_count if lesson else 0,
        "first_page_id": first_page_id,
        "task_status": task.status if task else None,
        "pipeline": detail.get("pipeline"),
        "queue": detail.get("queue"),
        "task_updated_at": task.updated_at if task else None,
    }


def get_material_for_preview(db: Session, *, material_id: int, user: User) -> CourseMaterial:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    _assert_material_access(db, material, user)
    return material


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
    _assert_material_owner(db, material, user, require_active=True)
    metadata_changed = title is not None or chapter_id_provided
    if title is not None:
        # 与 create_material 对齐：strip 后校验非空，避免纯空白脏数据写入标题及 chunk/artifact 元数据
        title = title.strip()
        if not title:
            raise bad_request("资料标题不能为空")
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
        try:
            vector_store.upsert_chunks(db, chunks=chunks)
        except Exception:
            material.vector_status = ProcessStatus.FAILED.value
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
    _assert_material_owner(db, material, user, require_active=True)
    from datetime import UTC, datetime

    vector_store.delete_material(db, course_id=material.course_id, material_id=material.id)
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.material_id == material.id))
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
    _assert_material_owner(db, material, user, require_active=True)
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
    _assert_material_owner(db, material, user, require_active=True)
    try:
        script_text = ai_service.generate_page_script(title=page.page_title, content=page.page_text, db=db)
    except Exception:
        script_text = None
    script_degraded_reason: str | None = None
    if not (script_text and script_text.strip()):
        # 模型未配置/调用失败/返回空：用带降级标记的兜底稿，不让页面落空或冒充真实讲解稿。
        script_text = _fallback_page_script(
            {"page_title": page.page_title, "page_text": page.page_text}
        )
        script_degraded_reason = "模型未返回有效讲解稿"
    audio_url, duration, error_message = _synthesize_or_none(script_text, db)
    page.script_text = script_text
    page.subtitle_text = script_text
    page.script_status = ProcessStatus.READY.value
    page.audio_url = audio_url
    page.audio_duration_seconds = duration
    db.add(page)
    log_detail: dict[str, Any] = {}
    if error_message:
        log_detail["tts_warning"] = error_message
    if script_degraded_reason:
        log_detail["script_degraded"] = script_degraded_reason
    log_operation(
        db,
        user_id=user.id,
        action="material.page.script.regenerate",
        target_type="lesson_page",
        target_id=page.id,
        detail=log_detail or None,
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


def _page_knowledge_text(
    *,
    material: CourseMaterial,
    page: LessonPage,
    chapter_title: str = "",
    lesson_summary: str = "",
) -> str:
    page_text = _compact_knowledge_text(page.page_text)
    script_text = _compact_knowledge_text(page.script_text or "")
    # 语境头：所属章节 + 资料 + 课时主题，让每个 chunk 自带"它属于哪一章/讲什么"的定位，
    # 显著提升中文教学库的章节类召回与 rerank 区分度（轻量版 contextual chunking，零额外 LLM 成本）
    parts: list[str] = []
    chapter_title = _compact_knowledge_text(chapter_title or "")
    if chapter_title:
        parts.append(f"章节：{chapter_title}")
    parts.append(f"资料：{material.title}")
    parts.append(f"页码：第{page.page_number}页")
    if page.page_title:
        parts.append(f"页面标题：{page.page_title}")
    lesson_summary = _compact_knowledge_text(lesson_summary or "")
    if lesson_summary:
        parts.append(f"本课时概要：{lesson_summary[:120]}")
    if page_text:
        parts.append(f"页面内容：\n{page_text}")
    if script_text and script_text != page_text:
        parts.append(f"讲解文稿：\n{script_text}")
    return "\n\n".join(parts)


def _build_page_knowledge_chunks(
    *,
    material: CourseMaterial,
    page: LessonPage,
    chapter_title: str = "",
    lesson_summary: str = "",
) -> list[KnowledgeChunk]:
    windows = _split_knowledge_text(
        _page_knowledge_text(material=material, page=page, chapter_title=chapter_title, lesson_summary=lesson_summary)
    )
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


def _task_detail(task: AsyncTaskLog) -> dict:
    return dict(task.detail) if isinstance(task.detail, dict) else {}


def _material_process_task_statement(*, material_id: int | None = None):
    statement = select(AsyncTaskLog).where(
        AsyncTaskLog.task_name == MATERIAL_PROCESS_TASK_NAME,
        AsyncTaskLog.target_type == "material",
    )
    if material_id is not None:
        statement = statement.where(AsyncTaskLog.target_id == material_id)
    return statement


def _latest_active_material_processing_task(db: Session, *, material_id: int) -> AsyncTaskLog | None:
    return db.scalar(
        _material_process_task_statement(material_id=material_id)
        .where(AsyncTaskLog.status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]))
        .order_by(AsyncTaskLog.id.desc())
        .limit(1)
    )


def _queue_task_payload(*, reason: str) -> dict[str, Any]:
    return {
        "status": ProcessStatus.PENDING.value,
        "reason": reason,
        "queued_at": datetime.now(UTC).isoformat(),
    }


def _pipeline_stage_payload(
    *,
    stage: str,
    status: str,
    progress: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "stage": stage,
        "status": status,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if progress is not None:
        payload["progress"] = int(max(0, min(progress, 100)))
    payload.update(extra)
    return payload


def _update_task_stage(
    db: Session,
    task: AsyncTaskLog,
    *,
    stage: str,
    status: str,
    progress: int | None = None,
    **extra: Any,
) -> None:
    _update_task_detail(
        db,
        task,
        pipeline=_pipeline_stage_payload(stage=stage, status=status, progress=progress, **extra),
    )


def _prepare_material_for_processing_retry(db: Session, *, material: CourseMaterial) -> None:
    local_pages = _material_local_parsed_pages(db, material=material)
    if local_pages:
        _store_material_parsed_pages(material, local_pages, source="local_cache")
        _set_reuse_cached_parse(material, True)
    else:
        _set_reuse_cached_parse(material, False)
    material.parse_status = ProcessStatus.PENDING.value
    material.vector_status = ProcessStatus.PENDING.value
    db.add(material)


def _enqueue_material_processing_task_record(db: Session, *, material_id: int, reason: str) -> AsyncTaskLog | None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        return None
    task = _latest_active_material_processing_task(db, material_id=material_id)
    if task is None:
        task = AsyncTaskLog(
            task_name=MATERIAL_PROCESS_TASK_NAME,
            target_type="material",
            target_id=material_id,
            status=ProcessStatus.PENDING.value,
            detail={"queue": _queue_task_payload(reason=reason)},
        )
        db.add(task)
    else:
        detail = _task_detail(task)
        detail["queue"] = _queue_task_payload(reason=reason)
        task.detail = detail
        db.add(task)
    db.commit()
    return task


def _claim_material_processing_task(db: Session, *, material_id: int) -> AsyncTaskLog:
    task = _latest_active_material_processing_task(db, material_id=material_id)
    if task is None:
        task = AsyncTaskLog(
            task_name=MATERIAL_PROCESS_TASK_NAME,
            target_type="material",
            target_id=material_id,
            status=ProcessStatus.PROCESSING.value,
            detail={},
        )
        db.add(task)
        db.flush()
    duplicates = list(
        db.scalars(
            _material_process_task_statement(material_id=material_id)
            .where(
                AsyncTaskLog.status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]),
                AsyncTaskLog.id != task.id,
            )
            .order_by(AsyncTaskLog.id.desc())
        )
    )
    for duplicate in duplicates:
        duplicate.status = ProcessStatus.FAILED.value
        duplicate.detail = {
            **_task_detail(duplicate),
            "error": "同资料存在更新的处理任务，旧任务已终止。",
            "failed_at": datetime.now(UTC).isoformat(),
        }
        db.add(duplicate)
    detail = _task_detail(task)
    detail["started_at"] = datetime.now(UTC).isoformat()
    task.status = ProcessStatus.PROCESSING.value
    task.detail = detail
    db.add(task)
    return task


def recover_interrupted_material_processing(db: Session, *, assume_local_queue_lost: bool = False) -> list[int]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=max(1, int(_settings.material_processing_stale_minutes)))
    active_tasks = list(
        db.scalars(
            _material_process_task_statement()
            .where(AsyncTaskLog.status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]))
            .order_by(AsyncTaskLog.target_id.asc(), AsyncTaskLog.id.desc())
        )
    )
    latest_task_by_material: dict[int, AsyncTaskLog] = {}
    changed = False
    for task in active_tasks:
        if task.target_id is None:
            continue
        material_id = int(task.target_id)
        if material_id not in latest_task_by_material:
            latest_task_by_material[material_id] = task
            continue
        task.status = ProcessStatus.FAILED.value
        task.detail = {
            **_task_detail(task),
            "error": "同资料存在更新的处理任务，旧任务已终止。",
            "failed_at": now.isoformat(),
        }
        db.add(task)
        changed = True

    materials = list(
        db.scalars(
            select(CourseMaterial)
            .where(
                CourseMaterial.deleted_at.is_(None),
                or_(
                    CourseMaterial.parse_status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]),
                    CourseMaterial.vector_status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]),
                ),
            )
            .order_by(CourseMaterial.id.asc())
        )
    )
    requeue_ids: list[int] = []
    for material in materials:
        active_task = latest_task_by_material.get(material.id)
        if active_task is None:
            _prepare_material_for_processing_retry(db, material=material)
            db.add(
                AsyncTaskLog(
                    task_name=MATERIAL_PROCESS_TASK_NAME,
                    target_type="material",
                    target_id=material.id,
                    status=ProcessStatus.PENDING.value,
                    detail={"queue": _queue_task_payload(reason="orphan_recovery")},
                )
            )
            requeue_ids.append(material.id)
            changed = True
            continue
        updated_at = _as_utc_datetime(active_task.updated_at)
        task_is_stale = updated_at is None or updated_at < cutoff
        if active_task.status == ProcessStatus.PROCESSING.value and (assume_local_queue_lost or task_is_stale):
            active_task.status = ProcessStatus.FAILED.value
            active_task.detail = {
                **_task_detail(active_task),
                "error": "后台资料处理任务中断，系统已自动重新排队。",
                "recovered_at": now.isoformat(),
                "stale_after_minutes": int(_settings.material_processing_stale_minutes),
            }
            db.add(active_task)
            _prepare_material_for_processing_retry(db, material=material)
            db.add(
                AsyncTaskLog(
                    task_name=MATERIAL_PROCESS_TASK_NAME,
                    target_type="material",
                    target_id=material.id,
                    status=ProcessStatus.PENDING.value,
                    detail={"queue": _queue_task_payload(reason="restart_recovery" if assume_local_queue_lost else "stale_recovery")},
                )
            )
            requeue_ids.append(material.id)
            changed = True
            continue
        if active_task.status == ProcessStatus.PENDING.value and (assume_local_queue_lost or task_is_stale):
            _prepare_material_for_processing_retry(db, material=material)
            detail = _task_detail(active_task)
            detail["queue"] = _queue_task_payload(reason="restart_recovery" if assume_local_queue_lost else "pending_recovery")
            active_task.detail = detail
            db.add(active_task)
            requeue_ids.append(material.id)
            changed = True
    if changed:
        db.commit()
    return list(dict.fromkeys(requeue_ids))


def _find_docmind_task_id(value: Any) -> str | None:
    if isinstance(value, dict):
        direct = value.get("docmind_task_id")
        if direct:
            return str(direct)
        for item in value.values():
            found = _find_docmind_task_id(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_docmind_task_id(item)
            if found:
                return found
    elif isinstance(value, str):
        match = re.search(r"docmind-\d{8}-[A-Za-z0-9]+", value)
        if match:
            return match.group(0)
    return None


def _latest_docmind_task_id(db: Session, *, material_id: int, exclude_task_id: int | None = None) -> str | None:
    statement = (
        select(AsyncTaskLog)
        .where(
            AsyncTaskLog.task_name == MATERIAL_PROCESS_TASK_NAME,
            AsyncTaskLog.target_type == "material",
            AsyncTaskLog.target_id == material_id,
        )
        .order_by(AsyncTaskLog.updated_at.desc(), AsyncTaskLog.id.desc())
        .limit(10)
    )
    if exclude_task_id is not None:
        statement = statement.where(AsyncTaskLog.id != exclude_task_id)
    for task in db.scalars(statement):
        found = _find_docmind_task_id(task.detail)
        if found:
            return found
    return None


def _update_task_detail(db: Session, task: AsyncTaskLog, **updates: Any) -> None:
    task.detail = {**_task_detail(task), **updates, "detail_updated_at": datetime.now(UTC).isoformat()}
    db.add(task)
    db.commit()


def _material_has_active_processing_task(db: Session, *, material_id: int) -> bool:
    return (
        db.scalar(
            select(AsyncTaskLog.id)
            .where(
                AsyncTaskLog.task_name == MATERIAL_PROCESS_TASK_NAME,
                AsyncTaskLog.target_type == "material",
                AsyncTaskLog.target_id == material_id,
                AsyncTaskLog.status.in_([ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value]),
            )
            .limit(1)
        )
        is not None
    )


def process_material_pipeline(db: Session, material_id: int) -> None:
    material = db.get(CourseMaterial, material_id)
    if material is None or material.deleted_at is not None:
        raise not_found("资料不存在")
    task = _claim_material_processing_task(db, material_id=material_id)
    material.parse_status = ProcessStatus.PROCESSING.value
    material.vector_status = ProcessStatus.PROCESSING.value
    reuse_cached_parse = _consume_reuse_cached_parse(material)
    db.add(material)
    db.commit()
    _update_task_stage(db, task, stage="starting", status=ProcessStatus.PROCESSING.value, progress=0)

    def record_parser_progress(progress: dict[str, Any]) -> None:
        _update_task_detail(
            db,
            task,
            doc_parser={**progress, "updated_at": datetime.now(UTC).isoformat()},
        )

    try:
        warnings: list[str] = []
        artifact_count = 0
        pages_source = "aliyun_docmind"
        pages: list[dict[str, Any]] = []
        if reuse_cached_parse:
            pages = _material_local_parsed_pages(db, material=material)
            if pages:
                pages_source = "local_cache"
                _update_task_detail(
                    db,
                    task,
                    doc_parser={
                        "stage": "reused_local_cache",
                        "status": "success",
                        "progress": 100,
                        "page_count": len(pages),
                        "updated_at": datetime.now(UTC).isoformat(),
                    },
                )
        if not pages:
            _update_task_stage(db, task, stage="doc_parser", status=ProcessStatus.PROCESSING.value, progress=5)
            resume_task_id = _latest_docmind_task_id(db, material_id=material.id, exclude_task_id=task.id)
            with _doc_parser_limiter:
                pages = parse_material(
                    storage_service.absolute_path(material.storage_path),
                    material.material_type,
                    db=db,
                    filename=material.original_filename,
                    resume_task_id=resume_task_id,
                    on_progress=record_parser_progress,
                )
        if not pages:
            pages = [{"page_number": 1, "page_title": material.title, "page_text": "未提取到资料内容。"}]
        pages = _store_material_parsed_pages(material, pages, source=pages_source)
        material.extracted_text = "\n\n".join(page["page_text"] for page in pages)
        db.add(material)
        db.commit()
        _update_task_stage(
            db,
            task,
            stage="doc_parser",
            status=ProcessStatus.READY.value,
            progress=15,
            page_count=len(pages),
            source=pages_source,
        )
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
        _update_task_stage(db, task, stage="lesson_summary", status=ProcessStatus.PROCESSING.value, progress=20)
        lesson.summary, summary_degraded_reason = _summarize_lesson_with_limit(db, title=material.title, pages=pages)
        if summary_degraded_reason:
            warnings.append(f"课时摘要降级为模板：{summary_degraded_reason}")
        db.add(lesson)
        db.commit()
        _update_task_stage(db, task, stage="lesson_summary", status=ProcessStatus.READY.value, progress=25)

        _update_task_stage(
            db,
            task,
            stage="script_generation",
            status=ProcessStatus.PROCESSING.value,
            progress=30,
            total_pages=len(pages),
            completed_pages=0,
        )

        def record_script_progress(completed: int, total: int, page_data: dict[str, Any]) -> None:
            base_progress = 30
            stage_progress = 30
            progress = base_progress + int(stage_progress * completed / max(total, 1))
            _update_task_stage(
                db,
                task,
                stage="script_generation",
                status=ProcessStatus.PROCESSING.value,
                progress=progress,
                total_pages=total,
                completed_pages=completed,
                current_page=page_data.get("page_number"),
            )

        script_texts, script_degraded_reasons = _generate_page_scripts(pages, on_progress=record_script_progress)
        for page_data, degraded_reason in zip(pages, script_degraded_reasons, strict=True):
            if degraded_reason:
                warnings.append(f"第{page_data['page_number']}页讲解稿降级为模板：{degraded_reason}")
        _update_task_stage(
            db,
            task,
            stage="script_generation",
            status=ProcessStatus.READY.value,
            progress=60,
            total_pages=len(pages),
            completed_pages=len(script_texts),
        )
        created_pages: list[LessonPage] = []
        _update_task_stage(
            db,
            task,
            stage="tts",
            status=ProcessStatus.PROCESSING.value,
            progress=62,
            total_pages=len(pages),
            completed_pages=0,
        )
        for index, (page_data, script_text) in enumerate(zip(pages, script_texts, strict=True), start=1):
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
            lesson.page_count = len(created_pages)
            db.add(lesson)
            _update_task_stage(
                db,
                task,
                stage="tts",
                status=ProcessStatus.PROCESSING.value,
                progress=62 + int(13 * index / max(len(pages), 1)),
                total_pages=len(pages),
                completed_pages=index,
                current_page=page_data.get("page_number"),
            )
        db.commit()
        _update_task_stage(
            db,
            task,
            stage="tts",
            status=ProcessStatus.READY.value,
            progress=75,
            total_pages=len(created_pages),
            completed_pages=len(created_pages),
        )

        lesson.page_count = len(created_pages)
        lesson.status = LessonStatus.READY.value
        db.add(lesson)
        db.commit()

        created_chunks: list[KnowledgeChunk] = []
        chapter_title = ""
        if material.chapter_id is not None:
            chapter = db.get(Chapter, material.chapter_id)
            chapter_title = chapter.title if chapter else ""
        lesson_summary = lesson.summary or ""
        for page in created_pages:
            page_chunks = _build_page_knowledge_chunks(
                material=material, page=page, chapter_title=chapter_title, lesson_summary=lesson_summary
            )
            for chunk in page_chunks:
                db.add(chunk)
            created_chunks.extend(page_chunks)
        db.flush()
        # Knowledge-point workers use independent DB sessions, so chunks must be committed before any
        # concurrent extraction starts. Do not rely on task-progress commits as an implicit boundary.
        db.commit()
        try:
            _update_task_stage(
                db,
                task,
                stage="vector_index",
                status=ProcessStatus.PROCESSING.value,
                progress=80,
                chunk_count=len(created_chunks),
            )
            with _material_ai_limiter:
                vector_store.upsert_chunks(db, chunks=created_chunks)
            material.vector_status = ProcessStatus.READY.value
            _update_task_stage(
                db,
                task,
                stage="vector_index",
                status=ProcessStatus.READY.value,
                progress=88,
                chunk_count=len(created_chunks),
            )
        except Exception as exc:
            material.vector_status = ProcessStatus.FAILED.value
            warnings.append(f"向量索引写入失败: {exc}")
        db.add(material)
        db.commit()

        knowledge_point_count = 0
        try:
            _update_task_stage(
                db,
                task,
                stage="knowledge_points",
                status=ProcessStatus.PROCESSING.value,
                progress=89,
                chunk_count=len(created_chunks),
                max_concurrency=int(_settings.knowledge_point_extraction_max_concurrency),
            )
            knowledge_result = pre_generate_knowledge_points(
                db,
                course_id=material.course_id,
                chapter_id=material.chapter_id,
            )
            knowledge_point_count = len(knowledge_result.points)
            if knowledge_result.failed_chunk_count:
                warnings.append(
                    f"知识点抽取有 {knowledge_result.failed_chunk_count}/{knowledge_result.chunk_count} 个片段使用本地关键词降级"
                )
            _update_task_stage(
                db,
                task,
                stage="knowledge_points",
                status=ProcessStatus.READY.value,
                progress=90,
                chunk_count=knowledge_result.chunk_count,
                knowledge_point_count=knowledge_point_count,
                failed_chunk_count=knowledge_result.failed_chunk_count,
                reused_existing=knowledge_result.reused_existing,
            )
        except Exception as exc:
            db.rollback()
            warnings.append(f"知识点预生成失败: {exc}")
            _update_task_stage(
                db,
                task,
                stage="knowledge_points",
                status=ProcessStatus.FAILED.value,
                progress=90,
                error=str(exc),
            )
        try:
            _update_task_stage(
                db,
                task,
                stage="pedagogy",
                status=ProcessStatus.PROCESSING.value,
                progress=91,
                total_pages=len(created_pages),
                completed_pages=0,
            )

            def record_pedagogy_progress(progress: dict[str, Any]) -> None:
                completed = int(progress.get("completed_pages") or 0)
                total = int(progress.get("total_pages") or len(created_pages) or 1)
                _update_task_stage(
                    db,
                    task,
                    stage="pedagogy",
                    status=ProcessStatus.PROCESSING.value,
                    progress=91 + int(7 * completed / max(total, 1)),
                    total_pages=total,
                    completed_pages=completed,
                    current_page=progress.get("page_number"),
                )

            artifacts = generate_material_pedagogy_artifacts(
                db,
                material=material,
                lesson=lesson,
                pages=created_pages,
                on_progress=record_pedagogy_progress,
                warnings=warnings,
            )
            artifact_count = len(artifacts)
            _update_task_stage(
                db,
                task,
                stage="pedagogy",
                status=ProcessStatus.READY.value,
                progress=98,
                artifact_count=artifact_count,
            )
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
        task.detail = {
            **_task_detail(task),
            "page_count": len(created_pages),
            "knowledge_point_count": knowledge_point_count,
            "pedagogy_artifact_count": artifact_count,
            "warnings": warnings,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        db.add(task)
        db.commit()
    except Exception as exc:
        db.rollback()
        lesson = db.scalar(select(Lesson).where(Lesson.material_id == material.id))
        if lesson is not None:
            page_count = int(db.scalar(select(func.count(LessonPage.id)).where(LessonPage.lesson_id == lesson.id)) or 0)
            lesson.page_count = page_count
            lesson.status = LessonStatus.READY.value if page_count else LessonStatus.DRAFT.value
            db.add(lesson)
        material.parse_status = ProcessStatus.FAILED.value
        material.vector_status = ProcessStatus.FAILED.value
        task.status = ProcessStatus.FAILED.value
        task.detail = {**_task_detail(task), "error": str(exc), "failed_at": datetime.now(UTC).isoformat()}
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


def _ensure_material_processing_worker() -> None:
    global _material_processing_worker_count_started

    target_worker_count = max(1, int(_settings.material_processing_worker_count))
    with _material_processing_worker_lock:
        while _material_processing_worker_count_started < target_worker_count:
            worker_index = _material_processing_worker_count_started + 1
            Thread(
                target=_material_processing_worker,
                name=f"material-processing-worker-{worker_index}",
                daemon=True,
            ).start()
            _material_processing_worker_count_started = worker_index


def _ensure_material_processing_supervisor() -> None:
    global _material_processing_supervisor_started

    with _material_processing_supervisor_lock:
        if _material_processing_supervisor_started:
            return
        Thread(target=_material_processing_supervisor, name="material-processing-supervisor", daemon=True).start()
        _material_processing_supervisor_started = True


def start_material_processing_runtime() -> None:
    if not _settings.celery_task_always_eager:
        return
    _ensure_material_processing_worker()
    _ensure_material_processing_supervisor()


def _queue_material_processing(material_id: int) -> bool:
    with _material_processing_enqueued_lock:
        if material_id in _material_processing_enqueued_ids:
            return False
        _material_processing_enqueued_ids.add(material_id)
        _material_processing_queue.put(material_id)
        return True


def _material_processing_worker() -> None:
    while True:
        material_id = _material_processing_queue.get()
        try:
            with _material_processing_enqueued_lock:
                _material_processing_enqueued_ids.discard(material_id)
            _process_material_in_background(material_id)
        finally:
            _material_processing_queue.task_done()


def _material_processing_supervisor() -> None:
    from app.db import session as db_session

    interval = max(15, int(_settings.material_processing_watchdog_interval_seconds))
    while True:
        sleep(interval)
        try:
            with db_session.SessionLocal() as db:
                material_ids = recover_interrupted_material_processing(db, assume_local_queue_lost=False)
            for material_id in material_ids:
                dispatch_material_processing(material_id)
        except Exception:
            continue


def dispatch_material_processing(material_id: int) -> None:
    from app.tasks.materials import process_material_task

    settings = get_settings()
    if settings.celery_task_always_eager:
        from app.db import session as db_session

        with db_session.SessionLocal() as db:
            parser_config = get_enabled_service_config(db, "doc_parser")
            _enqueue_material_processing_task_record(db, material_id=material_id, reason="dispatch")
        if parser_config is not None:
            start_material_processing_runtime()
            _queue_material_processing(material_id)
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
    tasks = [task for task in tasks if (_as_utc_datetime(task.updated_at) or cutoff) < cutoff]
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
    _assert_material_owner(db, material, user, require_active=True)
    if material.parse_status in {ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value}:
        raise bad_request("资料已在处理中，请等待当前任务完成")
    if material.vector_status in {ProcessStatus.PENDING.value, ProcessStatus.PROCESSING.value}:
        raise bad_request("资料已在处理中，请等待当前任务完成")
    if _material_has_active_processing_task(db, material_id=material.id):
        raise bad_request("资料已在处理中，请等待当前任务完成")
    local_pages = _material_local_parsed_pages(db, material=material)
    if local_pages:
        _store_material_parsed_pages(material, local_pages, source="local_cache")
        _set_reuse_cached_parse(material, True)
    else:
        _set_reuse_cached_parse(material, False)
    material.parse_status = ProcessStatus.PENDING.value
    material.vector_status = ProcessStatus.PENDING.value
    db.add(material)
    db.commit()
    dispatch_material_processing(material.id)
    db.refresh(material)
    return material
