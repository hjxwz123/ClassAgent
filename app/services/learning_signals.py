from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.enums import LearningSignalSource
from app.db.models import KnowledgePoint, QARecord, StudentLearningSignal, User
from app.services.ai import ai_service
from app.services.knowledge import ensure_knowledge_points


LEARNING_SIGNAL_SOURCE_QA = LearningSignalSource.QA.value
QA_SIGNAL_CONFIDENCE_MIN = 0.35
QA_SIGNAL_MAX_POINTS = 3

_QA_SIGNAL_INTENT_SCORES = {
    "error_explanation": 0.8,
    "problem_solving": 0.6,
    "concept_confusion": 0.4,
    "method_confusion": 0.4,
    "difference_compare": 0.35,
    "review_summary": 0.15,
}


def _compact(value: str) -> str:
    return "".join(str(value or "").lower().split())


def _attachment_text(record: QARecord) -> str:
    pieces: list[str] = []
    for attachment in record.attachments or []:
        if isinstance(attachment, dict):
            text = str(attachment.get("ocr_text") or "").strip()
            if text:
                pieces.append(text)
    return "\n".join(pieces)


def _infer_qa_intent(question: str) -> str:
    text = _compact(question)
    if not text:
        return "other"
    if any(token in text for token in ("为什么错", "哪里错", "错在哪", "为什么不对", "为什么选", "为什么不是")):
        return "error_explanation"
    if any(token in text for token in ("这道题", "这题", "第几题", "题干", "怎么做", "求解", "解题", "证明", "计算", "答案", "选哪个", "选什么")):
        return "problem_solving"
    if any(token in text for token in ("怎么用", "如何用", "公式", "方法", "步骤", "适用条件", "什么时候用")):
        return "method_confusion"
    if any(token in text for token in ("区别", "不同", "比较", "联系", "关系")):
        return "difference_compare"
    if any(token in text for token in ("总结", "复习", "重点", "梳理", "归纳", "提纲")):
        return "review_summary"
    if any(token in text for token in ("是什么", "什么是", "概念", "定义", "原理", "理解", "为什么", "讲一下", "解释")):
        return "concept_confusion"
    return "other"


def _match_points(points: list[KnowledgePoint], text: str) -> list[KnowledgePoint]:
    haystack = _compact(text)
    if not haystack:
        return []
    matched: list[KnowledgePoint] = []
    seen: set[int] = set()
    for point in points:
        name = str(point.name or "").strip()
        key = _compact(name)
        if len(key) < 2 or point.id in seen:
            continue
        if key in haystack:
            matched.append(point)
            seen.add(point.id)
    return matched


def _match_points_by_names(points: list[KnowledgePoint], names: list[str]) -> list[KnowledgePoint]:
    if not names:
        return []
    matched: list[KnowledgePoint] = []
    seen: set[int] = set()
    normalized_names = [_compact(name) for name in names if len(_compact(name)) >= 2]
    for point in points:
        key = _compact(point.name)
        if len(key) < 2 or point.id in seen:
            continue
        if any(key == name or key in name or name in key for name in normalized_names):
            matched.append(point)
            seen.add(point.id)
    return matched


def _course_signal_points(db: Session, *, course_id: int) -> list[KnowledgePoint]:
    points = list(db.scalars(select(KnowledgePoint).where(KnowledgePoint.course_id == course_id).order_by(KnowledgePoint.id)))
    if points:
        return points
    return ensure_knowledge_points(db, course_id=course_id, chapter_id=None)


