from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import forbidden, not_found
from app.core.responses import success_response
from app.db.models import AsyncTaskLog, KnowledgePoint, Quiz, QuizAnswer, QuizQuestion, User
from app.db.session import get_db
from app.schemas.learning import (
    KnowledgePointResponse,
    LearningRecordResponse,
    AsyncTaskResponse,
    QuizEditRequest,
    QuizAttemptResponse,
    QuizDetailResponse,
    QuizGenerateRequest,
    QuizQuestionPayload,
    QuizResponse,
    QuizRetakeRequest,
    QuizSubmitRequest,
    StudyPlanCreateRequest,
    StudyPlanResponse,
    StudyPlanTaskResponse,
    TaskCheckinRequest,
    WeakQuizGenerateRequest,
    WeakPointResponse,
    WrongQuestionResponse,
)
from app.services.learning import (
    checkin_task,
    create_study_plan,
    delete_quiz,
    dismiss_generation_task,
    enqueue_quiz_generation,
    enqueue_teacher_weak_quiz,
    enqueue_wrong_book_practice,
    extract_reference_answer_value,
    get_knowledge_points,
    get_learning_records,
    get_plan_tasks,
    get_quiz_detail,
    get_student_quiz_attempt,
    get_teacher_quiz_attempts,
    get_weak_points,
    knowledge_point_name_map,
    list_my_generation_tasks,
    list_student_quiz_attempts,
    list_teacher_weak_quizzes,
    list_quizzes,
    list_study_plans,
    list_wrong_questions,
    publish_quiz,
    quiz_attempt_summary,
    quiz_question_count_map,
    regenerate_quiz_question,
    retake_quiz,
    submit_quiz,
    update_quiz_content,
    wrong_question_mastery,
    wrong_question_review_state,
)


router = APIRouter()


def _reference_answer(question: QuizQuestion):
    return extract_reference_answer_value(question.reference_answer)


def _attempt_detail(db: Session, attempt) -> dict:
    quiz = db.get(Quiz, attempt.quiz_id)
    rows = list(
        db.execute(
            select(QuizAnswer, QuizQuestion)
            .join(QuizQuestion, QuizQuestion.id == QuizAnswer.question_id)
            .where(QuizAnswer.attempt_id == attempt.id)
            .order_by(QuizQuestion.id.asc())
        )
    )
    point_names = knowledge_point_name_map(db, [question for _answer, question in rows])
    attempt_payload = QuizAttemptResponse.model_validate(attempt).model_dump(mode="json")
    answers = []
    for answer, question in rows:
        question_payload = QuizQuestionPayload.model_validate(question).model_dump(mode="json")
        question_payload["knowledge_point_name"] = point_names.get(question.knowledge_point_id)
        answers.append(
            {
                "id": answer.id,
                "question_id": question.id,
                "question": question_payload,
                "user_answer": answer.user_answer,
                "correct_answer": _reference_answer(question),
                "is_correct": answer.is_correct,
                "pending_review": bool(answer.pending_review),
                "score": answer.score,
                "feedback": answer.feedback,
            }
        )
    return {
        **attempt_payload,
        "attempt": attempt_payload,
        "quiz": QuizResponse.model_validate(quiz).model_dump(mode="json") if quiz else None,
        "answers": answers,
    }


def _generation_task_response(db: Session, task: AsyncTaskLog) -> dict:
    task_payload = AsyncTaskResponse.model_validate(task).model_dump(mode="json")
    if task.status == "ready" and task.target_id:
        quiz = db.get(Quiz, task.target_id)
        if quiz is not None:
            quiz_payload = QuizResponse.model_validate(quiz).model_dump(mode="json")
            quiz_payload["task_id"] = task.id
            quiz_payload["task_status"] = task.status
            quiz_payload["generation_task"] = task_payload
            return quiz_payload
    return {
        "task_id": task.id,
        "task_name": task.task_name,
        "target_type": task.target_type,
        "target_id": task.target_id,
        "status": task.status,
        "detail": task.detail,
        "created_at": task_payload["created_at"],
        "updated_at": task_payload["updated_at"],
    }


@router.get("/knowledge-points")
def get_knowledge_points_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    chapter_id: int | None = Query(default=None),
):
    items = [
        KnowledgePointResponse.model_validate(item).model_dump(mode="json")
        for item in get_knowledge_points(db, course_id=course_id, chapter_id=chapter_id, user=user)
    ]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/quizzes/generate")
