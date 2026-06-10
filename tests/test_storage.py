import json
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from PIL import Image

from app.core.errors import AppError
from app.core.media import signed_media_url
from app.core.security import decrypt_secret, encrypt_secret
from app.core.config import PUBLIC_DIR, STORAGE_DIR
from app.core.upload_validation import validate_image_upload, validate_material_upload
from app.db import session as db_session
from app.db.models import ServiceConfig
from app.services.admin import save_service_config
from app.services.materials import dispatch_material_processing
from app.services.storage import storage_service
from app.services.tts import tts_service
from app.services.vector_store import vector_store


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\xf0\x1f\x00\x05\x05\x02\x00\x1e^\x99\xed\x00\x00\x00\x00IEND\xaeB`\x82"
)


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


def test_image_upload_reencodes_and_strips_exif(monkeypatch):
    image = Image.new("RGB", (8, 8), color=(255, 0, 0))
    exif = Image.Exif()
    exif[0x010E] = "sensitive description"
    source = BytesIO()
    image.save(source, format="JPEG", exif=exif)
    upload = UploadFile(file=BytesIO(source.getvalue()), filename="avatar.jpg")

    validated = validate_image_upload(upload, max_bytes=1024 * 1024, label="头像")

    assert validated.suffix == ".jpg"
    assert b"sensitive description" not in validated.content
    with Image.open(BytesIO(validated.content)) as sanitized:
        assert sanitized.getexif() == {}
        assert sanitized.format == "JPEG"
    assert upload.file.read() == validated.content


def test_image_upload_replaces_source_stream_with_sanitized_bytes():
    upload = UploadFile(file=BytesIO(PNG_BYTES + b"trailing-junk"), filename="avatar.png")

    validated = validate_image_upload(upload, max_bytes=1024 * 1024, label="头像")

    upload.file.seek(0)
    assert upload.file.read() == validated.content
    assert b"trailing-junk" not in validated.content


def test_image_upload_rejects_excessive_pixels(monkeypatch):
    from app.core import upload_validation

    image = Image.new("RGB", (3, 3), color=(0, 0, 255))
    source = BytesIO()
    image.save(source, format="PNG")
    monkeypatch.setattr(upload_validation.get_settings(), "upload_image_max_pixels", 4)
    upload = UploadFile(file=BytesIO(source.getvalue()), filename="tiny.png")

    with pytest.raises(AppError) as exc_info:
        validate_image_upload(upload, max_bytes=1024 * 1024, label="图片")

    assert "像素数量超过限制" in exc_info.value.detail["message"]


def test_material_upload_rejects_failed_av_scan(monkeypatch):
    from app.core import upload_validation

    settings = upload_validation.get_settings()
    monkeypatch.setattr(settings, "upload_av_scan_enabled", True)
    monkeypatch.setattr(settings, "upload_av_scan_command", "/bin/false {file}")
    upload = UploadFile(file=BytesIO(b"clean text"), filename="lesson.txt")

    with pytest.raises(AppError) as exc_info:
        validate_material_upload(upload, max_bytes=1024 * 1024)

    assert "未通过安全扫描" in exc_info.value.detail["message"]


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
    assert public_url == ""
    assert storage_service.normalize_public_url(f"http://127.0.0.1:8000/static/{relative_path}?download=1") is None


def test_static_mount_does_not_expose_private_storage(client):
    private_path = STORAGE_DIR / "uploads" / "private-demo.txt"
    public_path = PUBLIC_DIR / "public-demo.txt"
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text("private", encoding="utf-8")
    public_path.write_text("public", encoding="utf-8")

    private_response = client.get("/static/uploads/private-demo.txt")
    public_response = client.get("/static/public-demo.txt")

    assert private_response.status_code == 404
    assert public_response.status_code == 200
    assert public_response.text == "public"


def test_signed_media_url_enforces_signature_and_expiration(client):
    relative_path = "uploads/qa_images/course_1/user_1/demo.png"
    storage_path = STORAGE_DIR / relative_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(b"\x89PNG\r\n\x1a\nsigned")

    valid_url = signed_media_url(relative_path, expires_seconds=60)
    assert client.get(valid_url).status_code == 200

    tampered_url = valid_url.replace("sig=", "sig=x", 1)
    expired_url = signed_media_url(relative_path, expires_seconds=-1)
    assert client.get(tampered_url).status_code == 403
    assert client.get(expired_url).status_code == 403


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


def test_aliyun_oss_read_failure_hides_provider_detail(client, monkeypatch):
    _add_service_config(
        provider="aliyun",
        config={
            "access_key_id": "ak",
            "access_key_secret": "secret",
            "bucket": "classagent",
            "region": "cn-beijing",
        },
    )

    class FakeBucket:
        def __init__(self, *args, **kwargs):
            pass

        def get_object(self, *args, **kwargs):
            raise RuntimeError("{'Code': 'NoSuchKey', 'Key': 'uploads/missing-sensitive.txt', 'RequestId': 'secret-request'}")

    monkeypatch.setitem(
        sys.modules,
        "oss2",
        SimpleNamespace(
            Auth=lambda *args, **kwargs: object(),
            AuthV4=lambda *args, **kwargs: object(),
            Bucket=FakeBucket,
        ),
    )

    with db_session.SessionLocal() as db, pytest.raises(AppError) as exc_info:
        storage_service.read_bytes("uploads/missing-sensitive.txt", db=db)

    assert exc_info.value.status_code == 400
    message = exc_info.value.detail["message"]
    assert message == "资料文件读取失败，请稍后重试或联系管理员"
    assert "NoSuchKey" not in message
    assert "missing-sensitive" not in message
    assert "secret-request" not in message


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
        relative_path, size = storage_service.save_upload(upload, folder="avatars/user_1", db=db, public=True)
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
        relative_path = storage_service.save_bytes(b"audio", folder="generated/audio", filename="demo.wav", db=db, public=True)

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
