from __future__ import annotations

import logging
import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, KnowledgeChunk, KnowledgePoint, LessonPage
from app.services.ai import ai_service
from app.services.retrieval import build_retrieval_query_variants, page_numbers_from_query, query_terms, score_text_for_query
from app.services.runtime_settings import runtime_setting_float
from app.services.vector_store import vector_store

LOGGER = logging.getLogger(__name__)


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
    query_variants = build_retrieval_query_variants(query, limit=6)
    try:
        rows = _query_course_variants(
            db,
            course_id=course_id,
            queries=query_variants,
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
            # 向量索引缺失时的自愈回填：会同步重嵌入整门课程的全部 chunk，是问答"卡在检索阶段
            # 数分钟"的常见原因。打点记录数量与耗时，便于定位；若频繁触发应排查向量库持久化。
            LOGGER.warning("QA 检索触发向量回填：course_id=%s 待重嵌入 chunk 数=%s（同步重建索引，可能较慢）", course_id, len(chunks_to_index))
            backfill_started = time.monotonic()
            try:
                vector_store.upsert_chunks(db, chunks=chunks_to_index)
                db.commit()
                LOGGER.warning("QA 检索向量回填完成：course_id=%s 耗时=%.1fs", course_id, time.monotonic() - backfill_started)
                rows = _query_course_variants(
                    db,
                    course_id=course_id,
                    queries=query_variants,
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
    chunks_by_id = {chunk.id: chunk for chunk in db.scalars(statement)}
    ordered_chunks = [chunks_by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in chunks_by_id]
    distances = {chunk_id: distance for chunk_id, distance in rows}
    return _rank_chunks_for_query(query=query, chunks=ordered_chunks, distances=distances, limit=limit)


def _chunk_page_number(chunk: KnowledgeChunk) -> int | None:
    source_meta = dict(chunk.source_meta or {})
    try:
        page_number = int(source_meta.get("page_number") or 0)
    except (TypeError, ValueError):
        page_number = 0
    return page_number or None


def _rank_chunks_for_query(
    *,
    query: str,
    chunks: list[KnowledgeChunk],
    distances: dict[int, float | None],
    limit: int,
) -> list[KnowledgeChunk]:
    if not chunks:
        return []
    keywords = query_terms(query, limit=24)
    page_numbers = page_numbers_from_query(query)

    def score(index: int, chunk: KnowledgeChunk) -> tuple[float, int, float, int]:
        page_number = _chunk_page_number(chunk)
        lexical_score = score_text_for_query(title=chunk.title, text=chunk.content, page_number=page_number, query=query, term_limit=24)
        token_score = sum(3 for token in chunk.tokens or [] if str(token).lower() in keywords)
        title = str(chunk.title or "").lower()
        title_score = sum(6 for keyword in keywords if keyword in title)
        page_score = 80 if page_number is not None and page_number in page_numbers else 0
        distance = distances.get(chunk.id)
        vector_score = 30.0 if distance is None else max(0.0, 90.0 - min(float(distance), 2.0) * 60.0)
        total = float(lexical_score + token_score + title_score + page_score) + vector_score
        distance_sort = -float(distance) if distance is not None else -9_999.0
        return total, lexical_score + token_score + title_score + page_score, distance_sort, -index

    ranked = sorted(enumerate(chunks), key=lambda item: score(item[0], item[1]), reverse=True)
    return [chunk for _index, chunk in ranked[:limit]]


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
    keywords = query_terms(query)
    page_numbers = page_numbers_from_query(query)

    def score(chunk: KnowledgeChunk) -> tuple[int, int]:
        source_meta = dict(chunk.source_meta or {})
        keyword_score = score_text_for_query(title=chunk.title, text=chunk.content, page_number=None, query=query)
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


def _query_course_variants(
    db: Session,
    *,
    course_id: int,
    queries: list[str],
    chapter_id: int | None,
    lesson_id: int | None,
    lesson_page_id: int | None,
    limit: int,
) -> list[tuple[int, float | None]]:
    merged: dict[int, tuple[float, int, int, float | None]] = {}
    candidate_limit = max(limit * 3, 12)
    per_query_limit = candidate_limit
    # 管理端「召回相似度阈值」：余弦相似度低于阈值的召回直接丢弃（distance = 1 - 相似度）。
    # vector_store 内部的 vector_max_distance(默认 0.9) 只是兜底粗筛，这里才是业务阈值。
    min_similarity = runtime_setting_float(db, "qa.retrieval.min_similarity", 0.35, minimum=0.0, maximum=0.99)
    max_distance = 1.0 - min_similarity
    # 一次性批量嵌入全部查询变体（单次 embedding 请求），再用预算向量逐个检索；
    # 避免旧实现对每个变体各发一次嵌入请求——慢/多变体时会把检索阶段拖到数十秒甚至数分钟。
    try:
        variant_embeddings = ai_service.embed_texts(db, list(queries))
    except Exception:
        variant_embeddings = []
    for query_index, variant in enumerate(queries):
        embedding = variant_embeddings[query_index] if query_index < len(variant_embeddings) else None
        if not embedding:
            continue
        rows = vector_store.query_course_by_embedding(
            db,
            course_id=course_id,
            embedding=embedding,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            lesson_page_id=lesson_page_id,
            limit=per_query_limit,
        )
        for row_index, (chunk_id, distance) in enumerate(rows):
            if distance is not None and distance > max_distance:
                continue
            rank = distance if distance is not None else 9_999.0
            candidate = (rank, query_index, row_index, distance)
            current = merged.get(chunk_id)
            if current is None or candidate < current:
                merged[chunk_id] = candidate
    ranked = sorted(merged.items(), key=lambda item: item[1])
    return [(chunk_id, meta[3]) for chunk_id, meta in ranked[:candidate_limit]]


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
