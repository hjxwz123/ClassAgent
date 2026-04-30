from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, KnowledgeChunk, KnowledgePoint
from app.services.ai import ai_service


def search_course_knowledge(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None = None,
    lesson_page_id: int | None = None,
    limit: int = 5,
) -> list[KnowledgeChunk]:
    statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgeChunk.chapter_id == chapter_id)
    chunks = list(db.scalars(statement))
    query_tokens = ai_service.extract_keywords(query, limit=10)
    scored: list[tuple[int, KnowledgeChunk]] = []
    for chunk in chunks:
        tokens = set(chunk.tokens or [])
        score = sum(1 for token in query_tokens if token.lower() in tokens)
        if lesson_page_id is not None and chunk.lesson_page_id == lesson_page_id:
            score += 2
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:limit]]


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
        for keyword in ai_service.extract_knowledge_points(chunk.content):
            counter[keyword] += 1
            source_text.setdefault(keyword, chunk.content)
    created: list[KnowledgePoint] = []
    for keyword, _ in counter.most_common(8):
        content = {
            "beginner": ai_service.generate_knowledge_explanation(
                name=keyword, difficulty="beginner", source_text=source_text[keyword]
            ),
            "standard": ai_service.generate_knowledge_explanation(
                name=keyword, difficulty="standard", source_text=source_text[keyword]
            ),
            "advanced": ai_service.generate_knowledge_explanation(
                name=keyword, difficulty="advanced", source_text=source_text[keyword]
            ),
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
