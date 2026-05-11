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
from app.services.vector_store import vector_store


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
    assert public_url == f"/static/{relative_path}"
    assert (
        storage_service.normalize_public_url(f"http://127.0.0.1:8000/static/{relative_path}?download=1")
        == f"/static/{relative_path}?download=1"
    )


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


def test_aliyun_oss_deletes_disposable_local_upload_copy(client, monkeypatch):
    _add_service_config(
        provider="aliyun",
        config={
            "access_key_id": "ak",
            "access_key_secret": "secret",
            "bucket": "bucket",
            "region": "cn-hangzhou",
        },
    )
    uploaded: list[tuple[str, bytes]] = []
    monkeypatch.setattr(
        storage_service,
        "_upload_to_oss",
        lambda relative_path, content, service: uploaded.append((relative_path, content)),
    )

    upload = UploadFile(file=BytesIO(b"avatar"), filename="avatar.png")
    with db_session.SessionLocal() as db:
        relative_path, size = storage_service.save_upload(upload, folder="avatars/user_1", db=db)
        public_url = storage_service.public_url(relative_path, db=db)

    assert size == 6
    assert uploaded == [(relative_path, b"avatar")]
    assert not storage_service.absolute_path(relative_path).exists()
    assert public_url == f"https://bucket.oss-cn-hangzhou.aliyuncs.com/{relative_path}"


def test_aliyun_oss_keeps_material_source_local_copy(client, monkeypatch):
    _add_service_config(
        provider="aliyun",
        config={
            "access_key_id": "ak",
            "access_key_secret": "secret",
            "bucket": "bucket",
            "region": "cn-hangzhou",
        },
    )
    monkeypatch.setattr(storage_service, "_upload_to_oss", lambda *args, **kwargs: None)

    upload = UploadFile(file=BytesIO(b"material"), filename="lesson.pdf")
    with db_session.SessionLocal() as db:
        relative_path, size = storage_service.save_upload(upload, folder="course_1", db=db)

    assert size == 8
    assert storage_service.absolute_path(relative_path).exists()


def test_aliyun_oss_deletes_generated_audio_local_copy(client, monkeypatch):
    _add_service_config(
        provider="aliyun",
        config={
            "access_key_id": "ak",
            "access_key_secret": "secret",
            "bucket": "bucket",
            "region": "cn-hangzhou",
        },
    )
    uploaded: list[tuple[str, bytes]] = []
    monkeypatch.setattr(
        storage_service,
        "_upload_to_oss",
        lambda relative_path, content, service: uploaded.append((relative_path, content)),
    )

    with db_session.SessionLocal() as db:
        relative_path = storage_service.save_bytes(b"audio", folder="generated/audio", filename="demo.wav", db=db)

    assert uploaded == [(relative_path, b"audio")]
    assert not storage_service.absolute_path(relative_path).exists()


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


def test_vector_delete_is_best_effort(client, monkeypatch):
    monkeypatch.setattr(
        vector_store._client,
        "get_collection",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("readonly vector database")),
    )

    with db_session.SessionLocal() as db:
        vector_store.delete_material(db, course_id=123, material_id=456)


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


def test_tts_requires_enabled_service(client):
    with db_session.SessionLocal() as db:
        with pytest.raises(AppError) as exc:
            tts_service.synthesize("测试语音", db=db)

    assert "TTS 服务未配置" in exc.value.detail["message"]


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
