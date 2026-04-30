from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKUP_DIR, GENERATED_DIR, RUNTIME_DIR, STORAGE_DIR, UPLOAD_DIR, get_settings
from app.db.base import Base


settings = get_settings()

for path in (STORAGE_DIR, RUNTIME_DIR, BACKUP_DIR, UPLOAD_DIR, GENERATED_DIR):
    path.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
