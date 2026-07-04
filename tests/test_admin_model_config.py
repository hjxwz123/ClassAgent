"""save_model_config 与密钥存储的回归测试。

覆盖三类历史问题：
1. 新建用途行时 API Key 留空被静默落库成无密钥（应继承同 endpoint 已存密钥）；
2. 同 purpose 多行 is_default 并存导致“改 A 生效 B”；
3. 密钥现按明文存储，但必须兼容读出两代历史密文（enc2: Fernet、XOR+hex）。
"""

import base64
from hashlib import sha256

import pytest
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import decrypt_secret, encrypt_secret
from app.db import session as db_session
from app.services.admin import delete_model_config, save_model_config
from app.services.runtime_config import get_default_model_config

ENDPOINT = "https://example.com/v1"


def _legacy_xor_encrypt(value: str) -> str:
    # 第一代 XOR+hex 格式（无完整性校验），用于验证存量数据兼容
    salt = sha256(get_settings().secret_key.encode("utf-8")).hexdigest()[:16]
    masked = "".join(chr(ord(char) ^ ord(salt[index % len(salt)])) for index, char in enumerate(value))
    return masked.encode("utf-8").hex()


def _fernet_encrypt(value: str) -> str:
    # 第二代 enc2: Fernet 格式，用于验证存量数据兼容
    key = base64.urlsafe_b64encode(sha256(get_settings().secret_key.encode("utf-8")).digest())
    return "enc2:" + Fernet(key).encrypt(value.encode("utf-8")).decode("ascii")


def test_secret_stored_as_plaintext_round_trip():
    plain = "sk-测试密钥-with-symbols-!@#"
    assert encrypt_secret(plain) == plain
    assert decrypt_secret(plain) == plain


def test_decrypt_secret_supports_legacy_xor_format():
    plain = "sk-legacy-key-001"
    assert decrypt_secret(_legacy_xor_encrypt(plain)) == plain


def test_decrypt_secret_supports_legacy_fernet_format():
    plain = "sk-fernet-key-001"
    assert decrypt_secret(_fernet_encrypt(plain)) == plain


def test_decrypt_secret_reports_changed_key_for_fernet_rows(monkeypatch):
    token = _fernet_encrypt("sk-old-key")
    monkeypatch.setattr(get_settings(), "secret_key", "another-secret-key-of-enough-length-123456")
    with pytest.raises(AppError) as exc_info:
        decrypt_secret(token)
    assert "SECRET_KEY" in exc_info.value.detail["message"]


def test_decrypt_secret_keeps_undecodable_hex_plaintext():
    # 纯 hex 明文若按旧格式解不开，应原样返回而不是报错/产出乱码
    value = "ff" * 16
    assert decrypt_secret(value) == value


def _save(db, **overrides):
    params = {
        "config_id": None,
        "provider": "qwen",
        "model_name": "qwen-plus",
        "purpose": "general",
        "endpoint": ENDPOINT,
        "api_key": None,
        "is_default": False,
        "extra_config": None,
    }
    params.update(overrides)
    return save_model_config(db, **params)


def test_new_purpose_without_key_inherits_same_endpoint_key(client):
    with db_session.SessionLocal() as db:
        _save(db, purpose="general", api_key="sk-shared-key", is_default=True)
        created = _save(db, purpose="task", model_name="qwen-turbo", api_key=None)
        assert created.api_key_encrypted, "新建行应继承同 endpoint 的已存密钥而不是落库成空"
        assert decrypt_secret(created.api_key_encrypted) == "sk-shared-key"


def test_update_with_blank_key_keeps_existing_key(client):
    with db_session.SessionLocal() as db:
        created = _save(db, purpose="qa", api_key="sk-original")
        updated = _save(db, config_id=created.id, purpose="qa", model_name="qwen-max", api_key=None)
        assert decrypt_secret(updated.api_key_encrypted) == "sk-original"


def test_set_default_clears_other_defaults_of_same_purpose(client):
    with db_session.SessionLocal() as db:
        first = _save(db, purpose="qa", api_key="sk-a", is_default=True)
        second = _save(db, purpose="qa", model_name="qwen-max", api_key="sk-b", is_default=True)
        db.refresh(first)
        assert first.is_default is False
        assert second.is_default is True
        resolved = get_default_model_config(db, "qa")
        assert resolved is not None and resolved.id == second.id


def test_save_rejects_soft_deleted_config(client):
    with db_session.SessionLocal() as db:
        created = _save(db, purpose="qa", api_key="sk-a")
        delete_model_config(db, config_id=created.id)
        with pytest.raises(AppError) as exc_info:
            _save(db, config_id=created.id, purpose="qa")
        assert exc_info.value.status_code == 404


def test_export_config_bundle_includes_plaintext_keys(client):
    from app.services.admin import export_config_bundle

    with db_session.SessionLocal() as db:
        _save(db, purpose="qa", model_name="qwen-max", api_key="sk-export-secret", is_default=True)
        bundle = export_config_bundle(db, actor_id=None)

    assert set(bundle) >= {"meta", "model_configs", "service_configs", "system_settings"}
    assert bundle["meta"]["kind"] == "classagent-config-export"
    assert bundle["meta"]["contains_secrets"] is True
    # 所有 API 配置都在，且密钥以明文导出（可再导入）
    exported = next((m for m in bundle["model_configs"] if m["model_name"] == "qwen-max"), None)
    assert exported is not None
    assert exported["api_key"] == "sk-export-secret"
    assert exported["purpose"] == "qa"
    assert bundle["meta"]["counts"]["model_configs"] == len(bundle["model_configs"])
