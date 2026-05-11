from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_enabled_service_config


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return _extract_text(json.loads(stripped))
            except json.JSONDecodeError:
                return stripped
        return stripped
    if isinstance(value, list):
        return "\n".join(item for item in (_extract_text(item) for item in value) if item)
    if isinstance(value, dict):
        preferred_keys = (
            "content",
            "text",
            "word",
            "words",
            "value",
            "line",
            "sentence",
            "prism_wordsInfo",
            "blocks",
            "paragraphs",
        )
        pieces: list[str] = []
        for key in preferred_keys:
            if key in value:
                text = _extract_text(value[key])
                if text:
                    pieces.append(text)
        if pieces:
            return "\n".join(dict.fromkeys(pieces))
        return "\n".join(item for item in (_extract_text(item) for item in value.values()) if item)
    return str(value)


class OCRService:
    default_endpoint = "ocr-api.cn-hangzhou.aliyuncs.com"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _recognize_aliyun(self, content: bytes, config: dict) -> str:
        required = ["access_key_id", "access_key_secret"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"OCR 配置缺少字段: {', '.join(missing)}")
        try:
            from alibabacloud_ocr_api20210707.client import Client as OCRClient
            from alibabacloud_ocr_api20210707 import models as ocr_models
            from alibabacloud_tea_openapi import models as openapi_models
            from alibabacloud_tea_util import models as util_models
        except ImportError as exc:
            raise RuntimeError("缺少阿里云 OCR SDK 依赖") from exc

        client = OCRClient(
            openapi_models.Config(
                access_key_id=config["access_key_id"],
                access_key_secret=config["access_key_secret"],
                endpoint=self.default_endpoint,
            )
        )
        request = ocr_models.RecognizeGeneralRequest(body=BytesIO(content))
        runtime = util_models.RuntimeOptions(
            connect_timeout=int(self.settings.external_service_timeout_seconds * 1000),
            read_timeout=int(self.settings.external_service_timeout_seconds * 1000),
        )
        response = client.recognize_general_with_options(request, runtime)
        body = response.body.to_map() if response.body else {}
        if body.get("Code") and str(body["Code"]).lower() not in {"ok", "success"}:
            raise bad_request(f"OCR 识别失败: {body.get('Message') or body.get('Code')}")
        text = _extract_text(body.get("Data") or body.get("data") or body)
        if not text:
            raise bad_request("OCR 未识别到文本")
        return text

    def recognize(self, upload: UploadFile, db: Session | None = None) -> str:
        service = get_enabled_service_config(db, "ocr")
        if service is None:
            raise bad_request("OCR 服务未配置，请先在管理员服务配置中启用 ocr")
        content = upload.file.read()
        upload.file.seek(0)
        if service.provider == "aliyun":
            return self._recognize_aliyun(content, service.config)
        raise bad_request(f"暂不支持的 OCR 服务提供方: {service.provider}")


ocr_service = OCRService()
