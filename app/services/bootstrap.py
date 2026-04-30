from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.db.models import User


def ensure_default_admin(db: Session) -> None:
    settings = get_settings()
    admin = db.scalar(select(User).where(User.email == settings.admin_default_email))
    if admin is not None:
        return
    admin = User(
        email=settings.admin_default_email,
        password_hash=hash_password(settings.admin_default_password),
        nickname=settings.admin_default_name,
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    db.add(admin)
    db.commit()
