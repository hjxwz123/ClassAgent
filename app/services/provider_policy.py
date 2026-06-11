from __future__ import annotations


MODEL_PROVIDERS_BY_PURPOSE: dict[str, set[str]] = {
    "embedding": {"qwen", "openai", "custom"},
    "rerank": {"qwen", "custom"},
}
DEFAULT_MODEL_PROVIDERS = {"qwen", "deepseek", "openai", "azure", "custom"}

SERVICE_PROVIDERS_BY_TYPE: dict[str, set[str]] = {
    "oss": {"aliyun", "local"},
    "ocr": {"aliyun"},
    "doc_parser": {"aliyun"},
    "tts": {"aliyun"},
    "email": {"smtp"},
}


def is_supported_model_provider(provider: str, purpose: str) -> bool:
    allowed = MODEL_PROVIDERS_BY_PURPOSE.get(purpose, DEFAULT_MODEL_PROVIDERS)
    return provider in allowed


def is_supported_service_provider(provider: str, service_type: str) -> bool:
    return provider in SERVICE_PROVIDERS_BY_TYPE.get(service_type, set())
