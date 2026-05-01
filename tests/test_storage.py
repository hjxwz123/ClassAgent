import json
import sys
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.core.errors import AppError
from app.core.security import decrypt_secret, encrypt_secret
from app.db import session as db_session
from app.db.models import ServiceConfig
from app.services.admin import save_service_config
from app.services.materials import dispatch_material_processing
from app.services.storage import storage_service
from app.services.tts import tts_service


def _add_service_config(*, provider: str, config: dict) -> None:
    with db_session.SessionLocal() as db:
        db.add(
            ServiceConfig(
                service_type="oss",
                provider=provider,
                name="OSS",
                config_encrypted=encrypt_secret(json.dumps(config, ensure_ascii=False)),
                is_enabled=True,
            )
        )
        db.commit()


def test_storage_ignores_local_oss_provider(client, monkeypatch):
    _add_service_config(
        provider="local",
        config={
            "access_key_id": "ak",
            "access_key_secret": "secret",
            "bucket": "bucket",
            "region": "cn-hangzhou",
        },
    )
    monkeypatch.setattr(
        storage_service,
        "_upload_to_oss",
        lambda *args, **kwargs: pytest.fail("local OSS provider must not upload to OSS"),
    )

    upload = UploadFile(file=BytesIO(b"hello"), filename="demo.txt")
    with db_session.SessionLocal() as db:
        relative_path, size = storage_service.save_upload(upload, folder="storage_test", db=db)
        public_url = storage_service.public_url(relative_path, db=db)

    assert size == 5
    assert storage_service.absolute_path(relative_path).exists()
    assert public_url.endswith(f"/static/{relative_path}")


def test_aliyun_oss_upload_failure_returns_bad_request(client, monkeypatch):
    _add_service_config(
        provider="aliyun",
        config={
            "access_key_id": " ak ",
            "access_key_secret": " secret ",
            "bucket": " bucket ",
            "region": "cn-hangzhou",
        },
    )

    class FakeBucket:
        def __init__(self, *args, **kwargs):
            pass

        def put_object(self, *args, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setitem(
        sys.modules,
        "oss2",
        SimpleNamespace(
            Auth=lambda *args, **kwargs: object(),
            AuthV4=lambda *args, **kwargs: object(),
            Bucket=FakeBucket,
        ),
    )

    upload = UploadFile(file=BytesIO(b"hello"), filename="demo.txt")
    with db_session.SessionLocal() as db, pytest.raises(AppError) as exc_info:
        storage_service.save_upload(upload, folder="storage_test", db=db)

    assert exc_info.value.status_code == 400
    assert "OSS 上传失败" in exc_info.value.detail["message"]


def test_local_oss_service_config_drops_oss_credentials(client):
    with db_session.SessionLocal() as db:
        record = save_service_config(
            db,
            config_id=None,
            service_type="oss",
            provider="local",
            name="本地存储",
            is_enabled=True,
            config={
                "access_key_id": " ak ",
                "access_key_secret": " secret ",
                "bucket": " bucket ",
                "region": " cn-hangzhou ",
                "url_expire_hours": 24,
            },
        )
        raw = json.loads(decrypt_secret(record.config_encrypted))

    assert raw == {"url_expire_hours": 24}


def test_aliyun_oss_service_config_trims_and_removes_endpoint(client):
    with db_session.SessionLocal() as db:
        record = save_service_config(
            db,
            config_id=None,
            service_type="oss",
            provider="aliyun",
            name="阿里云 OSS",
            is_enabled=True,
            config={
                "access_key_id": " ak ",
                "access_key_secret": " secret ",
                "bucket": " bucket ",
                "region": " cn-hangzhou ",
                "endpoint": "https://oss-cn-hangzhou.aliyuncs.com",
            },
        )
        raw = json.loads(decrypt_secret(record.config_encrypted))

    assert raw["access_key_id"] == "ak"
    assert raw["access_key_secret"] == "secret"
    assert raw["bucket"] == "bucket"
    assert raw["region"] == "cn-hangzhou"
    assert "endpoint" not in raw


def test_tts_mock_provider_does_not_call_aliyun(client, monkeypatch):
    with db_session.SessionLocal() as db:
        db.add(
            ServiceConfig(
                service_type="tts",
                provider="mock",
                name="Mock TTS",
                config_encrypted=encrypt_secret(
                    json.dumps(
                        {
                            "access_key_id": "ak",
                            "access_key_secret": "secret",
                            "appkey": "app",
                            "voice": "xiaoyun",
                        },
                        ensure_ascii=False,
                    )
                ),
                is_enabled=True,
            )
        )
        db.commit()

    monkeypatch.setattr(
        tts_service,
        "_synthesize_aliyun",
        lambda *args, **kwargs: pytest.fail("mock TTS provider must not call Aliyun"),
    )

    with db_session.SessionLocal() as db:
        url, duration = tts_service.synthesize("测试语音", db=db)

    assert url.endswith(".wav")
    assert duration >= 2


def test_tts_aliyun_config_is_trimmed():
    assert tts_service._clean_config(
        {
            "access_key_id": " ak ",
            "access_key_secret": " secret ",
            "appkey": " app ",
            "voice": " xiaoyun ",
        }
    ) == {
        "access_key_id": "ak",
        "access_key_secret": "secret",
        "appkey": "app",
        "voice": "xiaoyun",
    }


def test_material_dispatch_does_not_raise_when_eager_task_fails(client, monkeypatch):
    import app.tasks.materials as material_tasks

    monkeypatch.setattr(
        material_tasks.process_material_task,
        "delay",
        lambda material_id: (_ for _ in ()).throw(RuntimeError("processing failed")),
    )

    dispatch_material_processing(1)
