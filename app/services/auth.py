from datetime import UTC, datetime, timedelta
from random import randint

from sqlalchemy import Select, desc, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.errors import bad_request, not_found, unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import EmailCode, User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetCodeResponse,
    PasswordResetConfirmRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from app.schemas.common import UserSummary
from app.services.audit import log_login, log_operation


REGISTERABLE_ROLES = {UserRole.STUDENT.value, UserRole.TEACHER.value}


def _ensure_unique_identity(db: Session, payload: RegisterRequest) -> None:
    conditions = [User.email == payload.email]
    if payload.student_no:
        conditions.append(User.student_no == payload.student_no)
    if payload.employee_no:
        conditions.append(User.employee_no == payload.employee_no)
    existing = db.scalar(select(User).where(or_(*conditions), User.deleted_at.is_(None)))
    if existing is not None:
        raise bad_request("邮箱、学号或工号已存在")


def register_user(db: Session, payload: RegisterRequest) -> User:
    if payload.role.value not in REGISTERABLE_ROLES:
        raise bad_request("当前角色不允许自助注册")
    if payload.role == UserRole.STUDENT and not payload.student_no:
        raise bad_request("学生注册必须提供学号")
    if payload.role == UserRole.TEACHER and not payload.employee_no:
        raise bad_request("教师注册必须提供工号")
    _ensure_unique_identity(db, payload)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        status=UserStatus.ACTIVE.value,
        nickname=payload.nickname,
        student_no=payload.student_no,
        employee_no=payload.employee_no,
    )
    db.add(user)
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
    if user is None or not verify_password(payload.password, user.password_hash):
        raise unauthorized("账号或密码错误")
    if user.status != UserStatus.ACTIVE.value:
        raise unauthorized("账号已被禁用")
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


def create_password_reset_code(db: Session, email: str) -> PasswordResetCodeResponse:
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is None:
        raise not_found("该邮箱未注册")
    code = f"{randint(100000, 999999)}"
    record = EmailCode(
        email=email,
        purpose="password_reset",
        code=code,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    db.add(record)
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.request",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    settings = get_settings()
    return PasswordResetCodeResponse(
        email=email,
        expires_in_seconds=600,
        debug_code=code if settings.app_env != "production" else None,
    )


def reset_password(db: Session, payload: PasswordResetConfirmRequest) -> None:
    statement: Select[tuple[EmailCode]] = (
        select(EmailCode)
        .where(
            EmailCode.email == payload.email,
            EmailCode.purpose == "password_reset",
            EmailCode.code == payload.code,
            EmailCode.used_at.is_(None),
        )
        .order_by(desc(EmailCode.id))
    )
    record = db.scalars(statement).first()
    if record is None:
        raise bad_request("验证码错误")
    expires_at = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise bad_request("验证码已过期")
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if user is None:
        raise not_found("用户不存在")
    user.password_hash = hash_password(payload.new_password)
    record.used_at = datetime.now(UTC)
    db.add_all([user, record])
    log_operation(
        db,
        user_id=user.id,
        action="user.password.reset.confirm",
        target_type="user",
        target_id=user.id,
    )
    db.commit()
