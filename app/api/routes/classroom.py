from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.enums import LessonStatus
from app.core.rate_limit import RateLimitRule, limit_request
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.classroom import LearningProgressResponse, LessonDetailResponse, LessonResponse, ProgressUpdateRequest
from app.schemas.material import LessonPageResponse
from app.schemas.material import MaterialResponse
from app.services.classroom import get_learning_progress, get_lesson_detail, list_lessons, publish_lesson, update_learning_progress
from app.services.pedagogy import ensure_lesson_pedagogy_artifacts, page_activity_payload


router = APIRouter()

# 学习进度上报为客户端自报，无法在不引入服务端浏览/心跳埋点的前提下彻底防伪；
# 此处用 per-user 限流遏制刷学习时长（重复 added_seconds 累加 total_study_seconds）。
# 前端翻页进度上报已做防抖（快速翻页合并为一次），这里给较宽额度，避免正常快速翻页误触限流。
PROGRESS_UPDATE_RULE = RateLimitRule(limit=120, window_seconds=60)


@router.get("")
def list_lessons_endpoint(
    request: Request,
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [LessonResponse.model_validate(item).model_dump(mode="json") for item in list_lessons(db, course_id=course_id, user=user)]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/{lesson_id}")
def get_lesson_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lesson, pages, material = get_lesson_detail(db, lesson_id=lesson_id, user=user)
    activities_by_page = page_activity_payload(db, lesson_page_ids=[page.id for page in pages])
    if pages and not any(activities_by_page.values()):
        if ensure_lesson_pedagogy_artifacts(db, lesson=lesson, pages=pages):
            db.commit()
            activities_by_page = page_activity_payload(db, lesson_page_ids=[page.id for page in pages])
    page_payloads = []
    for page in pages:
        payload = LessonPageResponse.model_validate(page).model_dump(mode="json")
        payload["pedagogy"] = activities_by_page.get(page.id, [])
        page_payloads.append(payload)
    payload = LessonDetailResponse(
        lesson=LessonResponse.model_validate(lesson),
        material=MaterialResponse.model_validate(material) if material else None,
        pages=page_payloads,
    )
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/{lesson_id}/publish")
def publish_lesson_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lesson = publish_lesson(db, lesson_id=lesson_id, user=user, status=LessonStatus.PUBLISHED.value)
    return success_response(data=LessonResponse.model_validate(lesson).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/{lesson_id}/unpublish")
def unpublish_lesson_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lesson = publish_lesson(db, lesson_id=lesson_id, user=user, status=LessonStatus.READY.value)
    return success_response(data=LessonResponse.model_validate(lesson).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/{lesson_id}/progress")
def get_progress_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    progress = get_learning_progress(db, lesson_id=lesson_id, user=user)
    return success_response(
        data=LearningProgressResponse.model_validate(progress).model_dump(mode="json") if progress else None,
        request_id=request.state.request_id,
    )


@router.post("/{lesson_id}/progress")
def update_progress_endpoint(
    lesson_id: int,
    payload: ProgressUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "lesson-progress", user.id, rule=PROGRESS_UPDATE_RULE)
    progress = update_learning_progress(
        db,
        lesson_id=lesson_id,
        user=user,
        current_page=payload.current_page,
        added_seconds=payload.added_seconds,
    )
    return success_response(data=LearningProgressResponse.model_validate(progress).model_dump(mode="json"), request_id=request.state.request_id)
