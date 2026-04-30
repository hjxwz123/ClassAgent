from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check():
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["service"] == "课程学习助手智能体后端"
