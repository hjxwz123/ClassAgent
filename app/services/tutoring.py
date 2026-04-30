from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ProblemSourceType, UserRole
from app.core.errors import forbidden, not_found
from app.db.models import CourseMembership, ProblemGuidance, ProblemRecord, User
from app.schemas.tutoring import ProblemTextRequest
from app.services.ai import ai_service
from app.services.ocr import ocr_service
from app.services.storage import storage_service


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用题目辅导")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内使用题目辅导")


def _populate_problem_analysis(problem: ProblemRecord, text: str) -> None:
    knowledge_points = ai_service.extract_knowledge_points(text)
    problem.corrected_text = text
    problem.knowledge_points = knowledge_points
    problem.common_mistakes = ai_service.generate_common_mistakes(knowledge_points)


def create_text_problem(db: Session, *, user: User, payload: ProblemTextRequest) -> ProblemRecord:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    problem = ProblemRecord(
        course_id=payload.course_id,
        user_id=user.id,
        source_type=ProblemSourceType.TEXT.value,
        raw_text=payload.text,
    )
    _populate_problem_analysis(problem, payload.text)
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def create_image_problem(db: Session, *, user: User, course_id: int, upload: UploadFile) -> ProblemRecord:
    _assert_student_course_access(db, course_id=course_id, user=user)
    relative_path, _ = storage_service.save_upload(upload, folder=f"problem_images/course_{course_id}")
    ocr_text = ocr_service.recognize(upload)
    problem = ProblemRecord(
        course_id=course_id,
        user_id=user.id,
        source_type=ProblemSourceType.IMAGE.value,
        image_path=storage_service.public_url(relative_path),
        ocr_text=ocr_text,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def confirm_problem_text(db: Session, *, problem_id: int, user: User, corrected_text: str) -> ProblemRecord:
    problem = db.scalar(select(ProblemRecord).where(ProblemRecord.id == problem_id, ProblemRecord.user_id == user.id))
    if problem is None:
        raise not_found("题目记录不存在")
    _populate_problem_analysis(problem, corrected_text)
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def get_problem_guidance(db: Session, *, problem_id: int, user: User, level: int) -> ProblemGuidance:
    problem = db.scalar(select(ProblemRecord).where(ProblemRecord.id == problem_id, ProblemRecord.user_id == user.id))
    if problem is None:
        raise not_found("题目记录不存在")
    guidance = db.scalar(
        select(ProblemGuidance).where(ProblemGuidance.problem_id == problem_id, ProblemGuidance.level == level)
    )
    if guidance is not None:
        return guidance
    source_text = problem.corrected_text or problem.ocr_text or problem.raw_text or ""
    guidance = ProblemGuidance(
        problem_id=problem_id,
        level=level,
        content=ai_service.generate_problem_guidance(problem_text=source_text, level=level),
        similar_questions=ai_service.generate_similar_questions(problem.knowledge_points or []),
    )
    db.add(guidance)
    db.commit()
    db.refresh(guidance)
    return guidance


def list_problem_history(db: Session, *, user: User, course_id: int | None = None) -> list[ProblemRecord]:
    statement = select(ProblemRecord).where(ProblemRecord.user_id == user.id)
    if course_id is not None:
        statement = statement.where(ProblemRecord.course_id == course_id)
    return list(db.scalars(statement.order_by(ProblemRecord.created_at.desc())))
