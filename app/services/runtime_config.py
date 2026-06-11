from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.db.models import ModelConfig, ServiceConfig
from app.services.provider_policy import is_supported_model_provider, is_supported_service_provider


@dataclass(frozen=True)
class RuntimeModelConfig:
    id: int
    provider: str
    model_name: str
    purpose: str
    endpoint: str | None
    api_key: str | None
    extra_config: dict


@dataclass(frozen=True)
class RuntimeServiceConfig:
    id: int
    service_type: str
    provider: str
    name: str
    config: dict


def get_enabled_service_config(db: Session | None, service_type: str) -> RuntimeServiceConfig | None:
    if db is None:
        return None
    records = db.scalars(
        select(ServiceConfig)
        .where(
            ServiceConfig.service_type == service_type,
            ServiceConfig.is_enabled.is_(True),
            ServiceConfig.deleted_at.is_(None),
        )
        .order_by(ServiceConfig.updated_at.desc(), ServiceConfig.created_at.desc())
    )
    record = next((item for item in records if is_supported_service_provider(item.provider, item.service_type)), None)
    if record is None:
        return None
    return RuntimeServiceConfig(
        id=record.id,
        service_type=record.service_type,
        provider=record.provider,
        name=record.name,
        config=json.loads(decrypt_secret(record.config_encrypted)),
    )


def get_default_model_config(db: Session | None, purpose: str, *, fallback_to_general: bool = True) -> RuntimeModelConfig | None:
    if db is None:
        return None
    statement = (
        select(ModelConfig)
        .where(ModelConfig.purpose == purpose, ModelConfig.deleted_at.is_(None))
        .order_by(ModelConfig.is_default.desc(), ModelConfig.updated_at.desc(), ModelConfig.created_at.desc())
    )
    records = db.scalars(statement)
    record = next((item for item in records if is_supported_model_provider(item.provider, item.purpose)), None)
    if record is None and purpose != "general" and fallback_to_general:
        fallback_records = db.scalars(
            select(ModelConfig)
            .where(ModelConfig.purpose == "general", ModelConfig.deleted_at.is_(None))
            .order_by(ModelConfig.is_default.desc(), ModelConfig.updated_at.desc(), ModelConfig.created_at.desc())
        )
        record = next((item for item in fallback_records if is_supported_model_provider(item.provider, item.purpose)), None)
    if record is None:
        return None
    return RuntimeModelConfig(
        id=record.id,
        provider=record.provider,
        model_name=record.model_name,
        purpose=record.purpose,
        endpoint=record.endpoint,
        api_key=decrypt_secret(record.api_key_encrypted) if record.api_key_encrypted else None,
        extra_config=record.extra_config or {},
    )
