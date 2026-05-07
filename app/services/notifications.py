from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SystemSetting, UserPreference


USER_NOTIFICATION_KEY = "user.notifications"
USER_NOTIFICATION_READ_KEY = "user.notification_reads"


def _setting_value(db: Session, key: str):
    item = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == key))
    return item.setting_value if item is not None else None


def _as_enabled(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "启用", "是"}


def active_system_announcement(db: Session, *, role: str) -> dict | None:
    if not _as_enabled(_setting_value(db, "system.announcement_enabled")):
        return None
    scope = str(_setting_value(db, "system.announcement_scope") or "all").strip().lower()
    normalized_role = str(role or "").strip().lower()
    if scope not in {"all", normalized_role}:
        return None
    setting = db.scalar(select(SystemSetting).where(SystemSetting.setting_key == "system.announcement"))
    raw_message = setting.setting_value if setting is not None else ""
    message = str(raw_message or "").strip()
    if not message:
        return None
    updated_at = (setting.updated_at if setting is not None else None) or datetime.now(UTC)
    return {
        "id": f"system-announcement-{int(_notification_time({'time': updated_at}))}",
        "type": "system_announcement",
        "title": "系统公告",
        "message": message,
        "time": updated_at,
        "unread": True,
    }


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


def _get_read_ids(db: Session, *, user_id: int) -> set[str]:
    item = db.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == USER_NOTIFICATION_READ_KEY,
        )
    )
    value = item.preference_value if item is not None else None
    if not isinstance(value, list):
        return set()
    return {str(notification_id) for notification_id in value if str(notification_id).strip()}


def _set_read_ids(db: Session, *, user_id: int, read_ids: set[str]) -> None:
    item = db.scalar(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.preference_key == USER_NOTIFICATION_READ_KEY,
        )
    )
    value = sorted(read_ids)[-500:]
    if item is None:
        item = UserPreference(user_id=user_id, preference_key=USER_NOTIFICATION_READ_KEY, preference_value=value)
    else:
        item.preference_value = value
    db.add(item)


def apply_user_notification_reads(db: Session, *, user_id: int, notifications: list[dict]) -> list[dict]:
    read_ids = _get_read_ids(db, user_id=user_id)
    normalized: list[dict] = []
    for item in notifications:
        copied = dict(item)
        notification_id = str(copied.get("id") or "").strip()
        if notification_id and notification_id in read_ids:
            copied["unread"] = False
        normalized.append(copied)
    return normalized


def mark_user_notifications_read(db: Session, *, user_id: int, notification_ids: list[str] | None = None) -> set[str]:
    requested_ids = {str(notification_id).strip() for notification_id in (notification_ids or []) if str(notification_id).strip()}
    existing = [item for item in _get_notifications(db, user_id=user_id) if isinstance(item, dict)]
    if not requested_ids:
        requested_ids = {str(item.get("id") or "").strip() for item in existing if str(item.get("id") or "").strip()}
    for item in existing:
        if str(item.get("id") or "").strip() in requested_ids:
            item["unread"] = False
    if existing:
        _set_notifications(db, user_id=user_id, notifications=existing)
    read_ids = _get_read_ids(db, user_id=user_id)
    read_ids.update(requested_ids)
    _set_read_ids(db, user_id=user_id, read_ids=read_ids)
    return requested_ids


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
    return apply_user_notification_reads(db, user_id=user_id, notifications=notifications[:limit])
