from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

import re

from app.db.models import Chapter, KnowledgeChunk, KnowledgePoint, LessonPage
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
    lesson_id: int | None = None,
    lesson_page_id: int | None = None,
    limit: int = 5,
) -> list[KnowledgeChunk]:
    try:
        rows = vector_store.query_course(
            db,
            course_id=course_id,
            query=query,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            lesson_page_id=lesson_page_id,
            limit=limit,
        )
    except Exception:
        rows = []
    if not rows:
        backfill_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
        if chapter_id is not None:
            backfill_statement = backfill_statement.where(KnowledgeChunk.chapter_id == chapter_id)
        if lesson_id is not None:
            backfill_statement = backfill_statement.where(
                KnowledgeChunk.lesson_page_id.in_(select(LessonPage.id).where(LessonPage.lesson_id == lesson_id))
            )
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
                    lesson_id=lesson_id,
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
            lesson_id=lesson_id,
            lesson_page_id=lesson_page_id,
            limit=limit,
        )
    statement = select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids), KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgeChunk.chapter_id == chapter_id)
    if lesson_id is not None:
        statement = statement.where(KnowledgeChunk.lesson_page_id.in_(select(LessonPage.id).where(LessonPage.lesson_id == lesson_id)))
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
    lesson_id: int | None,
    lesson_page_id: int | None,
    limit: int,
) -> list[KnowledgeChunk]:
    statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
    if chapter_id is not None:
        statement = statement.where(KnowledgeChunk.chapter_id == chapter_id)
    if lesson_id is not None:
        statement = statement.where(KnowledgeChunk.lesson_page_id.in_(select(LessonPage.id).where(LessonPage.lesson_id == lesson_id)))
    if lesson_page_id is not None:
        statement = statement.where(KnowledgeChunk.lesson_page_id == lesson_page_id)
    chunks = list(db.scalars(statement.order_by(KnowledgeChunk.chapter_id.is_(None), KnowledgeChunk.chapter_id, KnowledgeChunk.id).limit(160)))
    if not chunks:
        return []
    keywords = _query_terms(query)
    page_numbers = _page_numbers_from_query(query)

    def score(chunk: KnowledgeChunk) -> tuple[int, int]:
        source_meta = dict(chunk.source_meta or {})
        text = f"{chunk.title} {chunk.content}".lower()
        keyword_score = sum(2 + min(len(keyword), 8) for keyword in keywords if keyword and keyword in text)
        token_score = sum(3 for token in chunk.tokens or [] if str(token).lower() in keywords)
        page_score = 0
        try:
            page_number = int(source_meta.get("page_number") or 0)
        except (TypeError, ValueError):
            page_number = 0
        if page_number and page_number in page_numbers:
            page_score = 80
        return keyword_score + token_score + page_score, -int(chunk.id)

    ranked = sorted(chunks, key=score, reverse=True)
    return [chunk for chunk in ranked if score(chunk)[0] > 0][:limit] or ranked[:limit]


def _page_numbers_from_query(query: str) -> set[int]:
    numbers: set[int] = set()
    for pattern in (r"第\s*(\d{1,4})\s*页", r"(?<!\d)(\d{1,4})\s*页", r"\bp\s*(\d{1,4})\b"):
        for value in re.findall(pattern, query, flags=re.IGNORECASE):
            number = int(value)
            if number > 0:
                numbers.add(number)
    return numbers


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    candidates = [*ai_service.extract_keywords(query, limit=12), *re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", query)]
    for phrase in re.findall(r"[\u4e00-\u9fff]{3,16}", query):
        for size in (4, 3, 2):
            candidates.extend(phrase[index : index + size] for index in range(max(len(phrase) - size + 1, 0)))
    stopwords = {"这个", "那个", "什么", "请问", "关于", "内容", "解释", "怎么", "如何", "为什么", "当前问题", "前序对话"}
    for item in candidates:
        term = str(item).strip().lower()
        if not term or term.isdigit() or len(term) < 2 or term in stopwords:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:16]


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