def generate_quiz_endpoint(
    payload: QuizGenerateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = enqueue_quiz_generation(db, user=user, payload=payload)
    return success_response(data=_generation_task_response(db, task), request_id=request.state.request_id)


@router.get("/quizzes")
def list_quizzes_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quizzes = list_quizzes(db, course_id=course_id, user=user)
    count_map = quiz_question_count_map(db, [item.id for item in quizzes])
    items = []
    for item in quizzes:
        payload = QuizResponse.model_validate(item).model_dump(mode="json")
        payload["question_count"] = count_map.get(item.id, 0)
        if user.role == "student":
            attempts = [quiz_attempt_summary(db, attempt) for attempt in list_student_quiz_attempts(db, quiz_id=item.id, user=user)]
            payload["attempts"] = attempts
            payload["latest_attempt"] = attempts[0] if attempts else None
            payload["attempt_count"] = len(attempts)
            payload["has_attempted"] = bool(attempts)
        items.append(payload)
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/teacher/weak-quizzes")
def list_teacher_weak_quizzes_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=list_teacher_weak_quizzes(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.post("/teacher/weak-quizzes/generate")
def generate_teacher_weak_quiz_endpoint(
    payload: WeakQuizGenerateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = enqueue_teacher_weak_quiz(db, user=user, payload=payload)
    return success_response(data=_generation_task_response(db, task), request_id=request.state.request_id)


@router.get("/generation-tasks")
def list_generation_tasks_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # 供前端刷新/回访后重建"生成中/生成失败"占位卡，避免任务在后台跑却在界面上凭空消失。
    items = []
    for task in list_my_generation_tasks(db, user=user, course_id=course_id):
        detail = task.detail if isinstance(task.detail, dict) else {}
        payload = AsyncTaskResponse.model_validate(task).model_dump(mode="json")
        payload["task_id"] = task.id
        payload["title"] = str(detail.get("title") or "AI 出题")
        payload["kind"] = str(detail.get("kind") or "quiz")
        items.append(payload)
    return success_response(data=items, request_id=request.state.request_id)


@router.delete("/generation-tasks/{task_id}")
def dismiss_generation_task_endpoint(
    task_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    dismiss_generation_task(db, task_id=task_id, user=user)
    return success_response(data={"dismissed": True}, request_id=request.state.request_id)


@router.get("/generation-tasks/{task_id}")
def get_generation_task_endpoint(
    task_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = db.get(AsyncTaskLog, task_id)
    if task is None:
        raise not_found("生成任务不存在")
    detail = task.detail if isinstance(task.detail, dict) else {}
    if user.role != "admin" and int(detail.get("user_id") or 0) != user.id:
        raise forbidden("无权查看该生成任务")
    return success_response(data=_generation_task_response(db, task), request_id=request.state.request_id)


@router.get("/teacher/weak-quizzes/{quiz_id}/attempts")
def get_teacher_weak_quiz_attempts_endpoint(
    quiz_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_quiz_attempts(db, quiz_id=quiz_id, user=user), request_id=request.state.request_id)


@router.post("/quizzes/{quiz_id}/publish")
def publish_quiz_endpoint(
    quiz_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quiz = publish_quiz(db, quiz_id=quiz_id, user=user)
    return success_response(data=QuizResponse.model_validate(quiz).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/quizzes/{quiz_id}")
def get_quiz_detail_endpoint(
    quiz_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quiz, questions = get_quiz_detail(db, quiz_id=quiz_id, user=user)
    point_names = knowledge_point_name_map(db, questions)
    serialized_questions = []
    for item in questions:
        payload = QuizQuestionPayload.model_validate(item).model_dump(mode="json")
        payload["knowledge_point_name"] = point_names.get(item.knowledge_point_id)
        if user.role == "student":
            # #3：作答前对学生统一剥离正确答案与解析，避免提前泄露答案。
            payload["reference_answer"] = None
            payload["explanation"] = None
        serialized_questions.append(payload)
    payload = QuizDetailResponse(
        quiz=QuizResponse.model_validate(quiz),
        questions=[QuizQuestionPayload(**item) for item in serialized_questions],
    )
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/quizzes/{quiz_id}/questions/{question_id}/regenerate")
def regenerate_quiz_question_endpoint(
    quiz_id: int,
    question_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    question = regenerate_quiz_question(db, quiz_id=quiz_id, question_id=question_id, user=user)
    point_names = knowledge_point_name_map(db, [question])
    payload = QuizQuestionPayload.model_validate(question).model_dump(mode="json")
    payload["knowledge_point_name"] = point_names.get(question.knowledge_point_id)
    if user.role == "student":
        # 与 get_quiz_detail 学生分支同口径：单题"换一道"的响应也剥离答案/解析，避免作答前泄题。
        payload["reference_answer"] = None
        payload["explanation"] = None
    return success_response(data=payload, request_id=request.state.request_id)


@router.get("/quizzes/{quiz_id}/attempts")
def list_student_quiz_attempts_endpoint(
    quiz_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attempts = [quiz_attempt_summary(db, attempt) for attempt in list_student_quiz_attempts(db, quiz_id=quiz_id, user=user)]
    return success_response(data=attempts, request_id=request.state.request_id)


@router.get("/attempts/{attempt_id}")
def get_student_quiz_attempt_endpoint(
    attempt_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attempt = get_student_quiz_attempt(db, attempt_id=attempt_id, user=user)
    return success_response(data=_attempt_detail(db, attempt), request_id=request.state.request_id)


@router.put("/quizzes/{quiz_id}")
def update_quiz_endpoint(
    quiz_id: int,
    payload: QuizEditRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quiz, questions = update_quiz_content(db, quiz_id=quiz_id, user=user, payload=payload)
    response = QuizDetailResponse(
        quiz=QuizResponse.model_validate(quiz),
        questions=[QuizQuestionPayload.model_validate(item) for item in questions],
    )
    return success_response(data=response.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz_endpoint(
    quiz_id: int,
    payload: QuizSubmitRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attempt = submit_quiz(db, quiz_id=quiz_id, user=user, answers=payload.answers, duration_seconds=payload.duration_seconds)
    return success_response(data=_attempt_detail(db, attempt), request_id=request.state.request_id)


@router.delete("/quizzes/{quiz_id}")
def delete_quiz_endpoint(
    quiz_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    delete_quiz(db, quiz_id=quiz_id, user=user)
    return success_response(data={"deleted": True}, request_id=request.state.request_id)


@router.post("/quizzes/{quiz_id}/retake")
def retake_quiz_endpoint(
    quiz_id: int,
    payload: QuizRetakeRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quiz = retake_quiz(db, quiz_id=quiz_id, user=user, mode=payload.mode, attempt_id=payload.attempt_id)
    data = QuizResponse.model_validate(quiz).model_dump(mode="json")
    data["question_count"] = quiz_question_count_map(db, [quiz.id]).get(quiz.id, 0)
    return success_response(data=data, request_id=request.state.request_id)


@router.get("/wrong-questions")
def get_wrong_questions_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = []
    now = datetime.now(UTC)
    for wrong, question in list_wrong_questions(db, course_id=course_id, user=user):
        point = db.get(KnowledgePoint, wrong.knowledge_point_id) if wrong.knowledge_point_id else None
        review = wrong_question_review_state(wrong, now)
        items.append(
            WrongQuestionResponse(
                wrong_question_id=wrong.id,
                question=QuizQuestionPayload.model_validate(question),
                wrong_count=wrong.wrong_count,
                history_count=wrong.wrong_count,
                is_resolved=bool(wrong.is_resolved),
                correct_streak=int(wrong.correct_streak or 0),
                mastery=wrong_question_mastery(wrong),
                knowledge_point_id=wrong.knowledge_point_id,
                knowledge_point_name=point.name if point else None,
                last_attempt_id=wrong.last_attempt_id,
                resolved_at=wrong.resolved_at,
                last_wrong_at=wrong.last_wrong_at,
                last_correct_at=wrong.last_correct_at,
                next_review_at=review["next_review_at"],
                is_due=review["is_due"],
                review_stage=review["review_stage"],
                review_total=review["review_total"],
                created_at=wrong.created_at,
                updated_at=wrong.updated_at,
            ).model_dump(mode="json")
        )
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/wrong-questions/practice")
def generate_wrong_book_practice_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    wrong_question_id: int | None = None,
):
    # #64：可选 wrong_question_id 用于定向重练，确保该错题被纳入并排在首位。
    task = enqueue_wrong_book_practice(db, course_id=course_id, user=user, wrong_question_id=wrong_question_id)
    return success_response(data=_generation_task_response(db, task), request_id=request.state.request_id)


@router.get("/weak-points")
def get_weak_points_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [WeakPointResponse(**item).model_dump(mode="json") for item in get_weak_points(db, course_id=course_id, user=user)]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/plans")
def create_plan_endpoint(
    payload: StudyPlanCreateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    plan, tasks = create_study_plan(db, user=user, payload=payload)
    return success_response(
        data={
            "plan": StudyPlanResponse.model_validate(plan).model_dump(mode="json"),
            "tasks": [StudyPlanTaskResponse.model_validate(task).model_dump(mode="json") for task in tasks],
        },
        request_id=request.state.request_id,
    )


@router.get("/plans")
def list_plans_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = Query(default=None),
):
    items = [StudyPlanResponse.model_validate(item).model_dump(mode="json") for item in list_study_plans(db, user=user, course_id=course_id)]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/plans/{plan_id}/tasks")
def get_plan_tasks_endpoint(
    plan_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [StudyPlanTaskResponse.model_validate(item).model_dump(mode="json") for item in get_plan_tasks(db, plan_id=plan_id, user=user)]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/tasks/{task_id}/checkin")
def checkin_task_endpoint(
    task_id: int,
    payload: TaskCheckinRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    checkin = checkin_task(db, task_id=task_id, user=user, notes=payload.notes)
    already_checked_in = bool(getattr(checkin, "already_checked_in", False))
    return success_response(
        data={
            "id": checkin.id,
            "task_id": checkin.task_id,
            "checked_in_at": checkin.checked_in_at,
            "notes": checkin.notes,
            "already_checked_in": already_checked_in,
            "status": "already_checked_in" if already_checked_in else "checked_in",
        },
        request_id=request.state.request_id,
    )


@router.get("/records")
def get_learning_records_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    payload = LearningRecordResponse(**get_learning_records(db, course_id=course_id, user=user))
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)
