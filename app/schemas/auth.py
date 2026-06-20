import unicodedata
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import UserRole
from app.schemas.common import UserSummary


def _validate_avatar_url(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    # 仅允许本站相对路径（以单个 "/" 开头，排除 "//host" 协议相对地址）
    # 或显式 https 图片地址；拒绝 javascript:/data:/file: 等危险协议。
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    parsed = urlparse(candidate)
    if parsed.scheme == "https" and parsed.netloc:
        return candidate
    raise ValueError("头像地址必须是本站相对路径或 https 图片地址")


def _sanitize_bio(value: str | None) -> str | None:
    if value is None:
        return None
    # 去除控制字符（保留常规换行/制表）后再做长度与空值判定。
    cleaned = "".join(
        char
        for char in value
        if char in ("\n", "\t") or unicodedata.category(char)[0] != "C"
    ).strip()
    return cleaned or None


class RegisterRequest(BaseModel):
    email: EmailStr
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=2, max_length=50)
    role: UserRole
    student_no: str | None = Field(default=None, max_length=64)
    employee_no: str | None = Field(default=None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, min_length=2, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)

    @field_validator("avatar_url")
    @classmethod
    def _check_avatar_url(cls, value: str | None) -> str | None:
        return _validate_avatar_url(value)

    @field_validator("bio")
    @classmethod
    def _check_bio(cls, value: str | None) -> str | None:
        return _sanitize_bio(value)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class RegisterLinkRequest(BaseModel):
    email: EmailStr


class AuthLinkValidateRequest(BaseModel):
    email: EmailStr
    token: str = Field(max_length=128)
    mode: Literal["register", "reset"]


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=8, max_length=64)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class PasswordChangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthLinkResponse(BaseModel):
    email: EmailStr
    expires_in_seconds: int
