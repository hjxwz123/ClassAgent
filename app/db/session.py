import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKUP_DIR, GENERATED_DIR, PUBLIC_DIR, RUNTIME_DIR, STORAGE_DIR, UPLOAD_DIR, VECTOR_DIR, get_settings
from app.db.base import Base


for path in (STORAGE_DIR, RUNTIME_DIR, BACKUP_DIR, UPLOAD_DIR, PUBLIC_DIR, GENERATED_DIR, VECTOR_DIR):
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
    from app.db.models import PedagogyArtifact

    inspector = inspect(target_engine)
    table_names = inspector.get_table_names()
    if "pedagogy_artifacts" not in table_names:
        PedagogyArtifact.__table__.create(bind=target_engine, checkfirst=True)
        inspector = inspect(target_engine)
        table_names = inspector.get_table_names()
    statements: list[str] = []
    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "token_version" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")
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
        if "allow_general_ai_answer" not in course_columns:
            statements.append("ALTER TABLE courses ADD COLUMN allow_general_ai_answer BOOLEAN NOT NULL DEFAULT 0")
    if "email_codes" in table_names and target_engine.dialect.name == "mysql":
        email_code_columns = {column["name"]: str(column["type"]).upper() for column in inspector.get_columns("email_codes")}
        code_type = email_code_columns.get("code", "")
        if code_type.startswith("VARCHAR") and "128" not in code_type:
            statements.append("ALTER TABLE email_codes MODIFY COLUMN code VARCHAR(128) NOT NULL")
    if "email_codes" in table_names:
        email_columns = {column["name"] for column in inspector.get_columns("email_codes")}
        if "attempt_count" not in email_columns:
            statements.append("ALTER TABLE email_codes ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
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
    if "quiz_answers" in table_names:
        # 待人工批改主观题标记：用于学情分析/正确率把 pending 与真正答错区分开。
        quiz_answer_columns = {column["name"] for column in inspector.get_columns("quiz_answers")}
        if "pending_review" not in quiz_answer_columns:
            statements.append("ALTER TABLE quiz_answers ADD COLUMN pending_review BOOLEAN NOT NULL DEFAULT 0")
    if target_engine.dialect.name == "mysql":
        _append_mysql_longtext_updates(inspector, table_names, statements)
    if "quiz_attempts" in table_names:
        # #14：为既有库补建 (quiz_id, user_id) 唯一约束，使并发重复提交时 IntegrityError 兜底生效。
        # 自我隔离、crash-safe：单独事务执行，失败（如生产已存在重复行）仅告警不抛出，保证启动不崩。
        existing_indexes = {index.get("name") for index in inspector.get_indexes("quiz_attempts")}
        if "uq_quiz_attempt_user" not in existing_indexes:
            try:
                with target_engine.begin() as connection:
                    connection.execute(
                        text("CREATE UNIQUE INDEX uq_quiz_attempt_user ON quiz_attempts (quiz_id, user_id)")
                    )
            except Exception as exc:  # noqa: BLE001 - 迁移失败不应阻断应用启动
                logging.warning("跳过创建 quiz_attempts 唯一索引 uq_quiz_attempt_user：%s", exc)
    if not statements:
        return
    with target_engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _append_mysql_longtext_updates(inspector, table_names: list[str], statements: list[str]) -> None:
    targets = {
        "course_materials": {
            "extracted_text": "LONGTEXT NULL",
        },
        "lessons": {
            "summary": "LONGTEXT NULL",
        },
        "lesson_pages": {
            "page_text": "LONGTEXT NOT NULL",
            "script_text": "LONGTEXT NULL",
            "subtitle_text": "LONGTEXT NULL",
        },
        "knowledge_chunks": {
            "content": "LONGTEXT NOT NULL",
        },
        "pedagogy_artifacts": {
            "summary": "LONGTEXT NULL",
            "content": "LONGTEXT NOT NULL",
        },
    }
    for table_name, columns in targets.items():
        if table_name not in table_names:
            continue
        existing_columns = {column["name"]: str(column["type"]).upper() for column in inspector.get_columns(table_name)}
        for column_name, definition in columns.items():
            column_type = existing_columns.get(column_name)
            if column_type is not None and "LONGTEXT" not in column_type:
                statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} {definition}")


def drop_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
