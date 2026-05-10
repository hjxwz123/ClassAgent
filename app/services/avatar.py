from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.db.models import User
from app.services.storage import storage_service


AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def upload_avatar_file(db: Session, *, user: User, upload: UploadFile) -> dict:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()
    content_type = (upload.content_type or "").lower().split(";", 1)[0]
    if suffix not in AVATAR_EXTENSIONS:
        raise bad_request("头像仅支持 JPG、PNG、WEBP 或 GIF 图片")
    if content_type and not content_type.startswith("image/"):
        raise bad_request("头像仅支持图片文件")

    content = upload.file.read(AVATAR_MAX_BYTES + 1)
    upload.file.seek(0)
    if len(content) > AVATAR_MAX_BYTES:
        raise bad_request("头像不能超过 5MB")

    storage_path, size_bytes = storage_service.save_upload(upload, folder=f"avatars/user_{user.id}", db=db)
    avatar_url = storage_service.public_url(storage_path, db=db)
    user.avatar_url = avatar_url
    db.add(user)
    return {"avatar_url": avatar_url, "size_bytes": size_bytes}
