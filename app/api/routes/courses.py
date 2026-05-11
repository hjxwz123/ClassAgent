from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import UserSummary
from app.schemas.course import (
    ChapterCreateRequest,
    ChapterResponse,
    CourseCreateRequest,
    CourseDetailResponse,
    CourseMemberResponse,
    CourseResponse,
    CourseUpdateRequest,
    JoinCourseRequest,
)
from app.services.courses import (
    activate_course,
    create_chapter,
    create_course,
    deactivate_course,
    get_course_detail,
    join_course,
    leave_course,
    list_course_members,
    list_joined_courses,
    list_teaching_courses,
    upload_course_cover,
    update_course,
)


router = APIRouter()


@router.get("/teaching")
def get_teaching_courses(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [CourseResponse.model_validate(item).model_dump() for item in list_teaching_courses(db, user)]
    return success_response(data=items, request_id=request.state.request_id)


@router.get("/enrolled")
def get_enrolled_courses(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = [CourseResponse.model_validate(item).model_dump() for item in list_joined_courses(db, user)]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("")
def create_course_endpoint(
    payload: CourseCreateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = create_course(db, user, payload)
    return success_response(data=CourseResponse.model_validate(course).model_dump(), request_id=request.state.request_id)


@router.patch("/{course_id}")
def update_course_endpoint(
    course_id: int,
    payload: CourseUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = update_course(db, user, course_id, payload)
    return success_response(data=CourseResponse.model_validate(course).model_dump(), request_id=request.state.request_id)


@router.post("/{course_id}/cover")
def upload_course_cover_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    course = upload_course_cover(db, user, course_id, file)
    return success_response(data=CourseResponse.model_validate(course).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/join")
def join_course_endpoint(
    payload: JoinCourseRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = join_course(db, user, payload.course_code)
    return success_response(data=CourseResponse.model_validate(course).model_dump(), request_id=request.state.request_id)


@router.post("/{course_id}/leave")
def leave_course_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    leave_course(db, user, course_id)
    return success_response(message="已退出课程", request_id=request.state.request_id)


@router.get("/{course_id}")
def get_course_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course, teacher, chapters, student_count = get_course_detail(db, user, course_id)
    payload = CourseDetailResponse(
        course=CourseResponse.model_validate(course),
        teacher=UserSummary.model_validate(teacher),
        chapters=[ChapterResponse.model_validate(item) for item in chapters],
        student_count=student_count,
    )
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/{course_id}/chapters")
def create_chapter_endpoint(
    course_id: int,
    payload: ChapterCreateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    chapter = create_chapter(db, user, course_id, payload)
    return success_response(data=ChapterResponse.model_validate(chapter).model_dump(), request_id=request.state.request_id)


@router.get("/{course_id}/members")
def get_course_members_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    rows = list_course_members(db, user, course_id)
    items = [
        CourseMemberResponse(
            id=membership.id,
            user=UserSummary.model_validate(member),
            joined_at=membership.joined_at,
        ).model_dump(mode="json")
        for membership, member in rows
    ]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("/{course_id}/deactivate")
def deactivate_course_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = deactivate_course(db, user, course_id)
    return success_response(data=CourseResponse.model_validate(course).model_dump(), request_id=request.state.request_id)


@router.post("/{course_id}/activate")
def activate_course_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    course = activate_course(db, user, course_id)
    return success_response(data=CourseResponse.model_validate(course).model_dump(), request_id=request.state.request_id)
