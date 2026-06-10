from mimetypes import guess_type
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.errors import forbidden, not_found
from app.core.media import normalize_storage_path, verify_signed_media
from app.services.storage import storage_service


router = APIRouter()


@router.get("/files/{relative_path:path}", include_in_schema=False)
def get_signed_media_file(
    relative_path: str,
    exp: Annotated[int, Query()],
    sig: Annotated[str, Query(min_length=32, max_length=128)],
):
    path = normalize_storage_path(relative_path)
    if not verify_signed_media(path, exp, sig):
        raise forbidden("媒体链接无效或已过期")
    try:
        content = storage_service.read_bytes(path)
    except FileNotFoundError as exc:
        public_fallback_path = f"public/{path}"
        if path.startswith(("docmind_images/", "generated/audio/")):
            try:
                content = storage_service.read_bytes(public_fallback_path)
            except FileNotFoundError:
                raise not_found("文件不存在") from exc
        else:
            raise not_found("文件不存在") from exc
    media_type = guess_type(Path(path).name)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "private, max-age=300"})
