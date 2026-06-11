"""读取管理端可调的 system_settings 运行时值。

数据库值优先（管理员在后台修改后即时生效），读取失败或键不存在时回退给定默认值。
带进程内短 TTL 缓存，避免问答等热路径每次请求都查表；管理端写入时主动失效。
"""

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SystemSetting

_CACHE_TTL_SECONDS = 15.0
_cache: dict[str, tuple[float, Any]] = {}


def invalidate_runtime_setting(key: str | None = None) -> None:
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)


def runtime_setting_value(db: Session, key: str, default: Any = None) -> Any:
    now = time.monotonic()
    cached = _cache.get(key)
    if cached is not None and cached[0] > now:
        value = cached[1]
        return default if value is None else value
    try:
        value = db.scalar(select(SystemSetting.setting_value).where(SystemSetting.setting_key == key))
    except Exception:
        return default
    _cache[key] = (now + _CACHE_TTL_SECONDS, value)
    return default if value is None else value


def runtime_setting_int(
    db: Session,
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = runtime_setting_value(db, key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = int(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def runtime_setting_float(
    db: Session,
    key: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = runtime_setting_value(db, key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value
