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
VECTOR_DIR = STORAGE_DIR / "vectors"


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
    database_url: str = "mysql+pymysql://class_agent:class_agent_2026@127.0.0.1:3306/class_agent?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = True
    external_ai_mode: Literal["auto", "mock", "strict"] = "auto"
    external_storage_mode: Literal["auto", "local", "oss"] = "auto"
    external_service_timeout_seconds: float = 30.0
    public_base_url: str = "http://127.0.0.1:8000"
    vector_store_provider: Literal["chroma"] = "chroma"
    chroma_persist_dir: str = str(VECTOR_DIR / "chroma")
    embedding_dimension: int = 1536
    vector_query_limit: int = 8
    vector_max_distance: float = 0.9
    default_upload_limit_mb: int = 50
    max_course_materials: int = 200
    script_max_length: int = 3000
    qa_context_turn_limit: int = 6
    quiz_default_question_count: int = 10
    tutoring_default_release_level: int = 1
    default_tts_voice: str = "xiaoyun"
    default_tts_rate: int = 0
    default_tts_volume: int = 50
    admin_default_email: str = "admin@classagent.com"
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


def validate_production_settings(settings: Settings | None = None) -> None:
    current = settings or get_settings()
    if current.app_env != "production":
        return
    errors: list[str] = []
    if current.secret_key == "change-this-secret-key-in-production":
        errors.append("SECRET_KEY 不能使用默认值")
    if current.database_url.startswith("sqlite"):
        errors.append("DATABASE_URL 生产环境不能使用 SQLite")
    if current.celery_task_always_eager:
        errors.append("CELERY_TASK_ALWAYS_EAGER 生产环境必须为 false")
    if current.external_ai_mode == "mock":
        errors.append("EXTERNAL_AI_MODE 生产环境不能使用 mock")
    if not current.celery_broker_url.startswith("redis://") and not current.celery_broker_url.startswith("rediss://"):
        errors.append("CELERY_BROKER_URL 应配置为 Redis 地址")
    if errors:
        raise RuntimeError("生产配置不完整：" + "；".join(errors))
