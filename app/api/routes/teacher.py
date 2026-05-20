from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.classroom import LessonResponse
from app.schemas.course import ChapterResponse
from app.services.teacher import (
    delete_teacher_course,
    delete_chapter,
    delete_lesson,
    duplicate_lesson,
    export_teacher_analysis_csv,
    export_teacher_students_csv,
    get_teacher_profile,
    get_teacher_analysis,
    get_teacher_course_home,
    get_teacher_course_lessons,
    get_teacher_dashboard,
    get_teacher_materials_summary,
    get_teacher_student_detail,
    get_teacher_students,
    list_teacher_course_summaries,
    mark_teacher_notifications_read,
    remind_student,
    remove_student,
    upload_teacher_avatar,
    update_chapter,
    update_lesson,
    update_teacher_notifications,
    update_teacher_profile,
)


router = APIRouter()


class ChapterUpdateRequest(BaseModel):
    title: str
    description: str | None = None
    order_index: int = 1


class LessonUpdateRequest(BaseModel):
    title: str | None = None
    chapter_id: int | None = None
    status: str | None = None


class TeacherProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, min_length=2, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
    organization: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)


class NotificationSettingItem(BaseModel):
    key: str
    enabled: bool


class NotificationSettingsRequest(BaseModel):
    settings: list[NotificationSettingItem] = Field(min_length=1)


class NotificationReadRequest(BaseModel):
    ids: list[str] | None = Field(default=None, max_length=80)


class StudentReminderRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=500)


@router.get("/dashboard")
def dashboard_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_dashboard(db, user), request_id=request.state.request_id)


@router.get("/courses")
def courses_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=list_teacher_course_summaries(db, user), request_id=request.state.request_id)


@router.get("/profile")
def profile_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_profile(db, user), request_id=request.state.request_id)


@router.patch("/profile")
def update_profile_endpoint(
    payload: TeacherProfileUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    data = update_teacher_profile(
        db,
        user=user,
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
        bio=payload.bio,
        organization=payload.organization,
        department=payload.department,
    )
    return success_response(data=data, request_id=request.state.request_id)


@router.post("/profile/avatar")
def upload_profile_avatar_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
):
    data = upload_teacher_avatar(db, user=user, upload=file)
    return success_response(data=data, request_id=request.state.request_id)


@router.put("/profile/notifications")
def update_notifications_endpoint(
    payload: NotificationSettingsRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    data = update_teacher_notifications(db, user=user, settings=[item.model_dump() for item in payload.settings])
    return success_response(data=data, request_id=request.state.request_id)


@router.post("/notifications/read")
def mark_notifications_read_endpoint(
    payload: NotificationReadRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    data = mark_teacher_notifications_read(db, user=user, notification_ids=payload.ids)
    return success_response(data=data, request_id=request.state.request_id)


@router.get("/courses/{course_id}/home")
def course_home_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_course_home(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.get("/courses/{course_id}/lessons")
def course_lessons_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_course_lessons(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.get("/courses/{course_id}/materials/summary")
def course_materials_summary_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_materials_summary(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.delete("/courses/{course_id}")
def delete_course_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    delete_teacher_course(db, course_id=course_id, user=user)
    return success_response(message="已删除", request_id=request.state.request_id)


@router.get("/courses/{course_id}/students")
def course_students_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_students(db, course_id=course_id, user=user), request_id=request.state.request_id)


@router.get("/courses/{course_id}/students/export")
def export_students_endpoint(
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    csv_text = export_teacher_students_csv(db, course_id=course_id, user=user)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="course-{course_id}-students.csv"'},
    )


@router.get("/courses/{course_id}/students/{student_id}")
def student_detail_endpoint(
    course_id: int,
    student_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_teacher_student_detail(db, course_id=course_id, student_id=student_id, user=user), request_id=request.state.request_id)


@router.post("/courses/{course_id}/students/{student_id}/remind")
def remind_student_endpoint(
    course_id: int,
    student_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: StudentReminderRequest | None = None,
):
    data = remind_student(
        db,
        course_id=course_id,
        student_id=student_id,
        user=user,
        title=payload.title if payload else None,
        message=payload.message if payload else None,
    )
    return success_response(data=data, request_id=request.state.request_id)


@router.delete("/courses/{course_id}/students/{student_id}")
def remove_student_endpoint(
    course_id: int,
    student_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    remove_student(db, course_id=course_id, student_id=student_id, user=user)
    return success_response(message="已移出", request_id=request.state.request_id)


@router.patch("/courses/{course_id}/chapters/{chapter_id}")
def update_chapter_endpoint(
    course_id: int,
    chapter_id: int,
    payload: ChapterUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    chapter = update_chapter(
        db,
        course_id=course_id,
        chapter_id=chapter_id,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
        user=user,
    )
    return success_response(data=ChapterResponse.model_validate(chapter).model_dump(), request_id=request.state.request_id)


@router.delete("/courses/{course_id}/chapters/{chapter_id}")
def delete_chapter_endpoint(
    course_id: int,
    chapter_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    delete_chapter(db, course_id=course_id, chapter_id=chapter_id, user=user)
    return success_response(message="已删除", request_id=request.state.request_id)


@router.get("/courses/{course_id}/analysis")
def analysis_endpoint(
    course_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    return success_response(data=get_teacher_analysis(db, course_id=course_id, user=user, days=days), request_id=request.state.request_id)


@router.get("/courses/{course_id}/analysis/export")
def export_analysis_endpoint(
    course_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    csv_text = export_teacher_analysis_csv(db, course_id=course_id, user=user, days=days)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="course-{course_id}-analysis.csv"'},
    )


@router.patch("/lessons/{lesson_id}")
def update_lesson_endpoint(
    lesson_id: int,
    payload: LessonUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lesson = update_lesson(db, lesson_id=lesson_id, user=user, title=payload.title, chapter_id=payload.chapter_id, status=payload.status)
    return success_response(data=LessonResponse.model_validate(lesson).model_dump(mode="json"), request_id=request.state.request_id)


@router.post("/lessons/{lesson_id}/duplicate")
def duplicate_lesson_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lesson = duplicate_lesson(db, lesson_id=lesson_id, user=user)
    return success_response(data=LessonResponse.model_validate(lesson).model_dump(mode="json"), request_id=request.state.request_id)


@router.delete("/lessons/{lesson_id}")
def delete_lesson_endpoint(
    lesson_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    delete_lesson(db, lesson_id=lesson_id, user=user)
    return success_response(message="已删除", request_id=request.state.request_id)
