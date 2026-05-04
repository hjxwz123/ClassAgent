from collections.abc import Iterator
from pathlib import Path
from time import sleep

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.enums import QAFeedback, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import Chapter, Course, CourseMaterial, CourseMembership, KnowledgeChunk, Lesson, LessonPage, QAConversation, QARecord, User
from app.schemas.qa import QAAskRequest
from app.services.ai import ai_service
from app.services.knowledge import search_course_knowledge
from app.services.parser import _extract_text_payload
from app.services.ocr import ocr_service
from app.services.storage import storage_service
from app.services.usage import log_ai_usage


_THINK_START_TAGS = ("<think>", "<thinking>")
_THINK_END_TAGS = ("</think>", "</thinking>")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_QA_IMAGE_LIMIT_BYTES = 10 * 1024 * 1024
_STREAM_CHUNK_SIZE = 36
_STREAM_CHUNK_DELAY_SECONDS = 0.015


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内提问")


def _get_or_create_course_conversation(db: Session, *, user: User, payload: QAAskRequest) -> QAConversation:
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(
            select(QAConversation).where(
                QAConversation.id == payload.conversation_id,
                QAConversation.user_id == user.id,
                QAConversation.course_id == payload.course_id,
            )
        )
    if conversation is None:
        conversation = QAConversation(course_id=payload.course_id, user_id=user.id, title=payload.question[:30])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation


def _find_tag(buffer: str, tags: tuple[str, ...]) -> tuple[int, str] | None:
    lower = buffer.lower()
    matches = [(index, tag) for tag in tags if (index := lower.find(tag)) >= 0]
    return min(matches, key=lambda item: item[0]) if matches else None


def _safe_text_length(buffer: str, tags: tuple[str, ...]) -> int:
    lower = buffer.lower()
    hold = 0
    for size in range(1, min(len(lower), max(len(tag) for tag in tags) - 1) + 1):
        suffix = lower[-size:]
        if any(tag.startswith(suffix) for tag in tags):
            hold = size
    return len(buffer) - hold


def _split_thinking_tags(state: dict[str, object], chunk: str) -> list[tuple[str, str]]:
    state["buffer"] = str(state.get("buffer") or "") + chunk
    parts: list[tuple[str, str]] = []
    while state["buffer"]:
        buffer = str(state["buffer"])
        in_think = bool(state.get("in_think"))
        tags = _THINK_END_TAGS if in_think else _THINK_START_TAGS
        match = _find_tag(buffer, tags)
        kind = "thought" if in_think else "answer"
        if match:
            index, tag = match
            text = buffer[:index]
            if text:
                parts.append((kind, text))
            state["buffer"] = buffer[index + len(tag) :]
            state["in_think"] = not in_think
            continue
        safe_len = _safe_text_length(buffer, tags)
        if safe_len <= 0:
            break
        parts.append((kind, buffer[:safe_len]))
        state["buffer"] = buffer[safe_len:]
        break
    return parts


def _flush_thinking_tags(state: dict[str, object]) -> list[tuple[str, str]]:
    buffer = str(state.get("buffer") or "")
    if not buffer:
        return []
    state["buffer"] = ""
    return [("thought" if bool(state.get("in_think")) else "answer", buffer)]


def _text_chunks(text: str, *, size: int = _STREAM_CHUNK_SIZE) -> list[str]:
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    buffer = ""
    break_chars = set("，。！？；、,.!?; \n")
    for char in text:
        buffer += char
        if len(buffer) >= size and (char in break_chars or len(buffer) >= size * 2):
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def _stream_text_delta(kind: str, text: str, answer_parts: list[str], thought_parts: list[str]) -> Iterator[dict]:
    chunks = _text_chunks(text)
    target = thought_parts if kind == "thought" else answer_parts
    for chunk in chunks:
        target.append(chunk)
        yield {"event": "delta", "data": {"type": kind, "text": chunk}}
        if len(chunks) > 1:
            sleep(_STREAM_CHUNK_DELAY_SECONDS)


def _attachment_dicts(payload: QAAskRequest) -> list[dict]:
    return [attachment.model_dump(mode="json", exclude_none=True) for attachment in payload.attachments]


