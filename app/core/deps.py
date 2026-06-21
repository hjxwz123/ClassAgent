from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from datetime import UTC, datetime, timedelta

from app.core.enums import UserRole, UserStatus
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise unauthorized() from exc
    user = db.get(User, int(payload["sub"]))
    if user is None or user.deleted_at is not None:
        raise unauthorized()
    token_version = int(payload.get("token_version") or payload.get("ver") or 0)
    if token_version != int(getattr(user, "token_version", 0) or 0):
        raise unauthorized()
    if user.status != UserStatus.ACTIVE.value:
        raise unauthorized("账号已被禁用")
    # last_seen_at 仅用于"最近活跃"展示，节流到最多每 5 分钟写一次：避免每个鉴权请求都对远程库
    # （走 SSH 隧道）做一次同步 COMMIT，单次往返延迟会叠加到每个请求（含问答热路径）上。
    now = datetime.now(UTC)
    last_seen = user.last_seen_at
    if last_seen is not None and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    if last_seen is None or now - last_seen > timedelta(minutes=5):
        user.last_seen_at = now
        db.add(user)
        db.commit()
    return user


def require_role(*roles: UserRole):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return dependency
