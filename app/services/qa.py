from collections.abc import Iterator
from pathlib import Path
from time import sleep

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.enums import QAFeedback, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import CourseMembership, QAConversation, QARecord, User
from app.schemas.qa import QAAskRequest
from app.services.ai import ai_service
from app.services.knowledge import search_course_knowledge
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
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(
            select(QAConversation).where(QAConversation.id == payload.conversation_id, QAConversation.user_id == user.id)
        )
    if conversation is None:
        conversation = QAConversation(course_id=payload.course_id, user_id=user.id, title=payload.question[:30])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    history = list(
        db.scalars(
            select(QARecord).where(QARecord.conversation_id == conversation.id).order_by(QARecord.created_at.asc())
        )
    )
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    chunks = search_course_knowledge(
        db,
        course_id=payload.course_id,
        query=question_for_ai,
        chapter_id=payload.chapter_id,
        lesson_page_id=payload.lesson_page_id,
        limit=4,
    )
    answer, out_of_scope, thinking_process = ai_service.answer_question(
        question=question_for_ai,
        contexts=[chunk.content for chunk in chunks],
        history=[item.question for item in history[-3:]],
        db=db,
    )
    sources = [chunk.source_meta or {} for chunk in chunks]
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
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(
            select(QAConversation).where(QAConversation.id == payload.conversation_id, QAConversation.user_id == user.id)
        )
    if conversation is None:
        conversation = QAConversation(course_id=payload.course_id, user_id=user.id, title=payload.question[:30])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    history = list(
        db.scalars(
            select(QARecord).where(QARecord.conversation_id == conversation.id).order_by(QARecord.created_at.asc())
        )
    )
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    chunks = search_course_knowledge(
        db,
        course_id=payload.course_id,
        query=question_for_ai,
        chapter_id=payload.chapter_id,
        lesson_page_id=payload.lesson_page_id,
        limit=4,
    )
    sources = [chunk.source_meta or {} for chunk in chunks]
    out_of_scope = not chunks
    answer_parts: list[str] = []
    thought_parts: list[str] = []
    tag_state: dict[str, object] = {"buffer": "", "in_think": False}
    ai_error_message: str | None = None

    try:
        for delta in ai_service.stream_answer_question(
            question=question_for_ai,
            contexts=[chunk.content for chunk in chunks],
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
                contexts=[chunk.content for chunk in chunks],
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
    record.feedback = feedback
    record.feedback_comment = feedback_comment
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
