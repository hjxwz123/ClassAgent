import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import drop_db, init_db, reset_engine
from app.core.security import encrypt_secret
from app.db import session as db_session
from app.db.models import ServiceConfig
from app.main import create_app


def _ensure_mock_doc_parser() -> None:
    config = {
        "mock_page_counts": {"pptx": 2, "pdf": 1, "docx": 1, "txt": 2},
        "mock_text": "极限定义\n极限描述函数在某点附近的变化趋势。\n矩阵可以表示线性变换。\n连续函数在区间内没有跳跃。行列式反映缩放系数。",
    }
    with db_session.SessionLocal() as db:
        db.add(
            ServiceConfig(
                service_type="doc_parser",
                provider="mock",
                name="Mock 文档解析",
                config_encrypted=encrypt_secret(json.dumps(config, ensure_ascii=False)),
                is_enabled=True,
            )
        )
        db.commit()


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    reset_engine(f"sqlite:///{db_path}")
    drop_db()
    init_db()
    app = create_app()
    with TestClient(app) as test_client:
        _ensure_mock_doc_parser()
        yield test_client
    drop_db()
