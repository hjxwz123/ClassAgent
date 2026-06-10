from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.upload_validation import validate_image_upload
from app.db.models import User
from app.services.storage import storage_service


AVATAR_MAX_BYTES = 5 * 1024 * 1024


def upload_avatar_file(db: Session, *, user: User, upload: UploadFile) -> dict:
    validated = validate_image_upload(upload, max_bytes=AVATAR_MAX_BYTES, label="头像")
    storage_path, size_bytes = storage_service.save_upload_bytes(
        validated.content,
        folder=f"avatars/user_{user.id}",
        suffix=validated.suffix,
        db=db,
        public=True,
    )
    avatar_url = storage_service.public_url(storage_path, db=db)
    user.avatar_url = avatar_url
    db.add(user)
    return {"avatar_url": avatar_url, "size_bytes": size_bytes}
