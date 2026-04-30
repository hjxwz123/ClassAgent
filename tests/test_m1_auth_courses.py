def register_user(client, *, email, password, nickname, role, student_no=None, employee_no=None):
    payload = {
        "email": email,
        "password": password,
        "nickname": nickname,
        "role": role,
        "student_no": student_no,
        "employee_no": employee_no,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def login_user(client, *, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_and_course_management_flow(client):
    teacher = register_user(
        client,
        email="teacher@example.com",
        password="Teacher123",
        nickname="张老师",
        role="teacher",
        employee_no="T2026001",
    )
    student = register_user(
        client,
        email="student@example.com",
        password="Student123",
        nickname="李同学",
        role="student",
        student_no="S2026001",
    )
    assert teacher["role"] == "teacher"
    assert student["role"] == "student"

    teacher_login = login_user(client, email="teacher@example.com", password="Teacher123")
    teacher_headers = auth_headers(teacher_login["access_token"])

    course_response = client.post(
        "/api/v1/courses",
        json={"name": "高等数学", "description": "极限与导数", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_response.status_code == 200, course_response.text
    course = course_response.json()["data"]
    assert len(course["course_code"]) == 6

    chapter_response = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第一章 极限", "description": "课程引导", "order_index": 1},
        headers=teacher_headers,
    )
    assert chapter_response.status_code == 200, chapter_response.text

    student_login = login_user(client, email="student@example.com", password="Student123")
    student_headers = auth_headers(student_login["access_token"])

    join_response = client.post(
        "/api/v1/courses/join",
        json={"course_code": course["course_code"]},
        headers=student_headers,
    )
    assert join_response.status_code == 200, join_response.text

    enrolled_response = client.get("/api/v1/courses/enrolled", headers=student_headers)
    assert enrolled_response.status_code == 200
    assert len(enrolled_response.json()["data"]) == 1

    detail_response = client.get(f"/api/v1/courses/{course['id']}", headers=student_headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["data"]
    assert detail_payload["student_count"] == 1
    assert len(detail_payload["chapters"]) == 1

    members_response = client.get(f"/api/v1/courses/{course['id']}/members", headers=teacher_headers)
    assert members_response.status_code == 200
    assert members_response.json()["data"][0]["user"]["email"] == "student@example.com"

    update_me_response = client.patch("/api/v1/auth/me", json={"bio": "热爱学习"}, headers=student_headers)
    assert update_me_response.status_code == 200
    assert update_me_response.json()["data"]["bio"] == "热爱学习"

    change_password_response = client.post(
        "/api/v1/auth/me/password",
        json={"old_password": "Student123", "new_password": "Student456"},
        headers=student_headers,
    )
    assert change_password_response.status_code == 200

    reset_request_response = client.post(
        "/api/v1/auth/password/reset/request",
        json={"email": "student@example.com"},
    )
    assert reset_request_response.status_code == 200
    code = reset_request_response.json()["data"]["debug_code"]
    assert code

    reset_confirm_response = client.post(
        "/api/v1/auth/password/reset/confirm",
        json={"email": "student@example.com", "code": code, "new_password": "Student789"},
    )
    assert reset_confirm_response.status_code == 200

    relogin = login_user(client, email="student@example.com", password="Student789")
    leave_response = client.post(
        f"/api/v1/courses/{course['id']}/leave",
        headers=auth_headers(relogin["access_token"]),
    )
    assert leave_response.status_code == 200
