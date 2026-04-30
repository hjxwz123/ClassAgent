from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import STORAGE_DIR, get_settings


class LocalStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _relative_to_storage(self, path: Path) -> str:
        return path.relative_to(STORAGE_DIR).as_posix()

    def save_upload(self, upload: UploadFile, *, folder: str) -> tuple[str, int]:
        target_dir = STORAGE_DIR / "uploads" / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(upload.filename or "").suffix.lower()
        filename = f"{uuid4().hex}{suffix}"
        target_path = target_dir / filename
        content = upload.file.read()
        target_path.write_bytes(content)
        return self._relative_to_storage(target_path), len(content)

    def save_bytes(self, content: bytes, *, folder: str, filename: str) -> str:
        target_dir = STORAGE_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(content)
        return self._relative_to_storage(target_path)

    def absolute_path(self, relative_path: str) -> Path:
        return STORAGE_DIR / relative_path

    def public_url(self, relative_path: str) -> str:
        return f"{self.settings.public_base_url}/static/{relative_path}"


storage_service = LocalStorageService()
