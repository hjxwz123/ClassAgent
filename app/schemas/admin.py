from pydantic import BaseModel, EmailStr, Field


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=2, max_length=50)


class AdminUserUpdateRequest(BaseModel):
    status: str | None = None
    role: str | None = None


class PasswordResetByAdminRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=64)


class CourseTakeoverRequest(BaseModel):
    teacher_id: int


class ModelConfigRequest(BaseModel):
    config_id: int | None = None
    provider: str
    model_name: str
    purpose: str
    endpoint: str | None = None
    api_key: str | None = None
    is_default: bool = False
    extra_config: dict | None = None


class ServiceConfigRequest(BaseModel):
    config_id: int | None = None
    service_type: str
    provider: str
    name: str
    config: dict
    is_enabled: bool = True


class SystemSettingUpdateRequest(BaseModel):
    value: dict | list | str | int | float | bool | None
