from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimitRule, limit_request
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.tutoring import ProblemConfirmRequest, ProblemGuidanceResponse, ProblemResponse, ProblemTextRequest
from app.services.tutoring import confirm_problem_text, create_image_problem, create_text_problem, get_problem_guidance, list_problem_history


router = APIRouter()
TUTORING_RULE = RateLimitRule(limit=60, window_seconds=300)
TUTORING_UPLOAD_RULE = RateLimitRule(limit=30, window_seconds=300)
TUTORING_GUIDANCE_RULE = RateLimitRule(limit=60, window_seconds=300)


@router.post("/problems/text")
def create_text_problem_endpoint(
    payload: ProblemTextRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "tutoring-text", user.id, payload.course_id, rule=TUTORING_RULE)
    problem = create_text_problem(db, user=user, payload=payload)
    return success_response(data=ProblemResponse.model_validate(problem).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/problems/image")
def create_image_problem_endpoint(
    request: Request,
    course_id: Annotated[int, Form(...)],
    file: UploadFile = File(...),
    user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    limit_request(request, "tutoring-image", user.id, course_id, rule=TUTORING_UPLOAD_RULE)
    problem = create_image_problem(db, user=user, course_id=course_id, upload=file)
    return success_response(data=ProblemResponse.model_validate(problem).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/problems/{problem_id}/confirm")
def confirm_problem_endpoint(
    problem_id: int,
    payload: ProblemConfirmRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "tutoring-guidance-ip", rule=TUTORING_GUIDANCE_RULE)
    problem = confirm_problem_text(db, problem_id=problem_id, user=user, corrected_text=payload.corrected_text)
    return success_response(data=ProblemResponse.model_validate(problem).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/problems/{problem_id}/guidance")
def get_guidance_endpoint(
    problem_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    level: int = Query(ge=1, le=3),
):
    limit_request(request, "tutoring-guidance-ip", rule=TUTORING_GUIDANCE_RULE)
    guidance = get_problem_guidance(db, problem_id=problem_id, user=user, level=level)
    return success_response(data=ProblemGuidanceResponse.model_validate(guidance).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/history")
def get_problem_history_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = None,
):
    items = [ProblemResponse.model_validate(item).model_dump(mode="json") for item in list_problem_history(db, user=user, course_id=course_id)]
    return success_response(data=items, request_id=request.state.request_id)
