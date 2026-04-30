from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import KnowledgePoint, QuizAnswer, QuizQuestion, User
from app.db.session import get_db
from app.schemas.learning import (
    KnowledgePointResponse,
    LearningRecordResponse,
    QuizAttemptResponse,
    QuizDetailResponse,
    QuizGenerateRequest,
    QuizQuestionPayload,
    QuizResponse,
    QuizSubmitRequest,
    StudyPlanCreateRequest,
    StudyPlanResponse,
    StudyPlanTaskResponse,
    TaskCheckinRequest,
    WeakPointResponse,
    WrongQuestionResponse,
)
from app.services.learning import (
    checkin_task,
    create_study_plan,
    generate_quiz,
    generate_wrong_book_practice,
    get_knowledge_points,
    get_learning_records,
    get_plan_tasks,
    get_quiz_detail,
    get_weak_points,
    list_quizzes,
    list_study_plans,
    list_wrong_questions,
    publish_quiz,
    submit_quiz,
)


router = APIRouter()


def _reference_answer(question: QuizQuestion):
    if isinstance(question.reference_answer, dict) and "value" in question.reference_answer:
        return question.reference_answer["value"]
    return question.reference_answer


def _attempt_detail(db: Session, attempt) -> dict:
    rows = list(
        db.execute(
            select(QuizAnswer, QuizQuestion)
            .join(QuizQuestion, QuizQuestion.id == QuizAnswer.question_id)
            .where(QuizAnswer.attempt_id == attempt.id)
            .order_by(QuizQuestion.id.asc())
        )
    )
    attempt_payload = QuizAttemptResponse.model_validate(attempt).model_dump(mode="json")
    return {
        **attempt_payload,
        "attempt": attempt_payload,
        "answers": [
            {
                "id": answer.id,
                "question_id": question.id,
                "question": QuizQuestionPayload.model_validate(question).model_dump(mode="json"),
                "user_answer": answer.user_answer,
                "correct_answer": _reference_answer(question),
                "is_correct": answer.is_correct,
                "score": answer.score,
                "feedback": answer.feedback,
            }
            for answer, question in rows
        ],
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
    quiz = generate_quiz(db, user=user, payload=payload)
    return success_response(data=QuizResponse.model_validate(quiz).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/quizzes")
def list_quizzes_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [QuizResponse.model_validate(item).model_dump(mode="json") for item in list_quizzes(db, course_id=course_id, user=user)]
    return success_response(data=items, request_id=request.state.request_id)


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
    serialized_questions = []
    for item in questions:
        payload = QuizQuestionPayload.model_validate(item).model_dump(mode="json")
        if user.role == "student":
            payload["reference_answer"] = None
        serialized_questions.append(payload)
    payload = QuizDetailResponse(
        quiz=QuizResponse.model_validate(quiz),
        questions=[QuizQuestionPayload(**item) for item in serialized_questions],
    )
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz_endpoint(
    quiz_id: int,
    payload: QuizSubmitRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    attempt = submit_quiz(db, quiz_id=quiz_id, user=user, answers=payload.answers)
    return success_response(data=_attempt_detail(db, attempt), request_id=request.state.request_id)


@router.get("/wrong-questions")
def get_wrong_questions_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = []
    for wrong, question in list_wrong_questions(db, course_id=course_id, user=user):
        point = db.get(KnowledgePoint, wrong.knowledge_point_id) if wrong.knowledge_point_id else None
        items.append(
            WrongQuestionResponse(
                wrong_question_id=wrong.id,
                question=QuizQuestionPayload.model_validate(question),
                wrong_count=wrong.wrong_count,
                knowledge_point_id=wrong.knowledge_point_id,
                knowledge_point_name=point.name if point else None,
            ).model_dump(mode="json")
        )
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/wrong-questions/practice")
def generate_wrong_book_practice_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    quiz = generate_wrong_book_practice(db, course_id=course_id, user=user)
    return success_response(data=QuizResponse.model_validate(quiz).model_dump(mode="json"), request_id=request.state.request_id)


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
    return success_response(data={"id": checkin.id, "task_id": checkin.task_id, "checked_in_at": checkin.checked_in_at, "notes": checkin.notes}, request_id=request.state.request_id)


@router.get("/records")
def get_learning_records_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    payload = LearningRecordResponse(**get_learning_records(db, course_id=course_id, user=user))
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)
