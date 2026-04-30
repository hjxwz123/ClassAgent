from io import BytesIO

from pptx import Presentation


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


def login_user(client, *, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def build_pptx_bytes() -> bytes:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "矩阵"
    slide.placeholders[1].text = "矩阵可以表示线性变换。"
    slide2 = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide2.shapes.title.text = "行列式"
    slide2.placeholders[1].text = "行列式反映缩放系数。"
    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def bootstrap_course_with_material(client):
    register_user(
        client,
        email="teacher3@example.com",
        password="Teacher123",
        nickname="周老师",
        role="teacher",
        employee_no="T2026003",
    )
    register_user(
        client,
        email="student3@example.com",
        password="Student123",
        nickname="钱同学",
        role="student",
        student_no="S2026003",
    )
    teacher_login = login_user(client, email="teacher3@example.com", password="Teacher123")
    student_login = login_user(client, email="student3@example.com", password="Student123")
    teacher_headers = auth_headers(teacher_login["access_token"])
    student_headers = auth_headers(student_login["access_token"])

    course_resp = client.post(
        "/api/v1/courses",
        json={"name": "线性代数进阶", "description": "矩阵、向量与行列式", "term": "2026春"},
        headers=teacher_headers,
    )
    course = course_resp.json()["data"]
    chapter_resp = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第一章 矩阵基础", "description": "矩阵概念", "order_index": 1},
        headers=teacher_headers,
    )
    chapter = chapter_resp.json()["data"]
    join_resp = client.post(
        "/api/v1/courses/join",
        json={"course_code": course["course_code"]},
        headers=student_headers,
    )
    assert join_resp.status_code == 200, join_resp.text

    upload_resp = client.post(
        "/api/v1/materials",
        data={
            "course_id": str(course["id"]),
            "title": "矩阵与行列式课件",
            "category": "courseware",
            "chapter_id": str(chapter["id"]),
        },
        files={
            "file": (
                "matrix_lesson.pptx",
                build_pptx_bytes(),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        },
        headers=teacher_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    material = upload_resp.json()["data"]
    detail_resp = client.get(f"/api/v1/materials/{material['id']}", headers=teacher_headers)
    assert detail_resp.status_code == 200, detail_resp.text
    lesson_id = detail_resp.json()["data"]["lesson_id"]
    publish_resp = client.post(f"/api/v1/lessons/{lesson_id}/publish", headers=teacher_headers)
    assert publish_resp.status_code == 200, publish_resp.text
    return course, chapter, lesson_id, teacher_headers, student_headers


def test_learning_core_flow(client):
    course, chapter, lesson_id, teacher_headers, student_headers = bootstrap_course_with_material(client)

    lessons_resp = client.get("/api/v1/lessons", params={"course_id": course["id"]}, headers=student_headers)
    assert lessons_resp.status_code == 200, lessons_resp.text
    assert len(lessons_resp.json()["data"]) == 1

    lesson_detail_resp = client.get(f"/api/v1/lessons/{lesson_id}", headers=student_headers)
    assert lesson_detail_resp.status_code == 200, lesson_detail_resp.text
    lesson_detail = lesson_detail_resp.json()["data"]
    assert len(lesson_detail["pages"]) == 2
    first_page_id = lesson_detail["pages"][0]["id"]

    progress_resp = client.post(
        f"/api/v1/lessons/{lesson_id}/progress",
        json={"current_page": 1, "added_seconds": 120, "completed": False},
        headers=student_headers,
    )
    assert progress_resp.status_code == 200, progress_resp.text
    assert progress_resp.json()["data"]["current_page"] == 1

    qa_resp = client.post(
        "/api/v1/qa/ask",
        json={"course_id": course["id"], "lesson_page_id": first_page_id, "question": "矩阵可以表示什么"},
        headers=student_headers,
    )
    assert qa_resp.status_code == 200, qa_resp.text
    qa_data = qa_resp.json()["data"]
    assert qa_data["is_out_of_scope"] is False
    assert qa_data["sources"]

    favorite_resp = client.post(
        f"/api/v1/qa/{qa_data['record_id']}/favorite",
        json={"is_favorite": True},
        headers=student_headers,
    )
    assert favorite_resp.status_code == 200, favorite_resp.text
    feedback_resp = client.post(
        f"/api/v1/qa/{qa_data['record_id']}/feedback",
        json={"feedback": "positive", "feedback_comment": "解释清晰"},
        headers=student_headers,
    )
    assert feedback_resp.status_code == 200, feedback_resp.text
    history_resp = client.get("/api/v1/qa/history", params={"keyword": "矩阵"}, headers=student_headers)
    assert history_resp.status_code == 200, history_resp.text
    assert len(history_resp.json()["data"]) >= 1

    problem_resp = client.post(
        "/api/v1/tutoring/problems/text",
        json={"course_id": course["id"], "text": "已知矩阵A，求其行列式"},
        headers=student_headers,
    )
    assert problem_resp.status_code == 200, problem_resp.text
    problem = problem_resp.json()["data"]
    assert problem["knowledge_points"]

    guidance_lvl1 = client.get(
        f"/api/v1/tutoring/problems/{problem['id']}/guidance",
        params={"level": 1},
        headers=student_headers,
    )
    assert guidance_lvl1.status_code == 200, guidance_lvl1.text
    guidance_lvl3 = client.get(
        f"/api/v1/tutoring/problems/{problem['id']}/guidance",
        params={"level": 3},
        headers=student_headers,
    )
    assert guidance_lvl3.status_code == 200, guidance_lvl3.text

    knowledge_resp = client.get(
        "/api/v1/learning/knowledge-points",
        params={"course_id": course["id"], "chapter_id": chapter["id"]},
        headers=student_headers,
    )
    assert knowledge_resp.status_code == 200, knowledge_resp.text
    assert len(knowledge_resp.json()["data"]) >= 1

    quiz_generate_resp = client.post(
        "/api/v1/learning/quizzes/generate",
        json={
            "course_id": course["id"],
            "chapter_id": chapter["id"],
            "title": "第一章测验",
            "quiz_type": "course",
            "question_count": 3,
        },
        headers=teacher_headers,
    )
    assert quiz_generate_resp.status_code == 200, quiz_generate_resp.text
    quiz = quiz_generate_resp.json()["data"]

    publish_quiz_resp = client.post(f"/api/v1/learning/quizzes/{quiz['id']}/publish", headers=teacher_headers)
    assert publish_quiz_resp.status_code == 200, publish_quiz_resp.text

    quiz_list_resp = client.get("/api/v1/learning/quizzes", params={"course_id": course["id"]}, headers=student_headers)
    assert quiz_list_resp.status_code == 200, quiz_list_resp.text
    assert len(quiz_list_resp.json()["data"]) >= 1

    quiz_detail_resp = client.get(f"/api/v1/learning/quizzes/{quiz['id']}", headers=student_headers)
    assert quiz_detail_resp.status_code == 200, quiz_detail_resp.text
    questions = quiz_detail_resp.json()["data"]["questions"]
    assert len(questions) == 3
    assert questions[0]["reference_answer"] is None

    submit_resp = client.post(
        f"/api/v1/learning/quizzes/{quiz['id']}/submit",
        json={
            "answers": [
                {"question_id": questions[0]["id"], "answer": 1},
                {"question_id": questions[1]["id"], "answer": 0},
                {"question_id": questions[2]["id"], "answer": "矩阵 线性 变换"},
            ]
        },
        headers=student_headers,
    )
    assert submit_resp.status_code == 200, submit_resp.text
    assert submit_resp.json()["data"]["score"] > 0

    wrong_resp = client.get("/api/v1/learning/wrong-questions", params={"course_id": course["id"]}, headers=student_headers)
    assert wrong_resp.status_code == 200, wrong_resp.text
    assert len(wrong_resp.json()["data"]) >= 1

    wrong_practice_resp = client.post(
        "/api/v1/learning/wrong-questions/practice",
        params={"course_id": course["id"]},
        headers=student_headers,
    )
    assert wrong_practice_resp.status_code == 200, wrong_practice_resp.text

    practice_resp = client.post(
        "/api/v1/learning/quizzes/generate",
        json={
            "course_id": course["id"],
            "chapter_id": chapter["id"],
            "title": "章节自练",
            "quiz_type": "practice",
            "question_count": 2,
        },
        headers=student_headers,
    )
    assert practice_resp.status_code == 200, practice_resp.text

    weak_resp = client.get("/api/v1/learning/weak-points", params={"course_id": course["id"]}, headers=student_headers)
    assert weak_resp.status_code == 200, weak_resp.text
    assert len(weak_resp.json()["data"]) >= 1

    plan_resp = client.post(
        "/api/v1/learning/plans",
        json={
            "course_id": course["id"],
            "title": "期中复习计划",
            "goal": "一周内完成矩阵与行列式复习",
            "available_days": 3,
            "daily_minutes": 40,
        },
        headers=student_headers,
    )
    assert plan_resp.status_code == 200, plan_resp.text
    plan_data = plan_resp.json()["data"]
    assert len(plan_data["tasks"]) == 3
    first_task_id = plan_data["tasks"][0]["id"]

    checkin_resp = client.post(
        f"/api/v1/learning/tasks/{first_task_id}/checkin",
        json={"notes": "已完成第一天任务"},
        headers=student_headers,
    )
    assert checkin_resp.status_code == 200, checkin_resp.text

    records_resp = client.get("/api/v1/learning/records", params={"course_id": course["id"]}, headers=student_headers)
    assert records_resp.status_code == 200, records_resp.text
    records = records_resp.json()["data"]
    assert records["progress_count"] >= 1
    assert records["qa_count"] >= 1
    assert records["problem_count"] >= 1
    assert records["attempt_count"] >= 1