def _question_with_attachments(question: str, attachments: list[dict]) -> str:
    if not attachments:
        return question
    lines = [question.strip()]
    for index, attachment in enumerate(attachments, start=1):
        filename = attachment.get("filename") or f"图片{index}"
        ocr_text = str(attachment.get("ocr_text") or "").strip()
        if ocr_text:
            lines.append(f"学生上传图片{index}（{filename}）OCR识别内容：{ocr_text}")
        else:
            lines.append(f"学生上传图片{index}（{filename}），未识别到可用文字。")
    return "\n\n".join(lines)


def _lesson_page_context(db: Session, *, course_id: int, lesson_page_id: int | None) -> tuple[list[str], list[dict]]:
    if lesson_page_id is None:
        return [], []
    row = db.execute(
        select(LessonPage, Lesson)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .where(LessonPage.id == lesson_page_id, Lesson.course_id == course_id)
    ).first()
    if row is None:
        return [], []
    page, lesson = row
    page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
    script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
    parts = [
        f"当前课时：{lesson.title}",
        f"当前页：第{page.page_number}页 {page.page_title or ''}".strip(),
    ]
    if page_text:
        parts.append(f"页面内容：\n{page_text}")
    if script_text and script_text != page_text:
        parts.append(f"讲解文稿：\n{script_text}")
    source = {
        "title": f"{lesson.title} · 第{page.page_number}页",
        "lesson_id": lesson.id,
        "lesson_page_id": page.id,
        "page_number": page.page_number,
    }
    return ["\n\n".join(parts)], [source]


def _trim_context(value: str, limit: int = 1200) -> str:
    clean = str(value or "").strip()
    return clean[:limit]


def _chapter_context(db: Session, *, course_id: int, chapter_id: int | None, limit: int = 8) -> tuple[list[str], list[dict]]:
    if chapter_id is None:
        return [], []
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.course_id != course_id:
        return [], []
    contexts: list[str] = []
    sources: list[dict] = []
    heading = f"章节：{chapter.title}"
    if chapter.description:
        contexts.append(f"{heading}\n章节说明：{chapter.description}")
        sources.append({"chapter_id": chapter.id, "chapter_title": chapter.title, "type": "chapter"})

    chunks = list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.course_id == course_id, KnowledgeChunk.chapter_id == chapter_id)
            .order_by(KnowledgeChunk.id)
            .limit(limit)
        )
    )
    for chunk in chunks:
        content = _trim_context(chunk.content)
        if not content:
            continue
        contexts.append(f"{heading}\n资料片段：{chunk.title}\n{content}")
        source = dict(chunk.source_meta or {})
        source.update({"chapter_id": chapter.id, "chapter_title": chapter.title, "chunk_id": chunk.id, "title": chunk.title})
        sources.append(source)
    if contexts:
        return contexts, sources

    page_rows = db.execute(
        select(LessonPage, Lesson)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .where(Lesson.course_id == course_id, Lesson.chapter_id == chapter_id)
        .order_by(Lesson.id, LessonPage.page_number)
        .limit(limit)
    )
    for page, lesson in page_rows:
        page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
        script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
        pieces = [f"{heading}", f"课时：{lesson.title}", f"页面：第{page.page_number}页 {page.page_title or ''}".strip()]
        if page_text:
            pieces.append(f"页面内容：{_trim_context(page_text)}")
        if script_text and script_text != page_text:
            pieces.append(f"讲解文稿：{_trim_context(script_text)}")
        if len(pieces) <= 3:
            continue
        contexts.append("\n".join(pieces))
        sources.append(
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "lesson_id": lesson.id,
                "lesson_page_id": page.id,
                "page_number": page.page_number,
                "title": f"{lesson.title} · 第{page.page_number}页",
            }
        )
    if contexts:
        return contexts, sources

    materials = list(
        db.scalars(
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id, CourseMaterial.chapter_id == chapter_id, CourseMaterial.deleted_at.is_(None))
            .order_by(CourseMaterial.id)
            .limit(4)
        )
    )
    for material in materials:
        text = _extract_text_payload(material.extracted_text) or str(material.extracted_text or "").strip()
        if not text:
            continue
        contexts.append(f"{heading}\n资料：{material.title}\n{_trim_context(text, limit=1800)}")
        sources.append({"chapter_id": chapter.id, "chapter_title": chapter.title, "material_id": material.id, "material_title": material.title})
    return contexts, sources