def _qa_signal_candidates(db: Session, *, record: QARecord, points: list[KnowledgePoint]) -> tuple[str, float, list[KnowledgePoint]]:
    attachment_text = _attachment_text(record)
    direct_text = "\n".join(part for part in (record.question, attachment_text) if part)
    intent = _infer_qa_intent(direct_text)
    direct_matches = _match_points(points, direct_text)
    if direct_matches:
        confidence = 0.85 if intent != "review_summary" else 0.65
        return (intent if intent != "other" else "concept_confusion", confidence, direct_matches[:QA_SIGNAL_MAX_POINTS])

    if intent == "other":
        return "other", 0.0, []

    answer_matches = _match_points(points, record.answer or "")
    if answer_matches:
        confidence = 0.65 if intent != "review_summary" else 0.5
        return intent, confidence, answer_matches[:QA_SIGNAL_MAX_POINTS]

    extracted_names = ai_service.extract_knowledge_points(direct_text[:4000], db=db)
    extracted_matches = _match_points_by_names(points, extracted_names)
    if extracted_matches:
        return intent, 0.6, extracted_matches[:QA_SIGNAL_MAX_POINTS]

    return intent, 0.0, []


def _signal_score(intent: str, confidence: float) -> float:
    base_score = _QA_SIGNAL_INTENT_SCORES.get(intent, 0.0)
    if base_score <= 0 or confidence < QA_SIGNAL_CONFIDENCE_MIN:
        return 0.0
    return round(max(0.05, min(1.0, base_score * confidence)), 2)


def record_qa_learning_signals(db: Session, *, user: User, record: QARecord) -> list[StudentLearningSignal]:
    if record.is_out_of_scope:
        return []
    try:
        points = _course_signal_points(db, course_id=record.course_id)
        if not points:
            return []
        intent, confidence, matched_points = _qa_signal_candidates(db, record=record, points=points)
        score = _signal_score(intent, confidence)
        if not matched_points or score <= 0:
            return []

        created: list[StudentLearningSignal] = []
        for point in matched_points:
            existing = db.scalar(
                select(StudentLearningSignal).where(
                    StudentLearningSignal.user_id == user.id,
                    StudentLearningSignal.source_type == LEARNING_SIGNAL_SOURCE_QA,
                    StudentLearningSignal.source_id == record.id,
                    StudentLearningSignal.knowledge_point_id == point.id,
                )
            )
            if existing is not None:
                continue
            signal = StudentLearningSignal(
                user_id=user.id,
                course_id=record.course_id,
                knowledge_point_id=point.id,
                source_type=LEARNING_SIGNAL_SOURCE_QA,
                source_id=record.id,
                intent=intent,
                score=score,
                confidence=round(confidence, 2),
                evidence_text=(record.question or "")[:500],
                metadata_json={
                    "qa_record_id": record.id,
                    "conversation_id": record.conversation_id,
                    "knowledge_point": point.name,
                    "matched_from": "qa_history",
                },
            )
            db.add(signal)
            created.append(signal)
        if created:
            db.commit()
            for signal in created:
                db.refresh(signal)
        return created
    except Exception:
        db.rollback()
        return []


def learning_signal_point_stats(
    db: Session,
    *,
    course_id: int,
    user_id: int | None = None,
    point_ids: list[int] | None = None,
) -> dict[int, dict[str, float | int]]:
    # #49: qa_signal_count 应仅统计 source_type==QA 的信号，learning_signal_count 保留总数。
    qa_count_expr = func.sum(
        case((StudentLearningSignal.source_type == LEARNING_SIGNAL_SOURCE_QA, 1), else_=0)
    )
    statement = (
        select(
            StudentLearningSignal.knowledge_point_id,
            func.count(StudentLearningSignal.id),
            qa_count_expr,
            func.sum(StudentLearningSignal.score),
        )
        .where(StudentLearningSignal.course_id == course_id)
        .group_by(StudentLearningSignal.knowledge_point_id)
    )
    if user_id is not None:
        statement = statement.where(StudentLearningSignal.user_id == user_id)
    if point_ids:
        statement = statement.where(StudentLearningSignal.knowledge_point_id.in_(point_ids))

    stats: dict[int, dict[str, float | int]] = {}
    for point_id, count, qa_count, score in db.execute(statement):
        if point_id is None:
            continue
        stats[int(point_id)] = {
            "learning_signal_count": int(count or 0),
            "qa_signal_count": int(qa_count or 0),
            "signal_score": round(float(score or 0), 2),
        }
    return stats
