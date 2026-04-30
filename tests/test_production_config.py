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
        secret_key="replace-with-a-long-random-secret",
        database_url="mysql+pymysql://class_agent:password@127.0.0.1:3306/class_agent?charset=utf8mb4",
        celery_task_always_eager=False,
    )

    validate_production_settings(settings)
