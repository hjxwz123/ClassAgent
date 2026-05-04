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
    return create_engine(database_url, connect_args=connect_args, future=True, pool_pre_ping=True, pool_recycle=3600)


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
    table_names = inspector.get_table_names()
    statements: list[str] = []
    if "qa_records" in table_names:
        columns = {column["name"] for column in inspector.get_columns("qa_records")}
        if "thinking_process" not in columns:
            statements.append("ALTER TABLE qa_records ADD COLUMN thinking_process TEXT")
        if "attachments" not in columns:
            statements.append("ALTER TABLE qa_records ADD COLUMN attachments JSON")
    if "courses" in table_names:
        course_columns = {column["name"] for column in inspector.get_columns("courses")}
        if "cover_url" not in course_columns:
            statements.append("ALTER TABLE courses ADD COLUMN cover_url VARCHAR(500)")
        if "cover_color" not in course_columns:
            statements.append("ALTER TABLE courses ADD COLUMN cover_color VARCHAR(32)")
    if "wrong_questions" in table_names:
        wrong_columns = {column["name"] for column in inspector.get_columns("wrong_questions")}
        if "is_resolved" not in wrong_columns:
            statements.append("ALTER TABLE wrong_questions ADD COLUMN is_resolved BOOLEAN NOT NULL DEFAULT 0")
        if "resolved_at" not in wrong_columns:
            statements.append("ALTER TABLE wrong_questions ADD COLUMN resolved_at DATETIME")
        if "last_wrong_at" not in wrong_columns:
            statements.append("ALTER TABLE wrong_questions ADD COLUMN last_wrong_at DATETIME")
        if "last_correct_at" not in wrong_columns:
            statements.append("ALTER TABLE wrong_questions ADD COLUMN last_correct_at DATETIME")
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
