from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from app.services.auth import (
    authenticate_user,
    change_password,
    create_password_reset_code,
    get_user_profile,
    register_user,
    reset_password,
    update_profile,
)


router = APIRouter()


@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    user = register_user(db, payload)
    return success_response(data=get_user_profile(user).model_dump(), request_id=request.state.request_id)


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    result = authenticate_user(
        db,
        payload,
        login_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return success_response(data=result.model_dump(), request_id=request.state.request_id)


@router.post("/password/reset/request")
def password_reset_request(payload: PasswordResetRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    result = create_password_reset_code(db, payload.email)
    return success_response(data=result.model_dump(), request_id=request.state.request_id)


@router.post("/password/reset/confirm")
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    reset_password(db, payload)
    return success_response(message="密码已重置", request_id=request.state.request_id)


@router.get("/me")
def me(request: Request, user: Annotated[User, Depends(get_current_user)]):
    return success_response(data=get_user_profile(user).model_dump(), request_id=request.state.request_id)


@router.patch("/me")
def update_me(
    payload: ProfileUpdateRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    updated_user = update_profile(db, user, payload)
    return success_response(data=get_user_profile(updated_user).model_dump(), request_id=request.state.request_id)


@router.post("/me/password")
def change_me_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    change_password(db, user, payload.old_password, payload.new_password)
    return success_response(message="密码修改成功", request_id=request.state.request_id)
