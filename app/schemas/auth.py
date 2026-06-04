from pydantic import BaseModel, EmailStr, Field

from app.core.enums import UserRole
from app.schemas.common import UserSummary


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


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class RegisterLinkRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=8, max_length=64)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class AuthLinkResponse(BaseModel):
    email: EmailStr
    expires_in_seconds: int