def _course_context(db: Session, *, course_id: int, limit: int = 12) -> tuple[list[str], list[dict]]:
    course = db.get(Course, course_id)
    if course is None:
        return [], []
    contexts: list[str] = []
    sources: list[dict] = []
    course_heading = f"课程：{course.name}"
    if course.description:
        contexts.append(f"{course_heading}\n课程说明：{course.description}")
        sources.append({"course_id": course.id, "course_name": course.name, "type": "course"})

    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    if chapters:
        chapter_lines = [f"{item.order_index}. {item.title}" + (f"：{item.description}" if item.description else "") for item in chapters]
        contexts.append(f"{course_heading}\n章节结构：\n" + "\n".join(chapter_lines[:12]))
        sources.append({"course_id": course.id, "course_name": course.name, "type": "chapters"})

    chunks = list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.course_id == course_id)
            .order_by(KnowledgeChunk.chapter_id.is_(None), KnowledgeChunk.chapter_id, KnowledgeChunk.id)
            .limit(limit)
        )
    )
    for chunk in chunks:
        content = _trim_context(chunk.content, limit=1000)
        if not content:
            continue
        title = chunk.title or "资料片段"
        contexts.append(f"{course_heading}\n资料片段：{title}\n{content}")
        source = dict(chunk.source_meta or {})
        source.update({"course_id": course.id, "course_name": course.name, "chunk_id": chunk.id, "title": title})
        sources.append(source)
    if len(contexts) > (2 if chapters else 1):
        return contexts, sources

    page_rows = db.execute(
        select(LessonPage, Lesson)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .where(Lesson.course_id == course_id)
        .order_by(Lesson.chapter_id.is_(None), Lesson.chapter_id, Lesson.id, LessonPage.page_number)
        .limit(limit)
    )
    for page, lesson in page_rows:
        page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
        script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
        pieces = [course_heading, f"课时：{lesson.title}", f"页面：第{page.page_number}页 {page.page_title or ''}".strip()]
        if page_text:
            pieces.append(f"页面内容：{_trim_context(page_text, limit=1000)}")
        if script_text and script_text != page_text:
            pieces.append(f"讲解文稿：{_trim_context(script_text, limit=1000)}")
        if len(pieces) <= 3:
            continue
        contexts.append("\n".join(pieces))
        sources.append(
            {
                "course_id": course.id,
                "course_name": course.name,
                "lesson_id": lesson.id,
                "lesson_page_id": page.id,
                "page_number": page.page_number,
                "title": f"{lesson.title} · 第{page.page_number}页",
            }
        )
    if len(contexts) > (2 if chapters else 1):
        return contexts, sources

    materials = list(
        db.scalars(
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
            .order_by(CourseMaterial.chapter_id.is_(None), CourseMaterial.chapter_id, CourseMaterial.id)
            .limit(6)
        )
    )
    for material in materials:
        text = _extract_text_payload(material.extracted_text) or str(material.extracted_text or "").strip()
        if not text:
            continue
        contexts.append(f"{course_heading}\n资料：{material.title}\n{_trim_context(text, limit=1600)}")
        sources.append({"course_id": course.id, "course_name": course.name, "material_id": material.id, "material_title": material.title})
    return contexts, sources


def _merge_contexts(primary: list[str], chunks: list) -> list[str]:
    seen: set[str] = set()
    contexts: list[str] = []
    for text in [*primary, *(chunk.content for chunk in chunks)]:
        clean = " ".join(str(text or "").split())
        if not clean or clean in seen:
            continue
        seen.add(clean)
        contexts.append(str(text))
    return contexts


