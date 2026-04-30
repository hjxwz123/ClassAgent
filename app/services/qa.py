from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.enums import QAFeedback, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import CourseMembership, QAConversation, QARecord, User
from app.schemas.qa import QAAskRequest
from app.services.ai import ai_service
from app.services.knowledge import search_course_knowledge


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内提问")


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
    chunks = search_course_knowledge(
        db,
        course_id=payload.course_id,
        query=payload.question,
        chapter_id=payload.chapter_id,
        lesson_page_id=payload.lesson_page_id,
        limit=4,
    )
    answer, out_of_scope = ai_service.answer_question(
        question=payload.question,
        contexts=[chunk.content for chunk in chunks],
        history=[item.question for item in history[-3:]],
    )
    sources = [chunk.source_meta or {} for chunk in chunks]
    record = QARecord(
        conversation_id=conversation.id,
        course_id=payload.course_id,
        user_id=user.id,
        lesson_page_id=payload.lesson_page_id,
        question=payload.question,
        answer=answer,
        is_out_of_scope=out_of_scope,
        sources=sources,
        keywords=ai_service.extract_keywords(payload.question),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


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
