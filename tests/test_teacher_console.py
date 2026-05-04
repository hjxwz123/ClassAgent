from app.core.enums import LessonStatus, MaterialCategory, MaterialType, ProcessStatus
from app.db import session as db_session
from app.db.models import CourseMaterial, Lesson, LessonPage


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


def prepare_teacher_course(client):
    teacher = register_user(
        client,
        email="teacher-console@example.com",
        password="Teacher123",
        nickname="陈老师",
        role="teacher",
        employee_no="T2026999",
    )
    register_user(
        client,
        email="student-console@example.com",
        password="Student123",
        nickname="钱同学",
        role="student",
        student_no="S2026999",
    )
    teacher_headers = auth_headers(login_user(client, email="teacher-console@example.com", password="Teacher123")["access_token"])
    student_headers = auth_headers(login_user(client, email="student-console@example.com", password="Student123")["access_token"])
    course = client.post(
        "/api/v1/courses",
        json={"name": "计算机网络", "description": "网络体系结构", "term": "2026春"},
        headers=teacher_headers,
    ).json()["data"]
    chapter = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第一章 网络概述", "description": "", "order_index": 1},
        headers=teacher_headers,
    ).json()["data"]
    empty_chapter = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第二章 空章节", "description": "", "order_index": 2},
        headers=teacher_headers,
    ).json()["data"]
    join_response = client.post("/api/v1/courses/join", json={"course_code": course["course_code"]}, headers=student_headers)
    assert join_response.status_code == 200, join_response.text
    with db_session.SessionLocal() as db:
        material = CourseMaterial(
            course_id=course["id"],
            chapter_id=chapter["id"],
            uploader_id=teacher["id"],
            title="网络课件",
            category=MaterialCategory.COURSEWARE.value,
            material_type=MaterialType.PPTX.value,
            size_bytes=2048,
            original_filename="network.pptx",
            storage_path="uploads/test/network.pptx",
            preview_url="/static/uploads/test/network.pptx",
            extracted_text="计算机网络由节点、链路和协议组成。\n数据链路层负责帧封装和差错检测。",
            parse_status=ProcessStatus.READY.value,
            vector_status=ProcessStatus.READY.value,
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        lesson = Lesson(
            course_id=course["id"],
            chapter_id=chapter["id"],
            material_id=material.id,
            title="网络课件",
            summary="网络基础",
            page_count=2,
            status=LessonStatus.READY.value,
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        db.add_all(
            [
                LessonPage(
                    lesson_id=lesson.id,
                    page_number=1,
                    page_title="网络概述",
                    page_text="计算机网络由节点、链路和协议组成。",
                    script_text="讲解网络概述。",
                    script_status=ProcessStatus.READY.value,
                    audio_url="/static/generated/page1.wav",
                    subtitle_text="讲解网络概述。",
                ),
                LessonPage(
                    lesson_id=lesson.id,
                    page_number=2,
                    page_title="数据链路层",
                    page_text="数据链路层负责帧封装和差错检测。",
                    script_text="讲解数据链路层。",
                    script_status=ProcessStatus.READY.value,
                    audio_url="/static/generated/page2.wav",
                    subtitle_text="讲解数据链路层。",
                ),
            ]
        )
        db.commit()
        material_payload = {"id": material.id}
        lesson_id = lesson.id
    return teacher_headers, student_headers, course, chapter, empty_chapter, material_payload, lesson_id


def test_teacher_console_aggregation_and_actions(client):
    teacher_headers, student_headers, course, chapter, empty_chapter, material, lesson_id = prepare_teacher_course(client)

    dashboard_response = client.get("/api/v1/teacher/dashboard", headers=teacher_headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()["data"]
    assert dashboard["stats"]["course_total"] == 1
    assert dashboard["stats"]["student_total"] == 1

    courses_response = client.get("/api/v1/teacher/courses", headers=teacher_headers)
    assert courses_response.status_code == 200, courses_response.text
    assert courses_response.json()["data"][0]["material_count"] == 1

    cover_response = client.post(
        f"/api/v1/courses/{course['id']}/cover",
        files={"file": ("cover.png", b"course-cover", "image/png")},
        headers=teacher_headers,
    )
    assert cover_response.status_code == 200, cover_response.text
    assert cover_response.json()["data"]["cover_url"]
    student_courses_response = client.get("/api/v1/student/courses", headers=student_headers)
    assert student_courses_response.status_code == 200, student_courses_response.text
    assert student_courses_response.json()["data"][0]["cover_url"]

    home_response = client.get(f"/api/v1/teacher/courses/{course['id']}/home", headers=teacher_headers)
    assert home_response.status_code == 200, home_response.text
    home = home_response.json()["data"]
    assert home["quick_counts"]["lesson_count"] == 1
    assert len(home["chapters"]) == 2

    summary_response = client.get(f"/api/v1/teacher/courses/{course['id']}/materials/summary", headers=teacher_headers)
    assert summary_response.status_code == 200, summary_response.text
    assert summary_response.json()["data"]["ready"] == 1

    students_response = client.get(f"/api/v1/teacher/courses/{course['id']}/students", headers=teacher_headers)
    assert students_response.status_code == 200, students_response.text
    students = students_response.json()["data"]["items"]
    assert students[0]["student"]["nickname"] == "钱同学"
    student_id = students[0]["student"]["id"]

    detail_response = client.get(f"/api/v1/teacher/courses/{course['id']}/students/{student_id}", headers=teacher_headers)
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["data"]["student"]["id"] == student_id

    remind_response = client.post(
        f"/api/v1/teacher/courses/{course['id']}/students/{student_id}/remind",
        json={"title": "请完成第一章复习", "message": "请在今晚前完成网络概述课时，并整理一个问题。"},
        headers=teacher_headers,
    )
    assert remind_response.status_code == 200, remind_response.text
    assert remind_response.json()["data"]["sent"] is True
    notifications_response = client.get("/api/v1/student/notifications", headers=student_headers)
    assert notifications_response.status_code == 200, notifications_response.text
    reminders = [item for item in notifications_response.json()["data"] if item["type"] == "teacher_reminder"]
    assert reminders
    assert reminders[0]["title"] == "请完成第一章复习"
    assert reminders[0]["message"] == "请在今晚前完成网络概述课时，并整理一个问题。"
    dashboard_notifications_response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert dashboard_notifications_response.status_code == 200, dashboard_notifications_response.text
    dashboard_reminders = [
        item for item in dashboard_notifications_response.json()["data"]["notifications"] if item["type"] == "teacher_reminder"
    ]
    assert dashboard_reminders
    assert dashboard_reminders[0]["title"] == "请完成第一章复习"

    chapter_response = client.patch(
        f"/api/v1/teacher/courses/{course['id']}/chapters/{chapter['id']}",
        json={"title": "第一章 网络基础", "description": "", "order_index": 1},
        headers=teacher_headers,
    )
    assert chapter_response.status_code == 200, chapter_response.text
    assert chapter_response.json()["data"]["title"] == "第一章 网络基础"

    delete_chapter_response = client.delete(f"/api/v1/teacher/courses/{course['id']}/chapters/{empty_chapter['id']}", headers=teacher_headers)
    assert delete_chapter_response.status_code == 200, delete_chapter_response.text

    analysis_response = client.get(f"/api/v1/teacher/courses/{course['id']}/analysis", headers=teacher_headers)
    assert analysis_response.status_code == 200, analysis_response.text
    assert "metrics" in analysis_response.json()["data"]

    students_export = client.get(f"/api/v1/teacher/courses/{course['id']}/students/export", headers=teacher_headers)
    assert students_export.status_code == 200, students_export.text
    assert "钱同学" in students_export.text

    analysis_export = client.get(f"/api/v1/teacher/courses/{course['id']}/analysis/export", headers=teacher_headers)
    assert analysis_export.status_code == 200, analysis_export.text
    assert "指标" in analysis_export.text

    duplicate_response = client.post(f"/api/v1/teacher/lessons/{lesson_id}/duplicate", headers=teacher_headers)
    assert duplicate_response.status_code == 200, duplicate_response.text
    duplicate = duplicate_response.json()["data"]

    update_lesson_response = client.patch(
        f"/api/v1/teacher/lessons/{duplicate['id']}",
        json={"title": "网络课件副本", "status": "ready"},
        headers=teacher_headers,
    )
    assert update_lesson_response.status_code == 200, update_lesson_response.text
    assert update_lesson_response.json()["data"]["title"] == "网络课件副本"

    delete_lesson_response = client.delete(f"/api/v1/teacher/lessons/{duplicate['id']}", headers=teacher_headers)
    assert delete_lesson_response.status_code == 200, delete_lesson_response.text

    remove_student_response = client.delete(f"/api/v1/teacher/courses/{course['id']}/students/{student_id}", headers=teacher_headers)
    assert remove_student_response.status_code == 200, remove_student_response.text

    temp_course = client.post(
        "/api/v1/courses",
        json={"name": "临时课程", "description": "", "term": "2026春"},
        headers=teacher_headers,
    ).json()["data"]
    delete_course_response = client.delete(f"/api/v1/teacher/courses/{temp_course['id']}", headers=teacher_headers)
    assert delete_course_response.status_code == 200, delete_course_response.text


def test_teacher_can_delete_non_empty_chapter_without_deleting_content(client):
    teacher_headers, _, course, chapter, _empty_chapter, material, lesson_id = prepare_teacher_course(client)

    response = client.delete(f"/api/v1/teacher/courses/{course['id']}/chapters/{chapter['id']}", headers=teacher_headers)
    assert response.status_code == 200, response.text

    with db_session.SessionLocal() as db:
        saved_material = db.get(CourseMaterial, material["id"])
        saved_lesson = db.get(Lesson, lesson_id)
        assert saved_material is not None
        assert saved_lesson is not None
        assert saved_material.chapter_id is None
        assert saved_lesson.chapter_id is None

    home_response = client.get(f"/api/v1/teacher/courses/{course['id']}/home", headers=teacher_headers)
    assert home_response.status_code == 200, home_response.text
    home = home_response.json()["data"]
    assert all(item["id"] != chapter["id"] for item in home["chapters"])


def test_teacher_profile_preferences(client):
    register_user(
        client,
        email="teacher-profile@example.com",
        password="Teacher123",
        nickname="刘老师",
        role="teacher",
        employee_no="T2026888",
    )
    headers = auth_headers(login_user(client, email="teacher-profile@example.com", password="Teacher123")["access_token"])

    profile_response = client.get("/api/v1/teacher/profile", headers=headers)
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["data"]["notification_settings"]

    update_response = client.patch(
        "/api/v1/teacher/profile",
        json={"nickname": "刘明", "organization": "信息学院", "department": "计算机系", "bio": "主讲网络课程"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    data = update_response.json()["data"]
    assert data["user"]["nickname"] == "刘明"
    assert data["teacher_profile"]["department"] == "计算机系"

    notice_response = client.put(
        "/api/v1/teacher/profile/notifications",
        json={"settings": [{"key": "join", "enabled": False}, {"key": "ppt", "enabled": True}]},
        headers=headers,
    )
    assert notice_response.status_code == 200, notice_response.text
    settings = notice_response.json()["data"]
    assert next(item for item in settings if item["key"] == "join")["enabled"] is False
