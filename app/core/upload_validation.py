from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import shlex
import subprocess
import tempfile
import warnings
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import bad_request


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    suffix: str
    media_type: str
    size_bytes: int


IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
IMAGE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}

OOXML_EXTENSIONS = {
    ".pptx": "ppt/",
    ".docx": "word/",
}
MATERIAL_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


def _read_limited(upload: UploadFile, *, max_bytes: int, label: str) -> bytes:
    content = upload.file.read(max_bytes + 1)
    upload.file.seek(0)
    if not content:
        raise bad_request(f"{label}文件为空")
    if len(content) > max_bytes:
        raise bad_request(f"{label}大小不能超过 {max_bytes // 1024 // 1024}MB")
    return content


def _replace_upload_content(upload: UploadFile, content: bytes) -> None:
    upload.file.seek(0)
    upload.file.truncate(0)
    upload.file.write(content)
    upload.file.seek(0)


def _suffix(upload: UploadFile) -> str:
    return Path(upload.filename or "").suffix.lower()


def _is_webp(content: bytes) -> bool:
    return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"


def _assert_image_signature(content: bytes, suffix: str) -> None:
    if suffix == ".webp":
        if not _is_webp(content):
            raise bad_request("图片文件内容与扩展名不匹配")
        return
    signatures = IMAGE_SIGNATURES.get(suffix)
    if not signatures or not any(content.startswith(signature) for signature in signatures):
        raise bad_request("图片文件内容与扩展名不匹配")


def _command_args(command: str, file_path: str) -> list[str]:
    try:
        args = shlex.split(command)
    except ValueError as exc:
        raise bad_request("上传安全扫描命令配置不合法") from exc
    if not args:
        raise bad_request("上传安全扫描命令未配置")
    if any("{file}" in arg for arg in args):
        return [arg.replace("{file}", file_path) for arg in args]
    return [*args, file_path]


def _run_upload_command(*, content: bytes, command: str, timeout_seconds: int, label: str) -> None:
    with tempfile.NamedTemporaryFile(prefix="classagent-upload-", suffix=".scan") as temp_file:
        temp_file.write(content)
        temp_file.flush()
        args = _command_args(command, temp_file.name)
        try:
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise bad_request(f"{label}安全扫描超时") from exc
        except OSError as exc:
            raise bad_request(f"{label}安全扫描服务不可用") from exc
    if result.returncode != 0:
        raise bad_request(f"{label}未通过安全扫描")


def _scan_for_malware(content: bytes, *, label: str) -> None:
    settings = get_settings()
    if not settings.upload_av_scan_enabled:
        return
    command = settings.upload_av_scan_command.strip()
    if not command:
        raise bad_request("上传安全扫描命令未配置")
    _run_upload_command(
        content=content,
        command=command,
        timeout_seconds=settings.upload_av_scan_timeout_seconds,
        label=label,
    )


def _review_image_content(content: bytes, *, label: str) -> None:
    settings = get_settings()
    if not settings.upload_image_review_enabled:
        return
    command = settings.upload_image_review_command.strip()
    if not command:
        raise bad_request("图片内容审核命令未配置")
    _run_upload_command(
        content=content,
        command=command,
        timeout_seconds=settings.upload_image_review_timeout_seconds,
        label=f"{label}内容审核",
    )


def _assert_image_dimensions(width: int, height: int, *, label: str) -> None:
    settings = get_settings()
    if width <= 0 or height <= 0:
        raise bad_request(f"{label}尺寸无效")
    if width > settings.upload_image_max_width or height > settings.upload_image_max_height:
        raise bad_request(
            f"{label}尺寸不能超过 {settings.upload_image_max_width}x{settings.upload_image_max_height}"
        )
    if width * height > settings.upload_image_max_pixels:
        raise bad_request(f"{label}像素数量超过限制")


