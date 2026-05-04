from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, KnowledgeChunk, KnowledgePoint
from app.services.ai import ai_service
from app.services.vector_store import vector_store


def _clean_excerpt(value: str, limit: int = 260) -> str:
    return " ".join(value.split())[:limit]


def _local_knowledge_explanation(*, name: str, difficulty: str, source_text: str) -> dict[str, str]:
    source = _clean_excerpt(source_text)
    tone = {
        "beginner": "用最直观的方式先理解它是什么、为什么需要它。",
        "standard": "从定义、原理、应用场景三个层面完整掌握。",
        "advanced": "进一步关注限制条件、变形思路和综合题中的使用方式。",
    }.get(difficulty, "从定义、原理、应用场景三个层面完整掌握。")
    return {
        "name": name,
        "difficulty": difficulty,
        "definition": f"{name}：{tone}",
        "principle": f"相关原理材料摘要：{source or '可结合课程资料进一步补充。'}",
        "example": f"例题建议：围绕 {name} 设计一道从条件识别到步骤推导的典型题。",
        "common_mistake": f"常见错误：对 {name} 的适用范围理解不清。",
    }


def search_course_knowledge(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None = None,
    lesson_page_id: int | None = None,
    limit: int = 5,
) -> list[KnowledgeChunk]:
    try:
        rows = vector_store.query_course(
            db,
            course_id=course_id,
            query=query,
            chapter_id=chapter_id,
            lesson_page_id=lesson_page_id,
            limit=limit,
        )
    except Exception:
        rows = []
    if not rows:
        backfill_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
        if chapter_id is not None:
            backfill_statement = backfill_statement.where(KnowledgeChunk.chapter_id == chapter_id)
        if lesson_page_id is not None:
            backfill_statement = backfill_statement.where(KnowledgeChunk.lesson_page_id == lesson_page_id)
        chunks_to_index = list(db.scalars(backfill_statement))
        if chunks_to_index:
            try:
                vector_store.upsert_chunks(db, chunks=chunks_to_index)
                db.commit()
                rows = vector_store.query_course(
                    db,
                    course_id=course_id,
                    query=query,
                    chapter_id=chapter_id,
                    lesson_page_id=lesson_page_id,
                    limit=limit,
                )
            except Exception:
                db.rollback()
                rows = []
    chunk_ids = [chunk_id for chunk_id, _ in rows]
    if not chunk_ids:
        return _relational_chunk_fallback(
            db,
            course_id=course_id,
            query=query,
            chapter_id=chapter_id,
            lesson_page_id=lesson_page_id,
            limit=limit,
        )
    statement = select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids), KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgeChunk.chapter_id == chapter_id)
    if lesson_page_id is not None:
        statement = statement.where(KnowledgeChunk.lesson_page_id == lesson_page_id)
    chunks = {chunk.id: chunk for chunk in db.scalars(statement)}
    return [chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in chunks][:limit]


def _relational_chunk_fallback(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None,
    lesson_page_id: int | None,
    limit: int,
) -> list[KnowledgeChunk]:
    statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgeChunk.chapter_id == chapter_id)
    if lesson_page_id is not None:
        statement = statement.where(KnowledgeChunk.lesson_page_id == lesson_page_id)
    chunks = list(db.scalars(statement.order_by(KnowledgeChunk.chapter_id.is_(None), KnowledgeChunk.chapter_id, KnowledgeChunk.id).limit(80)))
    if not chunks:
        return []
    keywords = [item.lower() for item in ai_service.extract_keywords(query, limit=10)]

    def score(chunk: KnowledgeChunk) -> tuple[int, int]:
        text = f"{chunk.title} {chunk.content}".lower()
        keyword_score = sum(1 for keyword in keywords if keyword and keyword in text)
        token_score = sum(1 for token in chunk.tokens or [] if str(token).lower() in keywords)
        return keyword_score + token_score, -int(chunk.id)

    return sorted(chunks, key=score, reverse=True)[:limit]


def ensure_knowledge_points(db: Session, *, course_id: int, chapter_id: int | None = None) -> list[KnowledgePoint]:
    statement = select(KnowledgePoint).where(KnowledgePoint.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgePoint.chapter_id == chapter_id)
    existing = list(db.scalars(statement))
    if existing:
        return existing
    chunk_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        chunk_statement = chunk_statement.where(KnowledgeChunk.chapter_id == chapter_id)
    chunks = list(db.scalars(chunk_statement))
    counter: Counter[str] = Counter()
    source_text: dict[str, str] = {}
    for chunk in chunks:
        for keyword in ai_service.extract_knowledge_points(chunk.content, db=db):
            counter[keyword] += 1
            source_text.setdefault(keyword, chunk.content)
    created: list[KnowledgePoint] = []
    for keyword, _ in counter.most_common(8):
        content = {
            "beginner": _local_knowledge_explanation(name=keyword, difficulty="beginner", source_text=source_text[keyword]),
            "standard": _local_knowledge_explanation(name=keyword, difficulty="standard", source_text=source_text[keyword]),
            "advanced": _local_knowledge_explanation(name=keyword, difficulty="advanced", source_text=source_text[keyword]),
        }
        point = KnowledgePoint(
            course_id=course_id,
            chapter_id=chapter_id,
            name=keyword,
            description=f"{keyword} 相关知识点",
            content_by_level=content,
        )
        db.add(point)
        created.append(point)
    db.commit()
    return created


def get_chapter_name(db: Session, chapter_id: int | None) -> str | None:
    if chapter_id is None:
        return None
    chapter = db.get(Chapter, chapter_id)
    return chapter.title if chapter else None
