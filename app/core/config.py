from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
RUNTIME_DIR = STORAGE_DIR / "runtime"
BACKUP_DIR = STORAGE_DIR / "backups"
UPLOAD_DIR = STORAGE_DIR / "uploads"
PUBLIC_DIR = STORAGE_DIR / "public"
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
    cors_allow_origins: str = ""
    cors_allow_credentials: bool = False
    openapi_enabled: bool = True
    security_headers_enabled: bool = True
    upload_av_scan_enabled: bool = False
    upload_av_scan_command: str = ""
    upload_av_scan_timeout_seconds: int = Field(default=30, ge=1, le=300)
    upload_image_reencode_enabled: bool = True
    upload_image_max_pixels: int = Field(default=20_000_000, ge=1)
    upload_image_max_width: int = Field(default=8000, ge=1)
    upload_image_max_height: int = Field(default=8000, ge=1)
    upload_image_review_enabled: bool = False
    upload_image_review_command: str = ""
    upload_image_review_timeout_seconds: int = Field(default=30, ge=1, le=300)
    external_ai_mode: Literal["auto", "strict"] = "auto"
    external_storage_mode: Literal["auto", "local", "oss"] = "auto"
    external_service_timeout_seconds: float = 30.0
    material_processing_worker_count: int = 4
    doc_parser_max_concurrency: int = 2
    material_ai_max_concurrency: int = 6
    tts_max_concurrency: int = 1
    material_processing_stale_minutes: int = 10
    material_processing_watchdog_interval_seconds: int = 30
    public_base_url: str = "http://127.0.0.1:8000"
    vector_store_provider: Literal["chroma", "qdrant"] = "chroma"
    chroma_persist_dir: str = str(VECTOR_DIR / "chroma")
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "classagent"
    qdrant_timeout_seconds: float = 10.0
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
    def cors_origin_list(self) -> list[str]:
        return [item.strip().rstrip("/") for item in self.cors_allow_origins.split(",") if item.strip()]

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
    normalized_secret_key = current.secret_key.lower()
    forbidden_values = {
        "change-this-secret-key-in-production",
        "replace-with-a-long-random-secret",
        "replace_with_32_plus_char_random_secret",
        "replace-with-32-plus-char-random-secret",
    }
    if normalized_secret_key in forbidden_values or "replace" in normalized_secret_key or len(current.secret_key) < 32:
        errors.append("SECRET_KEY 必须使用至少 32 字符的随机值，不能使用默认值")
    if current.database_url.startswith("sqlite"):
        errors.append("DATABASE_URL 生产环境不能使用 SQLite")
    normalized_database_url = current.database_url.lower()
    if any(
        value in current.database_url
        for value in ("class_agent_2026", "root_password", "password@", "replace-password", "changeme", "change-me")
    ) or any(value in normalized_database_url for value in ("replace_with", "replace-with", "replace_password")):
        errors.append("DATABASE_URL 不能使用示例数据库密码")
    if current.celery_task_always_eager:
        errors.append("CELERY_TASK_ALWAYS_EAGER 生产环境必须为 false")
    if not current.celery_broker_url.startswith("redis://") and not current.celery_broker_url.startswith("rediss://"):
        errors.append("CELERY_BROKER_URL 应配置为 Redis 地址")
    public_base = urlsplit(current.public_base_url)
    if public_base.scheme != "https":
        errors.append("PUBLIC_BASE_URL 生产环境必须使用 HTTPS")
    if public_base.hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        errors.append("PUBLIC_BASE_URL 生产环境不能指向本机地址")
    public_base_hostname = public_base.hostname or ""
    if (
        public_base_hostname in {"example.com", "your-domain.example.com"}
        or public_base_hostname.endswith(".example.com")
        or ".example." in public_base_hostname
    ):
        errors.append("PUBLIC_BASE_URL 生产环境不能使用示例域名")
    normalized_admin_password = current.admin_default_password.lower()
    if normalized_admin_password in {
        "admin123456",
        "admin",
        "password",
        "class_agent_2026",
        "replace-admin-password",
        "replace_with_strong_admin_password",
        "changeme",
    } or "replace" in normalized_admin_password:
        errors.append("ADMIN_DEFAULT_PASSWORD 不能使用默认或弱口令")
    if not current.cors_origin_list:
        errors.append("CORS_ALLOW_ORIGINS 生产环境必须配置明确域名")
    if "*" in current.cors_origin_list:
        errors.append("CORS_ALLOW_ORIGINS 生产环境不能使用 *")
    if current.openapi_enabled:
        errors.append("OPENAPI_ENABLED 生产环境必须关闭")
    if not current.upload_av_scan_enabled or not current.upload_av_scan_command.strip():
        errors.append("UPLOAD_AV_SCAN_ENABLED 生产环境必须开启，并配置 UPLOAD_AV_SCAN_COMMAND")
    if not current.upload_image_reencode_enabled:
        errors.append("UPLOAD_IMAGE_REENCODE_ENABLED 生产环境必须开启")
    if not current.upload_image_review_enabled or not current.upload_image_review_command.strip():
        errors.append("UPLOAD_IMAGE_REVIEW_ENABLED 生产环境必须开启，并配置 UPLOAD_IMAGE_REVIEW_COMMAND")
    if errors:
        raise RuntimeError("生产配置不完整：" + "；".join(errors))
