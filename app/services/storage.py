from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import STORAGE_DIR, get_settings
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


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _oss_endpoint(self, config: dict) -> str:
        region = str(config.get("region") or "cn-hangzhou").strip()
        return f"https://oss-{region}.aliyuncs.com"

    def _relative_to_storage(self, path: Path) -> str:
        return path.relative_to(STORAGE_DIR).as_posix()

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
            return f"{self.settings.public_base_url}/static/{relative_path}"
        endpoint = self._oss_endpoint(config)
        endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
        return f"https://{bucket}.{endpoint}/{relative_path}"

    def save_upload(self, upload: UploadFile, *, folder: str, db: Session | None = None) -> tuple[str, int]:
        target_dir = STORAGE_DIR / "uploads" / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(upload.filename or "").suffix.lower()
        filename = f"{uuid4().hex}{suffix}"
        target_path = target_dir / filename
        content = upload.file.read()
        upload.file.seek(0)
        target_path.write_bytes(content)
        relative_path = self._relative_to_storage(target_path)
        oss_config = self._resolve_oss_config(db)
        if oss_config is not None:
            self._upload_to_oss(relative_path, content, oss_config)
        return relative_path, len(content)

    def save_bytes(self, content: bytes, *, folder: str, filename: str, db: Session | None = None) -> str:
        target_dir = STORAGE_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(content)
        relative_path = self._relative_to_storage(target_path)
        oss_config = self._resolve_oss_config(db)
        if oss_config is not None:
            self._upload_to_oss(relative_path, content, oss_config)
        return relative_path

    def absolute_path(self, relative_path: str) -> Path:
        return STORAGE_DIR / relative_path

    def public_url(self, relative_path: str, db: Session | None = None) -> str:
        oss_config = self._resolve_oss_config(db)
        if oss_config is not None:
            return self._oss_public_url(relative_path, oss_config)
        return f"{self.settings.public_base_url}/static/{relative_path}"


storage_service = StorageService()
