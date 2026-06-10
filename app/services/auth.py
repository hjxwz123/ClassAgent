from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

from sqlalchemy import Select, desc, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.errors import bad_request, not_found, unauthorized
from app.core.security import create_access_token, hash_password, hash_token, verify_password
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


REGISTERABLE_ROLES = {UserRole.STUDENT.value}
LOGIN_FAILED_MESSAGE = "登录失败，请检查用户名或者密码"
AUTH_LINK_EXPIRES_IN_SECONDS = 600
AUTH_LINK_INVALID_MESSAGE = "链接无效或已过期"


def _ensure_unique_identity(db: Session, payload: RegisterRequest) -> None:
    conditions = [User.email == payload.email]
    if payload.student_no:
        conditions.append(User.student_no == payload.student_no)
    if payload.employee_no:
        conditions.append(User.employee_no == payload.employee_no)
    existing = db.scalar(select(User).where(or_(*conditions), User.deleted_at.is_(None)))
    if existing is not None:
        raise bad_request("邮箱、学号或工号已存在")


def _build_auth_link(*, mode: str, email: str, token: str) -> str:
    settings = get_settings()
    query = urlencode({"mode": mode, "email": email, "token": token})
    return f"{settings.public_base_url.rstrip('/')}/auth?{query}"


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
            code=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=AUTH_LINK_EXPIRES_IN_SECONDS),
        )
    )
    return token


def _latest_available_email_token(db: Session, *, email: str, purpose: str, token: str) -> EmailCode | None:
    token_digest = hash_token(token)
    statement: Select[tuple[EmailCode]] = (
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.code == token_digest,
            EmailCode.used_at.is_(None),
        )
        .order_by(desc(EmailCode.id))
    )
    return db.scalars(statement).first()


def _latest_pending_email_token(db: Session, *, email: str, purpose: str) -> EmailCode | None:
    statement: Select[tuple[EmailCode]] = (
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.used_at.is_(None),
        )
        .order_by(desc(EmailCode.id))
    )
    return db.scalars(statement).first()


def _record_email_token_failure(db: Session, *, email: str, purpose: str) -> None:
    record = _latest_pending_email_token(db, email=email, purpose=purpose)
    if record is None:
        return
    record.attempt_count = int(record.attempt_count or 0) + 1
    db.add(record)
    db.commit()


def _ensure_email_token_valid(record: EmailCode | None) -> EmailCode:
    if record is None:
        raise bad_request(AUTH_LINK_INVALID_MESSAGE)
    if record.attempt_count >= 5:
        raise bad_request(AUTH_LINK_INVALID_MESSAGE)
    expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise bad_request(AUTH_LINK_INVALID_MESSAGE)
    return record


def _consume_email_token(db: Session, *, email: str, purpose: str, token: str) -> EmailCode:
    record = _latest_available_email_token(db, email=email, purpose=purpose, token=token)
    if record is None:
        _record_email_token_failure(db, email=email, purpose=purpose)
    record = _ensure_email_token_valid(record)
    record.used_at = datetime.now(UTC)
    db.add(record)
    return record


def validate_auth_link(db: Session, *, email: str, mode: str, token: str) -> AuthLinkResponse:
    purpose = "register" if mode == "register" else "password_reset"
    record = _latest_available_email_token(db, email=email, purpose=purpose, token=token)
    if record is None:
        _record_email_token_failure(db, email=email, purpose=purpose)
    record = _ensure_email_token_valid(record)
    if purpose == "register":
        existing = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
        if existing is not None:
            raise bad_request(AUTH_LINK_INVALID_MESSAGE)
    else:
        user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
        if user is None:
            raise bad_request(AUTH_LINK_INVALID_MESSAGE)
    expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=UTC)
    expires_in = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
    return AuthLinkResponse(email=email, expires_in_seconds=expires_in)


def _generic_auth_link_response(email: str) -> AuthLinkResponse:
    return AuthLinkResponse(email=email, expires_in_seconds=AUTH_LINK_EXPIRES_IN_SECONDS)


def create_registration_link(db: Session, email: str) -> tuple[AuthLinkResponse, str | None]:
    existing = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if existing is not None:
        db.commit()
        return _generic_auth_link_response(email), None
    token = _create_email_token(db, email=email, purpose="register")
    link = _build_auth_link(mode="register", email=email, token=token)
    db.commit()
    return _generic_auth_link_response(email), link


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
    token = create_access_token(str(user.id), extra={"role": user.role, "token_version": user.token_version})
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
    user.token_version = int(user.token_version or 0) + 1
    db.add(user)
    log_operation(
        db,
        user_id=user.id,
        action="user.password.change",
        target_type="user",
        target_id=user.id,
    )
    db.commit()


def create_password_reset_link(db: Session, email: str) -> tuple[AuthLinkResponse, str | None]:
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is None:
        db.commit()
        return _generic_auth_link_response(email), None
    token = _create_email_token(db, email=email, purpose="password_reset")
    link = _build_auth_link(mode="reset", email=email, token=token)
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.request",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return _generic_auth_link_response(email), link


def reset_password(db: Session, payload: PasswordResetConfirmRequest) -> None:
    record = _consume_email_token(db, email=payload.email, purpose="password_reset", token=payload.token)
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if user is None:
        raise not_found("用户不存在")
    user.password_hash = hash_password(payload.new_password)
    user.token_version = int(user.token_version or 0) + 1
    db.add_all([user, record])
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.confirm",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
