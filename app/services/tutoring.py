from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ProblemSourceType, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.core.upload_validation import validate_image_upload
from app.db.models import Course, CourseMembership, KnowledgeChunk, ProblemGuidance, ProblemRecord, User
from app.schemas.tutoring import ProblemTextRequest
from app.services.ai import ai_service
from app.services.courses import _assert_course_available_for_student
from app.services.knowledge import search_course_knowledge
from app.services.ocr import ocr_service
from app.services.pedagogy import TUTORING_ARTIFACT_TYPES, artifact_contexts, search_pedagogy_artifacts
from app.services.storage import storage_service
from app.services.usage import log_ai_usage

_TUTORING_CONTEXT_LIMIT = 8
_TUTORING_GENERAL_NOTICE = "提示：以下辅导未在当前课程资料中检索到直接依据，属于通用解题说明，请结合老师要求和课程内容自行核对。"
_TUTORING_GENERAL_DISABLED_NOTICE = "当前课程资料中没有检索到可直接支撑这道题的内容，且本课程未开启“资料外也可回答”，请换一道与课程资料更相关的题，或联系老师开启该开关。"


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用题目辅导")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内使用题目辅导")
    _assert_course_available_for_student(db, course_id)


def _student_course_scope(db: Session, *, user: User, course_id: int | None) -> int | None:
    if course_id is not None:
        _assert_student_course_access(db, course_id=course_id, user=user)
        return course_id
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用题目辅导")
    course_ids = list(db.scalars(select(CourseMembership.course_id).where(CourseMembership.user_id == user.id).limit(2)))
    return course_ids[0] if len(course_ids) == 1 else None


def _course_allows_general_ai_answer(db: Session, *, course_id: int) -> bool:
    course = db.get(Course, course_id)
    return bool(course and getattr(course, "allow_general_ai_answer", False))


def _populate_problem_analysis(problem: ProblemRecord, text: str, db: Session) -> None:
    knowledge_points = ai_service.extract_knowledge_points(text, db=db)
    problem.corrected_text = text
    problem.knowledge_points = knowledge_points
    problem.common_mistakes = ai_service.generate_common_mistakes(knowledge_points, db=db)


def _chunk_context(chunk: KnowledgeChunk) -> str:
    title = chunk.title or "资料片段"
    content = " ".join(str(chunk.content or "").split()).strip()
    return f"资料片段：{title}\n{content[:1400]}".strip()


def _problem_guidance_contexts(db: Session, *, course_id: int, problem_text: str) -> list[str]:
    artifacts = search_pedagogy_artifacts(
        db,
        course_id=course_id,
        query=problem_text,
        types=TUTORING_ARTIFACT_TYPES,
        limit=6,
    )
    chunks = search_course_knowledge(
        db,
        course_id=course_id,
        query=problem_text,
        limit=_TUTORING_CONTEXT_LIMIT,
    )
    if not artifacts and not chunks:
        rewritten_query = ai_service.rewrite_retrieval_query(question=problem_text, db=db)
        if rewritten_query and rewritten_query.strip() != problem_text.strip():
            artifacts = search_pedagogy_artifacts(
                db,
                course_id=course_id,
                query=rewritten_query,
                types=TUTORING_ARTIFACT_TYPES,
                limit=6,
            )
            chunks = search_course_knowledge(
                db,
                course_id=course_id,
                query=rewritten_query,
                limit=_TUTORING_CONTEXT_LIMIT,
            )
    contexts: list[str] = []
    seen: set[str] = set()
    for text in artifact_contexts(artifacts, limit=1500):
        key = " ".join(text.split())
        if not key or key in seen:
            continue
        seen.add(key)
        contexts.append(text)
    for chunk in chunks:
        text = _chunk_context(chunk)
        key = " ".join(text.split())
        if not key or key in seen:
            continue
        seen.add(key)
        contexts.append(text)
    return contexts


