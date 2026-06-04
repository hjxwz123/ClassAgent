from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

from sqlalchemy import Select, desc, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.errors import bad_request, not_found, unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import EmailCode, User
from app.schemas.auth import (
    AuthLinkResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from app.schemas.common import UserSummary
from app.services.audit import log_login, log_operation
from app.services.email import email_service


REGISTERABLE_ROLES = {UserRole.STUDENT.value}
LOGIN_FAILED_MESSAGE = "登录失败，请检查用户名或者密码"
AUTH_LINK_EXPIRES_IN_SECONDS = 600


def _ensure_unique_identity(db: Session, payload: RegisterRequest) -> None:
    conditions = [User.email == payload.email]
    if payload.student_no:
        conditions.append(User.student_no == payload.student_no)
    if payload.employee_no:
        conditions.append(User.employee_no == payload.employee_no)
    existing = db.scalar(select(User).where(or_(*conditions), User.deleted_at.is_(None)))
    if existing is not None:
        raise bad_request("邮箱、学号或工号已存在")


def _build_auth_link(*, mode: str, email: str, token: str, base_url: str | None = None) -> str:
    settings = get_settings()
    query = urlencode({"mode": mode, "email": email, "token": token})
    return f"{(base_url or settings.public_base_url).rstrip('/')}/auth?{query}"


def _expire_existing_email_tokens(db: Session, *, email: str, purpose: str) -> None:
    now = datetime.now(UTC)
    records = db.scalars(
        select(EmailCode).where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.used_at.is_(None),
        )
    )
    for record in records:
        record.used_at = now
        db.add(record)


def _create_email_token(db: Session, *, email: str, purpose: str) -> str:
    _expire_existing_email_tokens(db, email=email, purpose=purpose)
    token = token_urlsafe(32)
    db.add(
        EmailCode(
            email=email,
            purpose=purpose,
            code=token,
            expires_at=datetime.now(UTC) + timedelta(seconds=AUTH_LINK_EXPIRES_IN_SECONDS),
        )
    )
    return token


def _consume_email_token(db: Session, *, email: str, purpose: str, token: str) -> EmailCode:
    statement: Select[tuple[EmailCode]] = (
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.code == token,
            EmailCode.used_at.is_(None),
        )
        .order_by(desc(EmailCode.id))
    )
    record = db.scalars(statement).first()
    if record is None:
        raise bad_request("链接无效或已使用")
    expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise bad_request("链接已过期")
    record.used_at = datetime.now(UTC)
    db.add(record)
    return record


def create_registration_link(db: Session, email: str, *, base_url: str | None = None) -> AuthLinkResponse:
    existing = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if existing is not None:
        raise bad_request("该邮箱已注册")
    token = _create_email_token(db, email=email, purpose="register")
    link = _build_auth_link(mode="register", email=email, token=token, base_url=base_url)
    email_service.send_registration_link(db, to_email=email, link=link)
    db.commit()
    return AuthLinkResponse(email=email, expires_in_seconds=AUTH_LINK_EXPIRES_IN_SECONDS)


def register_user(db: Session, payload: RegisterRequest) -> User:
    if payload.role.value not in REGISTERABLE_ROLES:
        raise bad_request("当前角色不允许自助注册")
    if payload.role == UserRole.STUDENT and not payload.student_no:
        raise bad_request("学生注册必须提供学号")
    _ensure_unique_identity(db, payload)
    record = _consume_email_token(db, email=payload.email, purpose="register", token=payload.token)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        status=UserStatus.ACTIVE.value,
        nickname=payload.nickname,
        student_no=payload.student_no,
        employee_no=payload.employee_no,
    )
    db.add_all([user, record])
    db.commit()
    db.refresh(user)
    log_operation(
        db,
        user_id=user.id,
        action="user.register",
        target_type="user",
        target_id=user.id,
        detail={"role": user.role},
    )
    db.commit()
    return user


def authenticate_user(db: Session, payload: LoginRequest, *, login_ip: str | None, user_agent: str | None) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if user is None:
        raise unauthorized(LOGIN_FAILED_MESSAGE)
    if not verify_password(payload.password, user.password_hash):
        log_login(db, user_id=user.id, login_ip=login_ip, user_agent=user_agent, success=False)
        db.commit()
        raise unauthorized(LOGIN_FAILED_MESSAGE)
    if user.status != UserStatus.ACTIVE.value:
        log_login(db, user_id=user.id, login_ip=login_ip, user_agent=user_agent, success=False)
        db.commit()
        raise unauthorized(LOGIN_FAILED_MESSAGE)
    user.last_login_at = datetime.now(UTC)
    user.last_seen_at = user.last_login_at
    db.add(user)
    log_login(db, user_id=user.id, login_ip=login_ip, user_agent=user_agent, success=True)
    db.commit()
    token = create_access_token(str(user.id), extra={"role": user.role})
    return LoginResponse(access_token=token, user=UserSummary.model_validate(user))


def get_user_profile(user: User) -> UserSummary:
    return UserSummary.model_validate(user)


def update_profile(db: Session, user: User, payload: ProfileUpdateRequest) -> User:
    if payload.nickname is not None:
        user.nickname = payload.nickname
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url
    if payload.bio is not None:
        user.bio = payload.bio
    db.add(user)
    log_operation(
        db,
        user_id=user.id,
        action="user.profile.update",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise bad_request("旧密码错误")
    user.password_hash = hash_password(new_password)
    db.add(user)
    log_operation(
        db,
        user_id=user.id,
        action="user.password.change",
        target_type="user",
        target_id=user.id,
    )
    db.commit()


def create_password_reset_link(db: Session, email: str, *, base_url: str | None = None) -> AuthLinkResponse:
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is None:
        raise not_found("该邮箱未注册")
    token = _create_email_token(db, email=email, purpose="password_reset")
    link = _build_auth_link(mode="reset", email=email, token=token, base_url=base_url)
    email_service.send_password_reset_link(db, to_email=email, link=link)
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.request",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return AuthLinkResponse(email=email, expires_in_seconds=AUTH_LINK_EXPIRES_IN_SECONDS)


def reset_password(db: Session, payload: PasswordResetConfirmRequest) -> None:
    record = _consume_email_token(db, email=payload.email, purpose="password_reset", token=payload.token)
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if user is None:
        raise not_found("用户不存在")
    user.password_hash = hash_password(payload.new_password)
    db.add_all([user, record])
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.confirm",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
