from __future__ import annotations

from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from pathlib import Path
from time import time
from urllib.parse import quote

from app.core.config import get_settings


SIGNED_MEDIA_PREFIXES = (
    "generated/audio/",
    "uploads/qa_images/",
    "uploads/problem_images/",
    "docmind_images/",
)


def normalize_storage_path(value: str) -> str:
    normalized = value.split("?", 1)[0].strip().lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized.removeprefix("static/")
    if normalized.startswith("public/"):
        normalized = normalized.removeprefix("public/")
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("invalid_path")
    return path.as_posix()


def is_signed_media_path(value: str) -> bool:
    try:
        normalized = normalize_storage_path(value)
    except ValueError:
        return False
    return any(normalized.startswith(prefix) for prefix in SIGNED_MEDIA_PREFIXES)


def _media_signature(path: str, expires_at: int) -> str:
    settings = get_settings()
    message = f"{path}:{expires_at}".encode("utf-8")
    return hmac_new(settings.secret_key.encode("utf-8"), message, sha256).hexdigest()


def signed_media_url(relative_path: str, *, expires_seconds: int = 3600) -> str:
    path = normalize_storage_path(relative_path)
    expires_at = int(time()) + expires_seconds
    signature = _media_signature(path, expires_at)
    return f"{get_settings().api_v1_prefix}/media/files/{quote(path, safe='/')}?exp={expires_at}&sig={signature}"


def verify_signed_media(path: str, expires_at: int, signature: str) -> bool:
    if expires_at < int(time()):
        return False
    try:
        normalized = normalize_storage_path(path)
    except ValueError:
        return False
    if not is_signed_media_path(normalized):
        return False
    return compare_digest(_media_signature(normalized, expires_at), signature)
