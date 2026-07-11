from mimetypes import guess_type
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import not_found
from app.core.rate_limit import RateLimitRule, limit_request
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.material import LessonPageResponse, MaterialResponse, MaterialUpdateRequest, ScriptUpdateRequest
from app.services.materials import (
    create_material,
    delete_material,
    dispatch_material_processing,
    get_material_detail,
    get_material_for_preview,
    get_material_status,
    list_materials,
    regenerate_page_script,
    reprocess_material,
    update_material,
    update_page_script,
)
from app.services.storage import storage_service


router = APIRouter()
MATERIAL_UPLOAD_RULE = RateLimitRule(limit=20, window_seconds=300)
MATERIAL_PROCESS_RULE = RateLimitRule(limit=20, window_seconds=300)


def serialize_material(material) -> dict:
    payload = MaterialResponse.model_validate(material).model_dump(mode="json")
    payload["preview_url"] = storage_service.normalize_public_url(payload.get("preview_url"))
    return payload


def serialize_page(page) -> dict:
    payload = LessonPageResponse.model_validate(page).model_dump(mode="json")
    payload["audio_url"] = storage_service.normalize_public_url(payload.get("audio_url"))
    return payload


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
        serialize_material(item)
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
    limit_request(request, "material-upload", user.id, course_id, rule=MATERIAL_UPLOAD_RULE)
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
    return success_response(data=serialize_material(material), request_id=request.state.request_id)


@router.get("/{material_id}/status")
def get_material_status_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return success_response(data=get_material_status(db, material_id, user), request_id=request.state.request_id)


@router.get("/{material_id}")
def get_material_endpoint(
    material_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    material, lesson, pages = get_material_detail(db, material_id, user)
    payload = {
        "material": serialize_material(material),
        "lesson_id": lesson.id if lesson else None,
        "lesson_status": lesson.status if lesson else None,
        "lesson_page_count": lesson.page_count if lesson else 0,
        "pages": [serialize_page(page) for page in pages],
    }
    return success_response(data=payload, request_id=request.state.request_id)


@router.get("/{material_id}/content")
def get_material_content_endpoint(
    material_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    material = get_material_for_preview(db, material_id=material_id, user=user)
    try:
        content = storage_service.read_bytes(material.storage_path, db=db)
    except FileNotFoundError as exc:
        raise not_found("资料文件不存在") from exc
    media_type = guess_type(material.original_filename or material.storage_path)[0] or "application/octet-stream"
    filename = Path(material.original_filename or material.storage_path).name or f"material-{material.id}"
    fallback_name = f"material-{material.id}{Path(filename).suffix.lower()}"
    headers = {
        "Content-Disposition": f'''inline; filename="{fallback_name}"; filename*=UTF-8''{quote(filename)}''',
        "Cache-Control": "private, max-age=600",
    }
    return Response(content=content, media_type=media_type, headers=headers)


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
    return success_response(data=serialize_material(material), request_id=request.state.request_id)


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
    limit_request(request, "material-reprocess", user.id, material_id, rule=MATERIAL_PROCESS_RULE)
    material = reprocess_material(db, material_id=material_id, user=user)
    return success_response(data=serialize_material(material), request_id=request.state.request_id)


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
    return serialize_page(page)
