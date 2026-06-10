import logging
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import PUBLIC_DIR, STORAGE_DIR, get_settings
from app.core.errors import bad_request
from app.services.runtime_config import RuntimeServiceConfig, get_enabled_service_config


OSS_REQUIRED_KEYS = ("access_key_id", "access_key_secret", "bucket")
OSS_STRING_KEYS = (
    "access_key_id",
    "access_key_secret",
    "bucket",
    "region",
    "signature_version",
    "public_base_url",
    "cdn_domain",
)

OSS_DELETE_LOCAL_AFTER_UPLOAD_PREFIXES = (
    "public/avatars/",
    "public/course_covers/",
    "public/qa_images/",
    "public/problem_images/",
    "public/generated/audio/",
    "public/docmind_images/",
)

LOGGER = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _oss_endpoint(self, config: dict) -> str:
        region = str(config.get("region") or "cn-hangzhou").strip()
        return f"https://oss-{region}.aliyuncs.com"

    def _relative_to_storage(self, path: Path) -> str:
        return path.relative_to(STORAGE_DIR).as_posix()

    def _static_url(self, relative_path: str) -> str:
        return f"/static/{relative_path.removeprefix('public/').lstrip('/')}"

    def _sanitize_relative_path(self, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise bad_request("存储路径不合法")
        normalized = path.as_posix().strip("/")
        if not normalized:
            raise bad_request("存储路径不能为空")
        return normalized

    def _upload_folder_path(self, folder: str, *, public: bool = False) -> Path:
        normalized = self._sanitize_relative_path(folder)
        base = PUBLIC_DIR if public else STORAGE_DIR / "uploads"
        return base / normalized

    def _is_loopback_url(self, value: str) -> bool:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return False
        return parsed.hostname in {"127.0.0.1", "localhost", "0.0.0.0", "::1"}

    def _local_public_url(self, relative_path: str) -> str:
        base_url = str(self.settings.public_base_url or "").rstrip("/")
        if not base_url or self._is_loopback_url(base_url):
            return self._static_url(relative_path)
        public_path = relative_path.removeprefix("public/").lstrip("/")
        return f"{base_url}/static/{public_path}"

    def local_public_url(self, relative_path: str) -> str:
        return self._local_public_url(relative_path)

    def normalize_public_url(self, value: str | None) -> str | None:
        if not value:
            return value
        private_static_prefixes = ("/static/uploads/", "/static/backups/", "/static/vectors/", "/static/runtime/")
        if value.startswith("/static/"):
            if value.startswith(private_static_prefixes):
                return None
            return value
        if not self._is_loopback_url(value):
            return value
        parsed = urlsplit(value)
        if not parsed.path.startswith("/static/"):
            return value
        if parsed.path.startswith(private_static_prefixes):
            return None
        return urlunsplit(("", "", parsed.path, parsed.query, parsed.fragment))

    def _clean_oss_config(self, config: dict) -> dict:
        cleaned = dict(config)
        for key in OSS_STRING_KEYS:
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        return cleaned

    def _missing_oss_fields(self, config: dict) -> list[str]:
        return [key for key in OSS_REQUIRED_KEYS if not config.get(key)]

    def _resolve_oss_config(self, db: Session | None) -> RuntimeServiceConfig | None:
        mode = self.settings.external_storage_mode
        if mode == "local":
            return None
        service = get_enabled_service_config(db, "oss")
        if service is None:
            if mode == "oss":
                raise bad_request("OSS 服务未配置，请先在管理员服务配置中启用阿里云 OSS")
            return None
        if service.provider != "aliyun":
            if mode == "oss":
                raise bad_request(f"当前启用的存储服务不是阿里云 OSS: {service.provider}")
            return None
        config = self._clean_oss_config(service.config)
        missing = self._missing_oss_fields(config)
        if missing:
            raise bad_request(f"OSS 配置缺少字段: {', '.join(missing)}")
        return RuntimeServiceConfig(
            id=service.id,
            service_type=service.service_type,
            provider=service.provider,
            name=service.name,
            config=config,
        )

    def _upload_to_oss(self, relative_path: str, content: bytes, service: RuntimeServiceConfig) -> None:
        try:
            import oss2
        except ImportError as exc:
            raise bad_request("缺少 oss2 依赖，无法上传 OSS") from exc

        config = self._clean_oss_config(service.config)
        missing = self._missing_oss_fields(config)
        if missing:
            raise bad_request(f"OSS 配置缺少字段: {', '.join(missing)}")
        region = config.get("region")
        endpoint = self._oss_endpoint(config)
        try:
            if region and config.get("signature_version", "v4") != "v1":
                auth = oss2.AuthV4(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"], region=region)
            else:
                auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"])
            bucket.put_object(relative_path, content)
        except Exception as exc:
            raise bad_request(f"OSS 上传失败: {exc}") from exc

    def _oss_public_url(self, relative_path: str, service: RuntimeServiceConfig) -> str:
        config = self._clean_oss_config(service.config)
        if config.get("public_base_url"):
            return f"{str(config['public_base_url']).rstrip('/')}/{relative_path}"
        if config.get("cdn_domain"):
            return f"{str(config['cdn_domain']).rstrip('/')}/{relative_path}"
        bucket = str(config.get("bucket", "")).strip()
        if not bucket:
            return self._local_public_url(relative_path)
        endpoint = self._oss_endpoint(config)
        endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
        return f"https://{bucket}.{endpoint}/{relative_path}"

    def _should_delete_local_after_oss_upload(self, relative_path: str) -> bool:
        normalized = relative_path.lstrip("/")
        return any(normalized.startswith(prefix) for prefix in OSS_DELETE_LOCAL_AFTER_UPLOAD_PREFIXES)

    def _delete_local_after_oss_upload(self, target_path: Path, relative_path: str) -> None:
        if not self._should_delete_local_after_oss_upload(relative_path):
            return
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            return
        current = target_path.parent
        while current != STORAGE_DIR and STORAGE_DIR in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def save_upload(
        self,
        upload: UploadFile,
        *,
        folder: str,
        db: Session | None = None,
        max_bytes: int | None = None,
        public: bool = False,
        suffix: str | None = None,
    ) -> tuple[str, int]:
        target_dir = self._upload_folder_path(folder, public=public)
        target_dir.mkdir(parents=True, exist_ok=True)
        file_suffix = suffix if suffix is not None else Path(upload.filename or "").suffix.lower()
        filename = f"{uuid4().hex}{file_suffix}"
        target_path = target_dir / filename
        content = upload.file.read(max_bytes + 1 if max_bytes else -1)
        upload.file.seek(0)
        if max_bytes is not None and len(content) > max_bytes:
            raise bad_request(f"文件大小不能超过 {max_bytes // 1024 // 1024}MB")
        return self._write_content(target_path, content, db=db)

    def save_upload_bytes(
        self,
        content: bytes,
        *,
        folder: str,
        suffix: str,
        db: Session | None = None,
        public: bool = False,
    ) -> tuple[str, int]:
        target_dir = self._upload_folder_path(folder, public=public)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{uuid4().hex}{suffix}"
        return self._write_content(target_path, content, db=db)

    def _write_content(self, target_path: Path, content: bytes, *, db: Session | None = None) -> tuple[str, int]:
        target_path.write_bytes(content)
        relative_path = self._relative_to_storage(target_path)
        oss_config = self._resolve_oss_config(db)
        if oss_config is not None:
            self._upload_to_oss(relative_path, content, oss_config)
            self._delete_local_after_oss_upload(target_path, relative_path)
        return relative_path, len(content)

    def save_bytes(self, content: bytes, *, folder: str, filename: str, db: Session | None = None, public: bool = False) -> str:
        normalized_folder = self._sanitize_relative_path(folder)
        target_dir = (PUBLIC_DIR if public else STORAGE_DIR) / normalized_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        if Path(filename).name != filename:
            raise bad_request("文件名不合法")
        target_path = target_dir / filename
        relative_path, _ = self._write_content(target_path, content, db=db)
        return relative_path

    def absolute_path(self, relative_path: str) -> Path:
        return STORAGE_DIR / relative_path

    def read_bytes(self, relative_path: str, db: Session | None = None) -> bytes:
        path = self.absolute_path(relative_path)
        if path.is_file():
            return path.read_bytes()

        oss_config = self._resolve_oss_config(db)
        if oss_config is None:
            raise FileNotFoundError(relative_path)
        if oss_config.provider != "aliyun":
            raise bad_request(f"当前启用的存储服务不是阿里云 OSS: {oss_config.provider}")

        try:
            import oss2
        except ImportError as exc:
            raise bad_request("缺少 oss2 依赖，无法读取 OSS 文件") from exc

        config = self._clean_oss_config(oss_config.config)
        missing = self._missing_oss_fields(config)
        if missing:
            raise bad_request(f"OSS 配置缺少字段: {', '.join(missing)}")
        region = config.get("region")
        endpoint = self._oss_endpoint(config)
        try:
            if region and config.get("signature_version", "v4") != "v1":
                auth = oss2.AuthV4(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"], region=region)
            else:
                auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
                bucket = oss2.Bucket(auth, endpoint, config["bucket"])
            result = bucket.get_object(relative_path)
            buffer = BytesIO()
            while True:
                chunk = result.read(1024 * 256)
                if not chunk:
                    break
                buffer.write(chunk)
            return buffer.getvalue()
        except Exception as exc:
            LOGGER.warning("OSS file read failed for %s", relative_path, exc_info=True)
            raise bad_request("资料文件读取失败，请稍后重试或联系管理员") from exc

    def public_url(self, relative_path: str, db: Session | None = None) -> str:
        normalized = relative_path.lstrip("/")
        if not normalized.startswith("public/"):
            return ""
        oss_config = self._resolve_oss_config(db)
        if oss_config is not None:
            return self._oss_public_url(relative_path, oss_config)
        return self._local_public_url(relative_path)


storage_service = StorageService()