def _qa_contexts_and_sources(db: Session, *, course_id: int, payload: QAAskRequest, question_for_ai: str) -> tuple[list[str], list[dict], list]:
    course = db.get(Course, course_id)
    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    chapter_rows = [{"id": chapter.id, "title": chapter.title, "order_index": chapter.order_index} for chapter in chapters]
    classification = ai_service.classify_qa_question_scope(
        question=payload.question,
        course_name=course.name if course else "",
        chapters=chapter_rows,
        db=db,
    )
    scope = classification.get("scope")
    classified_chapter_id = classification.get("chapter_id")
    retrieval_chapter_id = payload.chapter_id if payload.chapter_id is not None else classified_chapter_id
    chunks = search_course_knowledge(
        db,
        course_id=course_id,
        query=question_for_ai,
        chapter_id=retrieval_chapter_id,
        lesson_page_id=payload.lesson_page_id,
        limit=4,
    )
    page_contexts, page_sources = _lesson_page_context(db, course_id=course_id, lesson_page_id=payload.lesson_page_id)
    chapter_contexts: list[str] = []
    chapter_sources: list[dict] = []
    course_contexts: list[str] = []
    course_sources: list[dict] = []
    if scope == "chapter_overview":
        chapter_contexts, chapter_sources = _chapter_context(db, course_id=course_id, chapter_id=retrieval_chapter_id)
    if scope == "course_overview" and not page_contexts and not chapter_contexts:
        course_contexts, course_sources = _course_context(db, course_id=course_id)
    contexts = _merge_contexts([*page_contexts, *chapter_contexts, *course_contexts], chunks)
    sources = [*page_sources, *chapter_sources, *course_sources, *(chunk.source_meta or {} for chunk in chunks)]
    return contexts, sources, chunks


def upload_qa_image(db: Session, *, user: User, course_id: int, upload: UploadFile) -> dict:
    _assert_student_course_access(db, course_id=course_id, user=user)
    suffix = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").lower()
    if suffix not in _IMAGE_SUFFIXES and not content_type.startswith("image/"):
        raise bad_request("请上传图片文件")
    relative_path, size_bytes = storage_service.save_upload(upload, folder=f"qa_images/course_{course_id}/user_{user.id}", db=db)
    if size_bytes <= 0:
        raise bad_request("图片文件为空")
    if size_bytes > _QA_IMAGE_LIMIT_BYTES:
        raise bad_request("图片大小不能超过 10MB")
    ocr_text = ocr_service.recognize(upload, db=db)
    return {
        "type": "image",
        "url": storage_service.public_url(relative_path, db=db),
        "filename": upload.filename or "image",
        "size_bytes": size_bytes,
        "ocr_text": ocr_text,
    }


def ask_question(db: Session, *, user: User, payload: QAAskRequest) -> QARecord:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    conversation = _get_or_create_course_conversation(db, user=user, payload=payload)
    history = list(
        db.scalars(
            select(QARecord).where(QARecord.conversation_id == conversation.id).order_by(QARecord.created_at.asc())
        )
    )
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    contexts, sources, _chunks = _qa_contexts_and_sources(db, course_id=payload.course_id, payload=payload, question_for_ai=question_for_ai)
    answer, out_of_scope, thinking_process = ai_service.answer_question(
        question=question_for_ai,
        contexts=contexts,
        history=[item.question for item in history[-3:]],
        db=db,
    )
    record = QARecord(
        conversation_id=conversation.id,
        course_id=payload.course_id,
        user_id=user.id,
        lesson_page_id=payload.lesson_page_id,
        question=payload.question,
        answer=answer,
        thinking_process=thinking_process,
        is_out_of_scope=out_of_scope,
        sources=sources,
        attachments=attachments,
        keywords=ai_service.extract_keywords(payload.question),
    )
    db.add(record)
    log_ai_usage(
        db,
        module="qa",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(question_for_ai),
        completion_chars=len(answer),
        success=not out_of_scope,
        error_message="out_of_scope" if out_of_scope else None,
    )
    db.commit()
    db.refresh(record)
    return record


