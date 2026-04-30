from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.material import MaterialDetailResponse, MaterialResponse, MaterialUpdateRequest, ScriptUpdateRequest
from app.services.materials import (
    create_material,
    delete_material,
    dispatch_material_processing,
    get_material_detail,
    list_materials,
    regenerate_page_script,
    reprocess_material,
    update_material,
    update_page_script,
)


router = APIRouter()


@router.get("")
def list_materials_endpoint(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = Query(default=None),
    chapter_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    items = [
        MaterialResponse.model_validate(item).model_dump(mode="json")
        for item in list_materials(
            db,
            user=user,
            course_id=course_id,
            chapter_id=chapter_id,
            keyword=keyword,
            category=category,
        )
    ]
    return success_response(data=items, request_id=request.state.request_id)


@router.post("")
def upload_material_endpoint(
    request: Request,
    course_id: Annotated[int, Form(...)],
    title: Annotated[str, Form(...)],
    category: Annotated[str, Form(...)],
    chapter_id: Annotated[int | None, Form()] = None,
    file: UploadFile = File(...),
    user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    material = create_material(
        db,
        user=user,
        course_id=course_id,
        title=title,
        category=category,
        chapter_id=chapter_id,
        upload=file,
    )
    dispatch_material_processing(material.id)
    db.refresh(material)
    return success_response(data=MaterialResponse.model_validate(material).model_dump(mode="json"), request_id=request.state.request_id)


@router.get("/{material_id}")
def get_material_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    material, lesson, pages = get_material_detail(db, material_id, user)
    payload = MaterialDetailResponse(
        material=MaterialResponse.model_validate(material),
        lesson_id=lesson.id if lesson else None,
        lesson_status=lesson.status if lesson else None,
        lesson_page_count=lesson.page_count if lesson else 0,
        pages=[page for page in pages],
    )
    return success_response(data=payload.model_dump(mode="json"), request_id=request.state.request_id)


@router.patch("/{material_id}")
def update_material_endpoint(
    material_id: int,
    payload: MaterialUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    material = update_material(
        db,
        material_id=material_id,
        user=user,
        title=payload.title,
        category=payload.category,
        chapter_id=payload.chapter_id,
        chapter_id_provided="chapter_id" in payload.model_fields_set,
    )
    return success_response(data=MaterialResponse.model_validate(material).model_dump(mode="json"), request_id=request.state.request_id)


@router.delete("/{material_id}")
def delete_material_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    delete_material(db, material_id=material_id, user=user)
    return success_response(message="资料已删除", request_id=request.state.request_id)


@router.post("/{material_id}/reprocess")
def reprocess_material_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    material = reprocess_material(db, material_id=material_id, user=user)
    return success_response(data=MaterialResponse.model_validate(material).model_dump(mode="json"), request_id=request.state.request_id)


@router.patch("/pages/{page_id}/script")
def update_page_script_endpoint(
    page_id: int,
    payload: ScriptUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    page = update_page_script(db, page_id=page_id, user=user, script_text=payload.script_text)
    return success_response(data=page_to_dict(page), request_id=request.state.request_id)


@router.post("/pages/{page_id}/script/regenerate")
def regenerate_page_script_endpoint(
    page_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    page = regenerate_page_script(db, page_id=page_id, user=user)
    return success_response(data=page_to_dict(page), request_id=request.state.request_id)


def page_to_dict(page):
    from app.schemas.material import LessonPageResponse

    return LessonPageResponse.model_validate(page).model_dump(mode="json")
