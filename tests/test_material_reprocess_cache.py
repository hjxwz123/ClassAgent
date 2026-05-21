from sqlalchemy import select

from app.db import session as db_session
from app.db.models import AsyncTaskLog, CourseMaterial
from app.services.ai import ai_service
from app.services import materials as material_services


def register_user(client, *, email, password, nickname, role, student_no=None, employee_no=None):
    payload = {
        "email": email,
        "password": password,
        "nickname": nickname,
        "role": role,
        "student_no": student_no,
        "employee_no": employee_no,
    }
    if role == "teacher":
        admin_login = login_user(client, email="admin@classagent.com", password="Admin123456")
        response = client.post("/api/v1/admin/users/admin", json=payload, headers=auth_headers(admin_login["access_token"]))
    else:
        response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def login_user(client, *, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def build_txt_bytes() -> bytes:
    return "第一页课件内容。\n\n第二页课件内容。".encode("utf-8")


def test_reprocess_reuses_cached_pages_without_recalling_doc_parser(client, monkeypatch):
    register_user(
        client,
        email="teacher-local-reuse@example.com",
        password="Teacher123",
        nickname="本地复用老师",
        role="teacher",
        employee_no="LOCAL-REUSE",
    )
    teacher_login = login_user(client, email="teacher-local-reuse@example.com", password="Teacher123")
    teacher_headers = auth_headers(teacher_login["access_token"])
    course_resp = client.post(
        "/api/v1/courses",
        json={"name": "本地复用课程", "description": "测试", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_resp.status_code == 200, course_resp.text
    course = course_resp.json()["data"]

    parse_calls = {"count": 0}
    script_calls = {"count": 0}
    parsed_pages = [
        {"page_number": 1, "page_title": "第一页", "page_text": "第一页课件内容。"},
        {"page_number": 2, "page_title": "第二页", "page_text": "第二页课件内容。"},
    ]

    def fake_parse_material(path, material_type, db=None, filename=None, resume_task_id=None, on_progress=None):
        parse_calls["count"] += 1
        if on_progress:
            on_progress(
                {
                    "stage": "parsed",
                    "status": "success",
                    "progress": 100,
                    "page_count": len(parsed_pages),
                    "docmind_task_id": "docmind-20260512-localreusetest",
                }
            )
        return [dict(page) for page in parsed_pages]

    def fake_generate_page_script(title=None, content="", db=None):
        script_calls["count"] += 1
        if script_calls["count"] == 1:
            raise RuntimeError("script api failed")
        return f"{title or '本页内容'}的讲解脚本。"

    monkeypatch.setattr(material_services, "parse_material", fake_parse_material)
    monkeypatch.setattr(ai_service, "generate_page_script", fake_generate_page_script)

    upload_resp = client.post(
        "/api/v1/materials",
        data={"course_id": str(course["id"]), "title": "脚本失败后复用课件", "category": "courseware"},
        files={"file": ("reuse.txt", build_txt_bytes(), "text/plain")},
        headers=teacher_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    material = upload_resp.json()["data"]

    with db_session.SessionLocal() as db:
        stored_material = db.get(CourseMaterial, material["id"])
        assert stored_material is not None
        assert stored_material.parse_status == "ready"
        assert stored_material.extracted_text == "第一页课件内容。\n\n第二页课件内容。"
        assert stored_material.metadata_json["doc_parser_cache"]["page_count"] == 2
        assert stored_material.metadata_json["doc_parser_cache"]["source"] == "aliyun_docmind"
        first_task = db.scalar(select(AsyncTaskLog).where(AsyncTaskLog.target_id == material["id"]).order_by(AsyncTaskLog.id.desc()))
        assert first_task is not None
        assert first_task.status == "ready"

    reprocess_resp = client.post(f"/api/v1/materials/{material['id']}/reprocess", headers=teacher_headers)
    assert reprocess_resp.status_code == 200, reprocess_resp.text
    assert parse_calls["count"] == 1

    detail_resp = client.get(f"/api/v1/materials/{material['id']}", headers=teacher_headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["data"]
    assert detail["material"]["parse_status"] == "ready"
    assert detail["lesson_page_count"] == 2
    assert len(detail["pages"]) == 2
    assert detail["pages"][0]["script_text"]

    with db_session.SessionLocal() as db:
        stored_material = db.get(CourseMaterial, material["id"])
        assert stored_material is not None
        assert stored_material.parse_status == "ready"
        assert stored_material.metadata_json["doc_parser_cache"]["page_count"] == 2
        latest_task = db.scalar(select(AsyncTaskLog).where(AsyncTaskLog.target_id == material["id"]).order_by(AsyncTaskLog.id.desc()))
        assert latest_task is not None
        assert (latest_task.detail or {})["doc_parser"]["stage"] == "reused_local_cache"