def _sanitize_image(content: bytes, suffix: str, *, label: str, max_bytes: int) -> bytes:
    settings = get_settings()
    expected_format = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }[suffix]
    Image.MAX_IMAGE_PIXELS = settings.upload_image_max_pixels
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format != expected_format:
                    raise bad_request("图片文件内容与扩展名不匹配")
                _assert_image_dimensions(image.width, image.height, label=label)
                image.load()
                normalized = ImageOps.exif_transpose(image)
                output = BytesIO()
                if expected_format == "JPEG":
                    normalized = normalized.convert("RGB")
                    normalized.save(output, format="JPEG", quality=88, optimize=True)
                elif expected_format == "PNG":
                    normalized.save(output, format="PNG", optimize=True)
                else:
                    if normalized.mode not in {"RGB", "RGBA"}:
                        normalized = normalized.convert("RGBA" if "A" in normalized.getbands() else "RGB")
                    normalized.save(output, format="WEBP", quality=88, method=6)
    except Image.DecompressionBombError as exc:
        raise bad_request(f"{label}像素数量超过限制") from exc
    except Image.DecompressionBombWarning as exc:
        raise bad_request(f"{label}像素数量超过限制") from exc
    except UnidentifiedImageError as exc:
        raise bad_request("图片文件内容无效") from exc
    except OSError as exc:
        raise bad_request("图片文件内容无效") from exc
    if not settings.upload_image_reencode_enabled:
        return content
    sanitized = output.getvalue()
    if len(sanitized) > max_bytes:
        raise bad_request(f"{label}大小不能超过 {max_bytes // 1024 // 1024}MB")
    return sanitized


def validate_image_upload(
    upload: UploadFile,
    *,
    max_bytes: int,
    label: str = "图片",
    allowed_suffixes: set[str] | None = None,
) -> ValidatedUpload:
    suffix = _suffix(upload)
    allowed = allowed_suffixes or set(IMAGE_MEDIA_TYPES)
    if suffix not in allowed or suffix not in IMAGE_MEDIA_TYPES:
        raise bad_request(f"{label}仅支持 JPG、PNG 或 WEBP 图片")
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type and content_type != IMAGE_MEDIA_TYPES[suffix]:
        raise bad_request(f"{label}类型与文件扩展名不匹配")
    content = _read_limited(upload, max_bytes=max_bytes, label=label)
    _assert_image_signature(content, suffix)
    _scan_for_malware(content, label=label)
    content = _sanitize_image(content, suffix, label=label, max_bytes=max_bytes)
    _review_image_content(content, label=label)
    _replace_upload_content(upload, content)
    return ValidatedUpload(
        content=content,
        suffix=".jpg" if suffix == ".jpeg" else suffix,
        media_type=IMAGE_MEDIA_TYPES[suffix],
        size_bytes=len(content),
    )


def _assert_ooxml(content: bytes, suffix: str) -> None:
    marker = OOXML_EXTENSIONS[suffix]
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
    except BadZipFile as exc:
        raise bad_request("Office 文档内容无效") from exc
    if "[Content_Types].xml" not in names or not any(name.startswith(marker) for name in names):
        raise bad_request("Office 文档类型与扩展名不匹配")


def _assert_text(content: bytes) -> None:
    if b"\x00" in content[:4096]:
        raise bad_request("文本资料内容无效")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise bad_request("文本资料必须使用 UTF-8 编码") from exc


def validate_material_upload(upload: UploadFile, *, max_bytes: int) -> ValidatedUpload:
    suffix = _suffix(upload)
    media_type = MATERIAL_MEDIA_TYPES.get(suffix)
    image_media_type = IMAGE_MEDIA_TYPES.get(suffix)
    if media_type is None and image_media_type is None:
        raise bad_request("仅支持 .pptx、.pdf、.docx、.txt、.md、.markdown 或 .png、.jpg、.jpeg、.webp 图片")
    # 修复 DEF-02：图片资料走图片校验/清洗链路（签名校验、像素与尺寸上限、重编码去 EXIF、可选内容审核）。
    if image_media_type is not None:
        content = _read_limited(upload, max_bytes=max_bytes, label="资料")
        _assert_image_signature(content, suffix)
        _review_image_content(content, label="资料")
        content = _sanitize_image(content, suffix, label="资料", max_bytes=max_bytes)
        _scan_for_malware(content, label="资料")
        _replace_upload_content(upload, content)
        return ValidatedUpload(content=content, suffix=suffix, media_type=image_media_type, size_bytes=len(content))
    content = _read_limited(upload, max_bytes=max_bytes, label="资料")
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise bad_request("PDF 文件内容无效")
    elif suffix in OOXML_EXTENSIONS:
        _assert_ooxml(content, suffix)
    elif suffix in {".txt", ".md", ".markdown"}:
        _assert_text(content)
    _scan_for_malware(content, label="资料")
    return ValidatedUpload(content=content, suffix=suffix, media_type=media_type, size_bytes=len(content))
