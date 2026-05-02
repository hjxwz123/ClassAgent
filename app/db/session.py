from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKUP_DIR, GENERATED_DIR, RUNTIME_DIR, STORAGE_DIR, UPLOAD_DIR, VECTOR_DIR, get_settings
from app.db.base import Base


for path in (STORAGE_DIR, RUNTIME_DIR, BACKUP_DIR, UPLOAD_DIR, GENERATED_DIR, VECTOR_DIR):
    path.mkdir(parents=True, exist_ok=True)


def _build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


settings = get_settings()
engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def reset_engine(database_url: str | None = None) -> None:
    global engine, SessionLocal

    target_database_url = database_url or get_settings().database_url
    engine.dispose()
    engine = _build_engine(target_database_url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_updates(engine)


def _ensure_schema_updates(target_engine: Engine) -> None:
    inspector = inspect(target_engine)
    if "qa_records" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("qa_records")}
    statements: list[str] = []
    if "thinking_process" not in columns:
        statements.append("ALTER TABLE qa_records ADD COLUMN thinking_process TEXT")
    if "attachments" not in columns:
        statements.append("ALTER TABLE qa_records ADD COLUMN attachments JSON")
    if not statements:
        return
    with target_engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def drop_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
