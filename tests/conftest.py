from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import drop_db, init_db, reset_engine
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    reset_engine(f"sqlite:///{db_path}")
    drop_db()
    init_db()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    drop_db()
