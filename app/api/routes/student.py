from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.services.student import (
    get_page_note,
    get_student_course_home,
    get_student_dashboard,
    get_student_notifications,
    get_student_profile,
    list_student_course_summaries,
    mark_student_notifications_read,
    preview_course_by_code,
    save_page_note,
    upload_student_avatar,
    update_student_notifications,
    update_student_profile,
)


router = APIRouter()


class PageNoteRequest(BaseModel):
    content: str = Field(default="", max_length=8000)


class StudentProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, min_length=2, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
    school: str | None = Field(default=None, max_length=120)


class StudentNoticeItem(BaseModel):
    key: str
    enabled: bool
    time: str | None = None


class StudentNoticeRequest(BaseModel):
    settings: list[StudentNoticeItem] = Field(min_length=1)


class NotificationReadRequest(BaseModel):
    ids: list[str] | None = Field(default=None, max_length=80)


@router.get("/dashboard")
def dashboard_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    refresh_recommendation: bool = Query(default=False),
):
    return success_response(
        data=get_student_dashboard(db, user, refresh_recommendation=refresh_recommendation),
        request_id=request.state.request_id,
    )


@router.get("/courses")
def courses_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=list_student_course_summaries(db, user), request_id=request.state.request_id)


@router.get("/courses/preview")
def course_preview_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_code: str = Query(min_length=5, max_length=12),
):
    return success_response(data=preview_course_by_code(db, course_code=course_code, user=user), request_id=request.state.request_id)


@router.get("/courses/{course_id}/home")
def course_home_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_student_course_home(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.get("/pages/{page_id}/note")
def get_note_endpoint(
    page_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_page_note(db, page_id=page_id, user=user), request_id=request.state.request_id)


@router.put("/pages/{page_id}/note")
def save_note_endpoint(
    page_id: int,
    payload: PageNoteRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=save_page_note(db, page_id=page_id, user=user, content=payload.content), request_id=request.state.request_id)


@router.get("/profile")
def profile_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_student_profile(db, user), request_id=request.state.request_id)


@router.patch("/profile")
def update_profile_endpoint(
    payload: StudentProfileUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(
        data=update_student_profile(
            db,
            user=user,
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
            bio=payload.bio,
            school=payload.school,
        ),
        request_id=request.state.request_id,
    )


@router.post("/profile/avatar")
def upload_profile_avatar_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    return success_response(data=upload_student_avatar(db, user=user, upload=file), request_id=request.state.request_id)


@router.get("/notifications")
def notifications_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_student_notifications(db, user), request_id=request.state.request_id)


@router.put("/notifications")
def update_notifications_endpoint(
    payload: StudentNoticeRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(
        data=update_student_notifications(db, user=user, settings=[item.model_dump() for item in payload.settings]),
        request_id=request.state.request_id,
    )


@router.post("/notifications/read")
def mark_notifications_read_endpoint(
    payload: NotificationReadRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(
        data=mark_student_notifications_read(db, user=user, notification_ids=payload.ids),
        request_id=request.state.request_id,
    )
