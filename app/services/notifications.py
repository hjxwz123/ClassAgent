from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserPreference


USER_NOTIFICATION_KEY = "user.notifications"


def _notification_time(value) -> float:
    raw = (value.get("time") or value.get("created_at")) if isinstance(value, dict) else None
    if isinstance(raw, datetime):
        normalized = raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
        return normalized.timestamp()
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            normalized = parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
            return normalized.timestamp()
        except ValueError:
            return 0
    return 0


def _get_notifications(db: Session, *, user_id: int) -> list[dict]:
    item = db.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == USER_NOTIFICATION_KEY,
        )
    )
    value = item.preference_value if item is not None else None
    return value if isinstance(value, list) else []


def _set_notifications(db: Session, *, user_id: int, notifications: list[dict]) -> None:
    item = db.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == USER_NOTIFICATION_KEY,
        )
    )
    if item is None:
        item = UserPreference(user_id=user_id, preference_key=USER_NOTIFICATION_KEY, preference_value=notifications)
    else:
        item.preference_value = notifications
    db.add(item)


def push_user_notification(
    db: Session,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    message: str = "",
    course_id: int | None = None,
    course_name: str | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    task_id: int | None = None,
) -> dict:
    now = datetime.now(UTC)
    notification = {
        "id": f"{int(now.timestamp() * 1000)}-{user_id}-{notification_type}-{resource_id or task_id or 0}",
        "type": notification_type,
        "title": title.strip()[:120] or "通知",
        "message": message.strip()[:500],
        "course_id": course_id,
        "course_name": course_name or "",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "task_id": task_id,
        "time": now.isoformat(),
        "unread": True,
    }
    existing = [item for item in _get_notifications(db, user_id=user_id) if isinstance(item, dict)]
    _set_notifications(db, user_id=user_id, notifications=[notification, *existing][:80])
    return notification


def list_user_notifications(db: Session, *, user_id: int, limit: int = 8) -> list[dict]:
    notifications = [item for item in _get_notifications(db, user_id=user_id) if isinstance(item, dict)]
    notifications.sort(key=_notification_time, reverse=True)
    return notifications[:limit]
