from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
RUNTIME_DIR = STORAGE_DIR / "runtime"
BACKUP_DIR = STORAGE_DIR / "backups"
UPLOAD_DIR = STORAGE_DIR / "uploads"
GENERATED_DIR = STORAGE_DIR / "generated"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "课程学习助手智能体后端"
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-this-secret-key-in-production", min_length=16)
    access_token_expire_minutes: int = 60 * 24
    database_url: str = f"sqlite:///{(STORAGE_DIR / 'app.db').as_posix()}"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = True
    public_base_url: str = "http://127.0.0.1:8000"
    default_upload_limit_mb: int = 50
    max_course_materials: int = 200
    script_max_length: int = 3000
    qa_context_turn_limit: int = 6
    quiz_default_question_count: int = 10
    tutoring_default_release_level: int = 1
    default_tts_voice: str = "xiaoyun"
    default_tts_rate: int = 0
    default_tts_volume: int = 50
    admin_default_email: str = "admin@classagent.local"
    admin_default_password: str = "Admin123456"
    admin_default_name: str = "系统管理员"

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def storage_dir(self) -> Path:
        return STORAGE_DIR


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