def ask_question_stream(db: Session, *, user: User, payload: QAAskRequest) -> Iterator[dict]:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    conversation = _get_or_create_course_conversation(db, user=user, payload=payload)
    history = list(
        db.scalars(
            select(QARecord).where(QARecord.conversation_id == conversation.id).order_by(QARecord.created_at.asc())
        )
    )
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    contexts, sources, _chunks = _qa_contexts_and_sources(db, course_id=payload.course_id, payload=payload, question_for_ai=question_for_ai)
    out_of_scope = not contexts
    answer_parts: list[str] = []
    thought_parts: list[str] = []
    tag_state: dict[str, object] = {"buffer": "", "in_think": False}
    ai_error_message: str | None = None

    try:
        for delta in ai_service.stream_answer_question(
            question=question_for_ai,
            contexts=contexts,
            history=[item.question for item in history[-3:]],
            db=db,
        ):
            if delta.kind == "reasoning":
                yield from _stream_text_delta("thought", delta.text, answer_parts, thought_parts)
                continue
            for kind, text in _split_thinking_tags(tag_state, delta.text):
                yield from _stream_text_delta(kind, text, answer_parts, thought_parts)
    except Exception as exc:
        answer_parts.clear()
        thought_parts.clear()
        tag_state = {"buffer": "", "in_think": False}
        try:
            fallback_answer, fallback_out_of_scope, fallback_thinking = ai_service.answer_question(
                question=question_for_ai,
                contexts=contexts,
                history=[item.question for item in history[-3:]],
                db=db,
            )
            out_of_scope = fallback_out_of_scope
            if fallback_thinking:
                yield from _stream_text_delta("thought", fallback_thinking, answer_parts, thought_parts)
            for kind, text in _split_thinking_tags(tag_state, fallback_answer):
                yield from _stream_text_delta(kind, text, answer_parts, thought_parts)
        except Exception as fallback_exc:
            ai_error_message = str(fallback_exc or exc)
            answer = "AI 服务暂时不可用，请稍后重试，或联系管理员检查问答模型配置。"
            answer_parts.append(answer)
            yield {"event": "delta", "data": {"type": "answer", "text": answer}}

    for kind, text in _flush_thinking_tags(tag_state):
        yield from _stream_text_delta(kind, text, answer_parts, thought_parts)

    answer = "".join(answer_parts).strip()
    thinking_process = "".join(thought_parts).strip() or None
    if not answer:
        answer = "当前没有生成有效回答，请换一种问法或稍后重试。"
        yield {"event": "delta", "data": {"type": "answer", "text": answer}}
    record = QARecord(
        conversation_id=conversation.id,
        course_id=payload.course_id,
        user_id=user.id,
        lesson_page_id=payload.lesson_page_id,
        question=payload.question,
        answer=answer,
        thinking_process=thinking_process,
        is_out_of_scope=out_of_scope,
        sources=sources,
        attachments=attachments,
        keywords=ai_service.extract_keywords(payload.question),
    )
    db.add(record)
    log_ai_usage(
        db,
        module="qa",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(question_for_ai),
        completion_chars=len(answer),
        success=not out_of_scope and ai_error_message is None,
        error_message=ai_error_message[:500] if ai_error_message else ("out_of_scope" if out_of_scope else None),
    )
    db.commit()
    db.refresh(record)
    yield {
        "event": "final",
        "data": {
            "conversation_id": record.conversation_id,
            "record_id": record.id,
            "question": record.question,
            "answer": record.answer,
            "thinking_process": record.thinking_process,
            "is_out_of_scope": record.is_out_of_scope,
            "sources": record.sources or [],
            "attachments": record.attachments or [],
        },
    }


def list_history(db: Session, *, user: User, course_id: int | None = None, keyword: str | None = None) -> list[QARecord]:
    if user.role == UserRole.STUDENT.value:
        if course_id is None:
            course_ids = list(
                db.scalars(select(CourseMembership.course_id).where(CourseMembership.user_id == user.id).limit(2))
            )
            if len(course_ids) != 1:
                return []
            course_id = course_ids[0]
        _assert_student_course_access(db, course_id=course_id, user=user)
    statement = select(QARecord).where(QARecord.user_id == user.id)
    if course_id is not None:
        statement = statement.where(QARecord.course_id == course_id)
    if keyword:
        like = f"%{keyword}%"
        statement = statement.where(or_(QARecord.question.like(like), QARecord.answer.like(like)))
    return list(db.scalars(statement.order_by(QARecord.created_at.desc())))


def update_favorite(db: Session, *, record_id: int, user: User, is_favorite: bool) -> QARecord:
    record = db.scalar(select(QARecord).where(QARecord.id == record_id, QARecord.user_id == user.id))
    if record is None:
        raise not_found("问答记录不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=record.course_id, user=user)
    record.is_favorite = is_favorite
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_feedback(db: Session, *, record_id: int, user: User, feedback: str, feedback_comment: str | None) -> QARecord:
    if feedback not in {item.value for item in QAFeedback}:
        raise bad_request("反馈值不合法")
    record = db.scalar(select(QARecord).where(QARecord.id == record_id, QARecord.user_id == user.id))
    if record is None:
        raise not_found("问答记录不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=record.course_id, user=user)
    record.feedback = feedback
    record.feedback_comment = feedback_comment
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
