from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimitRule, limit_key, limit_request
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    AuthLinkValidateRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterLinkRequest,
    RegisterRequest,
)
from app.services.email import email_service
from app.services.auth import (
    authenticate_user,
    change_password,
    create_password_reset_link,
    create_registration_link,
    get_user_profile,
    register_user,
    reset_password,
    update_profile,
    validate_auth_link,
)


router = APIRouter()


LOGIN_IP_RULE = RateLimitRule(limit=30, window_seconds=300)
LOGIN_ACCOUNT_RULE = RateLimitRule(limit=8, window_seconds=300)
EMAIL_IP_RULE = RateLimitRule(limit=20, window_seconds=3600)
EMAIL_ACCOUNT_RULE = RateLimitRule(limit=3, window_seconds=3600)


@router.post("/register/request")
def register_request(
    payload: RegisterLinkRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "auth-register-request-ip", rule=EMAIL_IP_RULE)
    limit_key("auth-register-request-email", payload.email, rule=EMAIL_ACCOUNT_RULE)
    response, link = create_registration_link(db, payload.email)
    if link:
        background_tasks.add_task(email_service.send_registration_link_background, to_email=payload.email, link=link)
    return success_response(data=response.model_dump(), message="如账号存在，将发送邮件", request_id=request.state.request_id)


@router.post("/link/validate")
def link_validate(payload: AuthLinkValidateRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    limit_request(request, "auth-link-validate-ip", rule=EMAIL_IP_RULE)
    limit_key("auth-link-validate-email", payload.email, rule=EMAIL_ACCOUNT_RULE)
    result = validate_auth_link(db, email=payload.email, mode=payload.mode, token=payload.token)
    return success_response(data=result.model_dump(), request_id=request.state.request_id)


@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    limit_request(request, "auth-register-ip", rule=EMAIL_IP_RULE)
    limit_key("auth-register-email", payload.email, rule=EMAIL_ACCOUNT_RULE)
    user = register_user(db, payload)
    return success_response(data=get_user_profile(user).model_dump(), request_id=request.state.request_id)


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Annotated[Session, Depends(get_db)]):
    limit_request(request, "auth-login-ip", rule=LOGIN_IP_RULE)
    limit_key("auth-login-account", payload.email, rule=LOGIN_ACCOUNT_RULE)
    result = authenticate_user(
        db,
        payload,
        login_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return success_response(data=result.model_dump(), request_id=request.state.request_id)


@router.post("/password/reset/request")
def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "auth-reset-request-ip", rule=EMAIL_IP_RULE)
    limit_key("auth-reset-request-email", payload.email, rule=EMAIL_ACCOUNT_RULE)
    response, link = create_password_reset_link(db, payload.email)
    if link:
        background_tasks.add_task(email_service.send_password_reset_link_background, to_email=payload.email, link=link)
    return success_response(data=response.model_dump(), message="如账号存在，将发送邮件", request_id=request.state.request_id)


@router.post("/password/reset/confirm")
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    limit_request(request, "auth-reset-confirm-ip", rule=EMAIL_IP_RULE)
    limit_key("auth-reset-confirm-email", payload.email, rule=EMAIL_ACCOUNT_RULE)
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
    result = change_password(db, user, payload.old_password, payload.new_password)
    return success_response(data=result.model_dump(), message="密码修改成功", request_id=request.state.request_id)
