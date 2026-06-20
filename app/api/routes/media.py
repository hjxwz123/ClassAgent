from mimetypes import guess_type
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.errors import forbidden, not_found
from app.core.media import normalize_storage_path, verify_signed_media
from app.db.session import get_db
from app.services.storage import storage_service


router = APIRouter()


@router.get("/files/{relative_path:path}", include_in_schema=False)
def get_signed_media_file(
    relative_path: str,
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query(min_length=32, max_length=128)],
    # 媒体路由本身用 HMAC 签名鉴权；注入只读 session 仅用于让 read_bytes 在
    # OSS/多实例部署下能回源到 OSS（本地无此文件时），不破坏既有鉴权模型。
    db: Annotated[Session, Depends(get_db)] = None,
):
    path = normalize_storage_path(relative_path)
    if not verify_signed_media(path, exp, sig):
        raise forbidden("媒体链接无效或已过期")
    try:
        content = storage_service.read_bytes(path, db=db)
    except FileNotFoundError as exc:
        public_fallback_path = f"public/{path}"
        if path.startswith(("docmind_images/", "generated/audio/")):
            try:
                content = storage_service.read_bytes(public_fallback_path, db=db)
            except FileNotFoundError:
                raise not_found("文件不存在") from exc
        else:
            raise not_found("文件不存在") from exc
    media_type = guess_type(Path(path).name)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "private, max-age=300"})
