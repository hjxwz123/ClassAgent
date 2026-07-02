from __future__ import annotations

import logging
import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, KnowledgeChunk, KnowledgePoint, LessonPage
from app.services.ai import ai_service
from app.services.retrieval import build_retrieval_query_variants, defocused_query_text, page_numbers_from_query, query_terms, score_text_for_query
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


# 向量索引"部分缺失"体检的每课程节流间隔：体检需要向向量库拉全量已索引 id，不宜每次查询都做。
_VECTOR_INDEX_CHECK_INTERVAL_SECONDS = 600.0
_vector_index_last_check: dict[int, float] = {}


def _backfill_missing_chunks(db: Session, *, course_id: int, scope_statement) -> int:
    """差集增量回填：只重嵌入向量库缺失的 chunk，而非整课重建。返回回填数量。

    覆盖两类场景：向量库整体丢失（缺失=全部，等价旧的整课回填）；以及 ingest 阶段
    个别资料嵌入失败留下的"部分缺失"（旧逻辑永不自愈）。同步执行、带耗时打点。
    """
    chunks = list(db.scalars(scope_statement))
    if not chunks:
        return 0
    try:
        indexed = vector_store.indexed_chunk_ids(db, course_id=course_id)
    except Exception:
        indexed = set()
    missing = [chunk for chunk in chunks if chunk.id not in indexed]
    if not missing:
        return 0
    LOGGER.warning(
        "QA 检索触发向量增量回填：course_id=%s 缺失 chunk=%s/%s（同步重嵌入，可能较慢）",
        course_id, len(missing), len(chunks),
    )
    backfill_started = time.monotonic()
    vector_store.upsert_chunks(db, chunks=missing)
    db.commit()
    LOGGER.warning("QA 检索向量增量回填完成：course_id=%s 耗时=%.1fs", course_id, time.monotonic() - backfill_started)
    return len(missing)


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
    except Exception as exc:
        LOGGER.warning("QA 向量检索失败，退化为关键词兜底：course_id=%s err=%s", course_id, exc)
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
        try:
            if _backfill_missing_chunks(db, course_id=course_id, scope_statement=backfill_statement):
                rows = _query_course_variants(
                    db,
                    course_id=course_id,
                    queries=query_variants,
                    chapter_id=chapter_id,
                    lesson_id=lesson_id,
                    lesson_page_id=lesson_page_id,
                    limit=limit,
                )
        except Exception as exc:
            db.rollback()
            LOGGER.warning("QA 检索向量回填失败：course_id=%s err=%s", course_id, exc)
            rows = []
    else:
        # 部分缺失自愈：旧逻辑只在"查询全空"时回填，老资料已有索引时新资料嵌入失败
        # 便永远不可语义召回且无人知道。这里按课程做节流的差集体检（每 10 分钟至多一次），
        # 发现缺失 chunk 就增量回填并重查一次，让新资料立即可召回。
        now = time.monotonic()
        if now - _vector_index_last_check.get(course_id, 0.0) >= _VECTOR_INDEX_CHECK_INTERVAL_SECONDS:
            _vector_index_last_check[course_id] = now
            try:
                course_statement = select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)
                if _backfill_missing_chunks(db, course_id=course_id, scope_statement=course_statement):
                    rows = _query_course_variants(
                        db,
                        course_id=course_id,
                        queries=query_variants,
                        chapter_id=chapter_id,
                        lesson_id=lesson_id,
                        lesson_page_id=lesson_page_id,
                        limit=limit,
                    )
            except Exception as exc:
                db.rollback()
                LOGGER.warning("QA 检索向量增量回填失败：course_id=%s err=%s", course_id, exc)
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
    positive = [chunk for chunk in ranked if score(chunk)[0] > 0][:limit]
    if positive:
        return positive
    # 指代型追问("这个能再举个例子吗")经 focused_query_text 聚焦后只剩代词，词法必然
    # 零命中：退回含前序对话的完整文本重打分，让上一轮话题词(如"矩阵")作为真实锚点。
    defocused = defocused_query_text(query)
    if defocused and defocused != query:
        history_keywords = query_terms(defocused)

        def defocused_score(chunk: KnowledgeChunk) -> tuple[int, int]:
            keyword_score = score_text_for_query(title=chunk.title, text=chunk.content, page_number=None, query=defocused)
            token_score = sum(3 for token in chunk.tokens or [] if str(token).lower() in history_keywords)
            return keyword_score + token_score, -int(chunk.id)

        ranked = sorted(chunks, key=defocused_score, reverse=True)
        positive = [chunk for chunk in ranked if defocused_score(chunk)[0] > 0][:limit]
        if positive:
            return positive
    # 仍零命中：不再返回按 id 排序的头部 chunk 冒充相关资料——那会让上游 contexts 非空、
    # 误判 in-scope，迫使模型"依据"无关内容强答。返回空，让上游走资料外/通用回答分支。
    return []


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
    # 默认与 bootstrap 种子(0.40)保持一致；0.28 对中文嵌入模型偏松，弱相关片段易过线诱发错答。
    min_similarity = runtime_setting_float(db, "qa.retrieval.min_similarity", 0.40, minimum=0.0, maximum=0.99)
    max_distance = 1.0 - min_similarity
    # 一次性批量嵌入全部查询变体（单次 embedding 请求），再用预算向量逐个检索；
    # 避免旧实现对每个变体各发一次嵌入请求——慢/多变体时会把检索阶段拖到数十秒甚至数分钟。
    try:
        variant_embeddings = ai_service.embed_texts(db, list(queries))
    except Exception as exc:
        # 嵌入失败会让全部变体被跳过、语义检索无声退化为关键词兜底——必须留痕，否则
        # 嵌入服务故障期间"答案频繁跑偏"无从排障。
        LOGGER.warning("QA 查询嵌入失败，语义检索退化为关键词兜底：course_id=%s err=%s", course_id, exc)
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
