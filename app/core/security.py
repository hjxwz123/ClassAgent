import base64
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import bad_request


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


def hash_token(value: str) -> str:
    settings = get_settings()
    return sha256(f"{settings.secret_key}:{value}".encode("utf-8")).hexdigest()


def mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


# 模型密钥/服务配置按明文存储（项目决策：与 SECRET_KEY 解耦，
# 避免轮换 SECRET_KEY 导致存量配置失效；注意数据库及其备份从此包含明文密钥）。
# encrypt_secret/decrypt_secret 保留为统一读写入口：写入原样落库；
# 读取兼容两代历史密文（enc2: Fernet 格式、更早的 XOR+hex 格式），
# 跑过 `python -m app.tools.migrate_secrets` 后存量数据即全部为明文。
_ENCRYPTED_PREFIX = "enc2:"
_LEGACY_HEX_PATTERN = re.compile(r"(?:[0-9a-f]{2}){8,}")
_SECRET_DECRYPT_ERROR = (
    "已保存的密钥/配置无法解密：SECRET_KEY 与保存配置时使用的不一致。"
    "请先恢复原 SECRET_KEY 并执行 python -m app.tools.migrate_secrets 转为明文存储，"
    "或在管理后台重新保存模型与服务配置。"
)


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(sha256(get_settings().secret_key.encode("utf-8")).digest())
    return Fernet(key)


def _legacy_xor_decrypt(value: str) -> str:
    settings = get_settings()
    salt = sha256(settings.secret_key.encode("utf-8")).hexdigest()[:16]
    raw = bytes.fromhex(value).decode("utf-8")
    return "".join(chr(ord(char) ^ ord(salt[index % len(salt)])) for index, char in enumerate(raw))


def encrypt_secret(value: str) -> str:
    return value


def decrypt_secret(value: str) -> str:
    if value.startswith(_ENCRYPTED_PREFIX):
        try:
            return _fernet().decrypt(value[len(_ENCRYPTED_PREFIX) :].encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError) as exc:
            raise bad_request(_SECRET_DECRYPT_ERROR) from exc
    if _LEGACY_HEX_PATTERN.fullmatch(value):
        # 形如旧 XOR+hex 密文的值才尝试旧格式解码；解不开按明文返回
        #（明文密钥恰好是纯小写 hex 时可能误判，迁移脚本跑过后不再有此类存量行）
        try:
            return _legacy_xor_decrypt(value)
        except (ValueError, UnicodeDecodeError):
            return value
    return value
