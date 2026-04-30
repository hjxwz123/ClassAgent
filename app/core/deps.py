from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from datetime import UTC, datetime

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
    if user.status != UserStatus.ACTIVE.value:
        raise unauthorized("账号已被禁用")
    user.last_seen_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    return user


def require_role(*roles: UserRole):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return dependency
