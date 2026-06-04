from datetime import UTC, datetime, timedelta
from io import BytesIO

from sqlalchemy import select

from app.db import session as db_session
from app.db.models import AsyncTaskLog, CourseMaterial
from app.services.materials import recover_interrupted_material_processing
from tests.auth_helpers import request_registration_token


def register_user(client, *, email, password, nickname, role, employee_no=None):
    payload = {
        "email": email,
        "password": password,
        "nickname": nickname,
        "role": role,
        "employee_no": employee_no,
    }
    if role == "teacher":
        admin_login = login_user(client, email="admin@classagent.com", password="Admin123456")
        response = client.post(
            "/api/v1/admin/users/admin",
            json=payload,
            headers=auth_headers(admin_login["access_token"]),
        )
    else:
        payload["token"] = request_registration_token(client, email)
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
    return "矩阵可以表示线性变换。\n\n行列式反映缩放系数。".encode("utf-8")


def test_recover_interrupted_material_processing_requeues_lost_local_tasks(client):
    register_user(
        client,
        email="teacher-recover@example.com",
        password="Teacher123",
        nickname="恢复老师",
        role="teacher",
        employee_no="RECOVER-QUEUE",
    )
    teacher_login = login_user(client, email="teacher-recover@example.com", password="Teacher123")
    teacher_headers = auth_headers(teacher_login["access_token"])
    course_resp = client.post(
        "/api/v1/courses",
        json={"name": "恢复课程", "description": "测试", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_resp.status_code == 200, course_resp.text
    course = course_resp.json()["data"]
    upload_resp = client.post(
        "/api/v1/materials",
        data={"course_id": str(course["id"]), "title": "恢复课件", "category": "courseware"},
        files={"file": ("recover.txt", BytesIO(build_txt_bytes()), "text/plain")},
        headers=teacher_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    material = upload_resp.json()["data"]
    stale_at = datetime.now(UTC) - timedelta(hours=2)

    with db_session.SessionLocal() as db:
        stored_material = db.get(CourseMaterial, material["id"])
        assert stored_material is not None
        for task in db.scalars(
            select(AsyncTaskLog).where(
                AsyncTaskLog.task_name == "material.process",
                AsyncTaskLog.target_type == "material",
                AsyncTaskLog.target_id == material["id"],
            )
        ):
            task.status = "failed"
            db.add(task)
        stored_material.parse_status = "processing"
        stored_material.vector_status = "processing"
        stale_task = AsyncTaskLog(
            task_name="material.process",
            target_type="material",
            target_id=material["id"],
            status="processing",
            detail={"pipeline": {"stage": "script_generation", "status": "processing"}},
            created_at=stale_at,
            updated_at=stale_at,
        )
        db.add_all([stored_material, stale_task])
        db.commit()

    with db_session.SessionLocal() as db:
        requeue_ids = recover_interrupted_material_processing(db, assume_local_queue_lost=True)
        assert requeue_ids == [material["id"]]

    with db_session.SessionLocal() as db:
        stored_material = db.get(CourseMaterial, material["id"])
        tasks = list(
            db.scalars(
                select(AsyncTaskLog)
                .where(
                    AsyncTaskLog.task_name == "material.process",
                    AsyncTaskLog.target_type == "material",
                    AsyncTaskLog.target_id == material["id"],
                )
                .order_by(AsyncTaskLog.id.desc())
            )
        )
        assert stored_material is not None
        assert stored_material.parse_status == "pending"
        assert stored_material.vector_status == "pending"
        assert tasks[0].status == "pending"
        assert tasks[0].detail["queue"]["reason"] == "restart_recovery"
        assert tasks[1].status == "failed"
        assert tasks[1].detail["error"] == "后台资料处理任务中断，系统已自动重新排队。"
