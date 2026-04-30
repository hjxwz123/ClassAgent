from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid_token") from exc


def mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def encrypt_secret(value: str) -> str:
    settings = get_settings()
    salt = sha256(settings.secret_key.encode("utf-8")).hexdigest()[:16]
    masked = "".join(chr(ord(char) ^ ord(salt[index % len(salt)])) for index, char in enumerate(value))
    return masked.encode("utf-8").hex()


def decrypt_secret(value: str) -> str:
    settings = get_settings()
    salt = sha256(settings.secret_key.encode("utf-8")).hexdigest()[:16]
    raw = bytes.fromhex(value).decode("utf-8")
    return "".join(chr(ord(char) ^ ord(salt[index % len(salt)])) for index, char in enumerate(raw))
