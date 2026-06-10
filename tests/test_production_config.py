import pytest

from app.core.config import Settings, validate_production_settings


def test_production_settings_reject_sqlite() -> None:
    settings = Settings(
        app_env="production",
        secret_key="replace-with-a-long-random-secret",
        database_url="sqlite:///tmp/app.db",
        celery_task_always_eager=False,
    )

    with pytest.raises(RuntimeError, match="SQLite"):
        validate_production_settings(settings)


def test_production_settings_accept_mysql_and_async_celery() -> None:
    settings = Settings(
        app_env="production",
        secret_key="prod-secret-key-with-more-than-32-characters",
        database_url="mysql+pymysql://class_agent:DbSecret2026!@mysql:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
        public_base_url="https://classagent.school",
        admin_default_password="StrongAdminPassword123!",
        cors_allow_origins="https://classagent.school",
        openapi_enabled=False,
        upload_av_scan_enabled=True,
        upload_av_scan_command="clamdscan --no-summary {file}",
        upload_image_review_enabled=True,
        upload_image_review_command="/usr/local/bin/classagent-image-review {file}",
    )

    validate_production_settings(settings)


def test_production_settings_accept_strict_ai_mode() -> None:
    settings = Settings(
        app_env="production",
        secret_key="prod-secret-key-with-more-than-32-characters",
        database_url="mysql+pymysql://class_agent:DbSecret2026!@mysql:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
        external_ai_mode="strict",
        public_base_url="https://classagent.school",
        admin_default_password="StrongAdminPassword123!",
        cors_allow_origins="https://classagent.school",
        openapi_enabled=False,
        upload_av_scan_enabled=True,
        upload_av_scan_command="clamdscan --no-summary {file}",
        upload_image_review_enabled=True,
        upload_image_review_command="/usr/local/bin/classagent-image-review {file}",
    )

    validate_production_settings(settings)


def test_production_settings_reject_placeholder_public_base_url() -> None:
    settings = Settings(
        app_env="production",
        secret_key="prod-secret-key-with-more-than-32-characters",
        database_url="mysql+pymysql://class_agent:DbSecret2026!@mysql:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
        public_base_url="https://your-domain.example.com",
        admin_default_password="StrongAdminPassword123!",
        cors_allow_origins="https://classagent.school",
        openapi_enabled=False,
        upload_av_scan_enabled=True,
        upload_av_scan_command="clamdscan --no-summary {file}",
        upload_image_review_enabled=True,
        upload_image_review_command="/usr/local/bin/classagent-image-review {file}",
    )

    with pytest.raises(RuntimeError, match="示例域名"):
        validate_production_settings(settings)


def test_production_settings_require_upload_security_controls() -> None:
    settings = Settings(
        app_env="production",
        secret_key="prod-secret-key-with-more-than-32-characters",
        database_url="mysql+pymysql://class_agent:DbSecret2026!@mysql:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
        public_base_url="https://classagent.school",
        admin_default_password="StrongAdminPassword123!",
        cors_allow_origins="https://classagent.school",
        openapi_enabled=False,
    )

    with pytest.raises(RuntimeError, match="UPLOAD_AV_SCAN_ENABLED"):
        validate_production_settings(settings)


def test_production_settings_reject_uppercase_placeholders() -> None:
    settings = Settings(
        app_env="production",
        secret_key="REPLACE_WITH_32_PLUS_CHAR_RANDOM_SECRET",
        database_url="mysql+pymysql://class_agent:REPLACE_WITH_STRONG_DB_PASSWORD@mysql:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
        public_base_url="https://classagent.school",
        admin_default_password="REPLACE_WITH_STRONG_ADMIN_PASSWORD",
        cors_allow_origins="https://classagent.school",
        openapi_enabled=False,
        upload_av_scan_enabled=True,
        upload_av_scan_command="clamdscan --no-summary {file}",
        upload_image_review_enabled=True,
        upload_image_review_command="/usr/local/bin/classagent-image-review {file}",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(settings)