def create_text_problem(db: Session, *, user: User, payload: ProblemTextRequest) -> ProblemRecord:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    problem = ProblemRecord(
        course_id=payload.course_id,
        user_id=user.id,
        source_type=ProblemSourceType.TEXT.value,
        raw_text=payload.text,
    )
    _populate_problem_analysis(problem, payload.text, db)
    db.add(problem)
    log_ai_usage(
        db,
        module="tutoring_analysis",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(payload.text),
        completion_chars=len("".join(problem.knowledge_points or [])),
    )
    db.commit()
    db.refresh(problem)
    return problem


def create_image_problem(db: Session, *, user: User, course_id: int, upload: UploadFile) -> ProblemRecord:
    _assert_student_course_access(db, course_id=course_id, user=user)
    validated = validate_image_upload(upload, max_bytes=10 * 1024 * 1024, label="题目图片")
    relative_path, _ = storage_service.save_upload_bytes(
        validated.content,
        folder=f"problem_images/course_{course_id}/user_{user.id}",
        suffix=validated.suffix,
        db=db,
    )
    ocr_text = ocr_service.recognize(upload, db=db)
    problem = ProblemRecord(
        course_id=course_id,
        user_id=user.id,
        source_type=ProblemSourceType.IMAGE.value,
        image_path=relative_path,
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
    _assert_student_course_access(db, course_id=problem.course_id, user=user)
    _populate_problem_analysis(problem, corrected_text, db)
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def get_problem_guidance(db: Session, *, problem_id: int, user: User, level: int) -> ProblemGuidance:
    problem = db.scalar(select(ProblemRecord).where(ProblemRecord.id == problem_id, ProblemRecord.user_id == user.id))
    if problem is None:
        raise not_found("题目记录不存在")
    _assert_student_course_access(db, course_id=problem.course_id, user=user)
    guidance = db.scalar(
        select(ProblemGuidance).where(ProblemGuidance.problem_id == problem_id, ProblemGuidance.level == level)
    )
    if guidance is not None:
        return guidance
    max_unlocked = db.scalar(
        select(func.max(ProblemGuidance.level)).where(ProblemGuidance.problem_id == problem_id)
    ) or 0
    if level > max_unlocked + 1:
        raise bad_request("请先完成前序层级的引导后再解锁更高层级")
    source_text = problem.corrected_text or problem.ocr_text or problem.raw_text or ""
    contexts = _problem_guidance_contexts(db, course_id=problem.course_id, problem_text=source_text)
    allow_general_ai_answer = _course_allows_general_ai_answer(db, course_id=problem.course_id)
    if contexts:
        content = ai_service.generate_problem_guidance(problem_text=source_text, level=level, contexts=contexts, db=db)
    elif allow_general_ai_answer:
        content = f"{_TUTORING_GENERAL_NOTICE}\n\n{ai_service.generate_problem_guidance(problem_text=source_text, level=level, contexts=[], db=db)}".strip()
    else:
        content = _TUTORING_GENERAL_DISABLED_NOTICE
    guidance = ProblemGuidance(
        problem_id=problem_id,
        level=level,
        content=content,
        similar_questions=ai_service.generate_similar_questions(problem.knowledge_points or [], db=db),
    )
    db.add(guidance)
    log_ai_usage(
        db,
        module="tutoring_guidance",
        user_id=user.id,
        course_id=problem.course_id,
        prompt_chars=len(source_text),
        completion_chars=len(guidance.content),
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_guidance = db.scalar(
            select(ProblemGuidance).where(ProblemGuidance.problem_id == problem_id, ProblemGuidance.level == level)
        )
        if existing_guidance is not None:
            return existing_guidance
        raise
    db.refresh(guidance)
    return guidance


def list_problem_history(db: Session, *, user: User, course_id: int | None = None) -> list[ProblemRecord]:
    scoped_course_id = _student_course_scope(db, user=user, course_id=course_id)
    if scoped_course_id is None:
        return []
    statement = select(ProblemRecord).where(ProblemRecord.user_id == user.id)
    statement = statement.where(ProblemRecord.course_id == scoped_course_id)
    return list(db.scalars(statement.order_by(ProblemRecord.created_at.desc())))
