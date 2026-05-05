from sqlalchemy import select

from app.core.enums import LessonStatus, MaterialCategory, MaterialType, ProcessStatus, QuizStatus, QuizType, QuestionType
from app.db import session as db_session
from app.db.models import CourseMaterial, Lesson, LessonPage, ProblemRecord, QAConversation, QARecord, Quiz, QuizQuestion, StudyPlan, User
from app.services.learning import extract_reference_answer_value


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


def test_student_dashboard_without_courses_has_no_ai_recommendation(client):
    register_user(
        client,
        email="student-empty-dashboard@example.com",
        password="Student123",
        nickname="空课程学生",
        role="student",
        student_no="S2026999",
    )
    student_headers = auth_headers(login_user(client, email="student-empty-dashboard@example.com", password="Student123")["access_token"])

    response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert response.status_code == 200, response.text
    dashboard = response.json()["data"]
    assert dashboard["courses"] == []
    assert dashboard["continue_learning"] is None
    assert dashboard["recommendation"]["status"] == "no_courses"
    assert dashboard["recommendation"]["text"] == ""
    assert dashboard["recommendation"]["based_on"]["courses"] == 0


def prepare_student_workspace(client):
    teacher = register_user(
        client,
        email="student-console-teacher@example.com",
        password="Teacher123",
        nickname="林老师",
        role="teacher",
        employee_no="T2026010",
    )
    register_user(
        client,
        email="student-console-user@example.com",
        password="Student123",
        nickname="赵同学",
        role="student",
        student_no="S2026010",
    )
    teacher_headers = auth_headers(login_user(client, email="student-console-teacher@example.com", password="Teacher123")["access_token"])
    student_headers = auth_headers(login_user(client, email="student-console-user@example.com", password="Student123")["access_token"])
    first_course = client.post(
        "/api/v1/courses",
        json={"name": "网络协议", "description": "TCP/IP", "term": "2026春"},
        headers=teacher_headers,
    ).json()["data"]
    second_course = client.post(
        "/api/v1/courses",
        json={"name": "操作系统", "description": "进程与内存", "term": "2026春"},
        headers=teacher_headers,
    ).json()["data"]
    chapter = client.post(
        f"/api/v1/courses/{first_course['id']}/chapters",
        json={"title": "第一章 协议基础", "description": "", "order_index": 1},
        headers=teacher_headers,
    ).json()["data"]
    for course in (first_course, second_course):
        join_response = client.post("/api/v1/courses/join", json={"course_code": course["course_code"]}, headers=student_headers)
        assert join_response.status_code == 200, join_response.text
    with db_session.SessionLocal() as db:
        material = CourseMaterial(
            course_id=first_course["id"],
            chapter_id=chapter["id"],
            uploader_id=teacher["id"],
            title="TCP课件",
            category=MaterialCategory.COURSEWARE.value,
            material_type=MaterialType.PPTX.value,
            size_bytes=4096,
            original_filename="tcp.pptx",
            storage_path="uploads/test/tcp.pptx",
            preview_url="/static/uploads/test/tcp.pptx",
            extracted_text="TCP 提供可靠传输，UDP 提供无连接传输。",
            parse_status=ProcessStatus.READY.value,
            vector_status=ProcessStatus.READY.value,
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        lesson = Lesson(
            course_id=first_course["id"],
            chapter_id=chapter["id"],
            material_id=material.id,
            title="TCP可靠传输",
            summary="TCP与UDP",
            page_count=2,
            status=LessonStatus.PUBLISHED.value,
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        page = LessonPage(
            lesson_id=lesson.id,
            page_number=1,
            page_title="TCP",
            page_text="TCP 通过确认、重传和窗口控制实现可靠传输。",
            script_text="讲解 TCP 可靠传输。",
            script_status=ProcessStatus.READY.value,
            subtitle_text="TCP 可靠传输。",
        )
        db.add(page)
        quiz = Quiz(
            course_id=first_course["id"],
            chapter_id=chapter["id"],
            creator_id=teacher["id"],
            title="协议测验",
            description="基础测验",
            quiz_type=QuizType.COURSE.value,
            status=QuizStatus.PUBLISHED.value,
            total_score=20,
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        first_question = QuizQuestion(
            quiz_id=quiz.id,
            course_id=first_course["id"],
            chapter_id=chapter["id"],
            question_type=QuestionType.SINGLE_CHOICE.value,
            stem="TCP 的主要特性是？",
            options=["无连接", "可靠传输", "不确认", "不重传"],
            reference_answer={"value": 1},
            explanation="TCP 提供可靠传输。",
            score=10,
            difficulty="standard",
        )
        second_question = QuizQuestion(
            quiz_id=quiz.id,
            course_id=first_course["id"],
            chapter_id=chapter["id"],
            question_type=QuestionType.JUDGE.value,
            stem="UDP 是面向连接协议。",
            options=["正确", "错误"],
            reference_answer={"value": 1},
            explanation="UDP 是无连接协议。",
            score=10,
            difficulty="standard",
        )
        db.add_all([first_question, second_question])
        db.commit()
        db.refresh(page)
        db.refresh(quiz)
        db.refresh(first_question)
        return student_headers, first_course, second_course, page.id, quiz.id, first_question.id


def test_student_console_endpoints_and_multiple_courses(client):
    student_headers, first_course, second_course, page_id, quiz_id, question_id = prepare_student_workspace(client)

    dashboard_response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()["data"]
    assert len(dashboard["courses"]) == 2
    assert dashboard["continue_learning"]["lesson"]["title"] == "TCP可靠传输"

    courses_response = client.get("/api/v1/student/courses", headers=student_headers)
    assert courses_response.status_code == 200, courses_response.text
    assert {item["id"] for item in courses_response.json()["data"]} == {first_course["id"], second_course["id"]}

    preview_response = client.get(
        "/api/v1/student/courses/preview",
        params={"course_code": first_course["course_code"]},
        headers=student_headers,
    )
    assert preview_response.status_code == 200, preview_response.text
    assert preview_response.json()["data"]["already_joined"] is True

    home_response = client.get(f"/api/v1/student/courses/{first_course['id']}/home", headers=student_headers)
    assert home_response.status_code == 200, home_response.text
    home = home_response.json()["data"]
    assert home["course"]["id"] == first_course["id"]
    assert len(home["lessons"]) == 1
    assert len(home["materials"]) == 1
    assert home["student_count"] == 1

    note_response = client.get(f"/api/v1/student/pages/{page_id}/note", headers=student_headers)
    assert note_response.status_code == 200, note_response.text
    assert note_response.json()["data"]["content"] == ""
    save_note_response = client.put(f"/api/v1/student/pages/{page_id}/note", json={"content": "可靠传输要点"}, headers=student_headers)
    assert save_note_response.status_code == 200, save_note_response.text
    assert save_note_response.json()["data"]["content"] == "可靠传输要点"

    submit_response = client.post(
        f"/api/v1/learning/quizzes/{quiz_id}/submit",
        json={"answers": [{"question_id": question_id, "answer": 1}]},
        headers=student_headers,
    )
    assert submit_response.status_code == 200, submit_response.text
    result = submit_response.json()["data"]
    assert result["score"] == 10
    assert result["attempt"]["score"] == 10
    assert len(result["answers"]) == 2
    assert result["answers"][0]["correct_answer"] == 1
    assert result["answers"][1]["feedback"] == "本题未作答。"

    with db_session.SessionLocal() as db:
        existing_quiz = db.get(Quiz, quiz_id)
        alias_quiz = Quiz(
            course_id=first_course["id"],
            chapter_id=None,
            creator_id=existing_quiz.creator_id,
            title="答案兼容测验",
            description="验证不同模型答案结构",
            quiz_type=QuizType.COURSE.value,
            status=QuizStatus.PUBLISHED.value,
            total_score=5,
        )
        db.add(alias_quiz)
        db.commit()
        db.refresh(alias_quiz)
        alias_question = QuizQuestion(
            quiz_id=alias_quiz.id,
            course_id=first_course["id"],
            chapter_id=None,
            question_type=QuestionType.SINGLE_CHOICE.value,
            stem="TCP 的主要特性是？",
            options=["无连接", "可靠传输"],
            reference_answer={"correct_answer": "可靠传输"},
            explanation="标准答案可能来自模型的 correct_answer 字段。",
            score=5,
            difficulty="standard",
        )
        db.add(alias_question)
        db.commit()
        db.refresh(alias_quiz)
        db.refresh(alias_question)
        alias_quiz_id = alias_quiz.id
        alias_question_id = alias_question.id

    alias_submit_response = client.post(
        f"/api/v1/learning/quizzes/{alias_quiz_id}/submit",
        json={"answers": [{"question_id": alias_question_id, "answer": 1}]},
        headers=student_headers,
    )
    assert alias_submit_response.status_code == 200, alias_submit_response.text
    alias_result = alias_submit_response.json()["data"]
    assert alias_result["score"] == 5
    assert alias_result["answers"][0]["correct_answer"] == "可靠传输"
    assert extract_reference_answer_value({"key": "A"}) == "A"
    assert extract_reference_answer_value({"text": "格式奖励是二值设计"}) == "格式奖励是二值设计"
    assert extract_reference_answer_value({"key_points": ["归约", "产生式"]}) == ["归约", "产生式"]

    wrong_first_response = client.get("/api/v1/learning/wrong-questions", params={"course_id": first_course["id"]}, headers=student_headers)
    assert wrong_first_response.status_code == 200, wrong_first_response.text
    assert wrong_first_response.json()["data"]
    assert {item["question"]["course_id"] for item in wrong_first_response.json()["data"]} == {first_course["id"]}
    wrong_second_response = client.get("/api/v1/learning/wrong-questions", params={"course_id": second_course["id"]}, headers=student_headers)
    assert wrong_second_response.status_code == 200, wrong_second_response.text
    assert wrong_second_response.json()["data"] == []

    with db_session.SessionLocal() as db:
        student_id = db.scalar(select(User.id).where(User.email == "student-console-user@example.com"))
        first_conversation = QAConversation(course_id=first_course["id"], user_id=student_id, title="TCP问答")
        second_conversation = QAConversation(course_id=second_course["id"], user_id=student_id, title="进程问答")
        db.add_all([first_conversation, second_conversation])
        db.flush()
        db.add_all(
            [
                QARecord(conversation_id=first_conversation.id, course_id=first_course["id"], user_id=student_id, question="TCP是什么", answer="可靠传输协议"),
                QARecord(conversation_id=second_conversation.id, course_id=second_course["id"], user_id=student_id, question="进程是什么", answer="资源分配单位"),
                ProblemRecord(course_id=first_course["id"], user_id=student_id, source_type="text", raw_text="TCP题目", corrected_text="TCP题目"),
                ProblemRecord(course_id=second_course["id"], user_id=student_id, source_type="text", raw_text="进程题目", corrected_text="进程题目"),
                StudyPlan(user_id=student_id, course_id=first_course["id"], title="TCP计划", goal="复习TCP", summary="TCP"),
                StudyPlan(user_id=student_id, course_id=second_course["id"], title="OS计划", goal="复习进程", summary="OS"),
            ]
        )
        db.commit()

    qa_first_response = client.get("/api/v1/qa/history", params={"course_id": first_course["id"]}, headers=student_headers)
    assert qa_first_response.status_code == 200, qa_first_response.text
    assert {item["course_id"] for item in qa_first_response.json()["data"]} == {first_course["id"]}
    qa_second_response = client.get("/api/v1/qa/history", params={"course_id": second_course["id"]}, headers=student_headers)
    assert qa_second_response.status_code == 200, qa_second_response.text
    assert {item["course_id"] for item in qa_second_response.json()["data"]} == {second_course["id"]}
    qa_mixed_response = client.get("/api/v1/qa/history", headers=student_headers)
    assert qa_mixed_response.status_code == 200, qa_mixed_response.text
    assert qa_mixed_response.json()["data"] == []

    tutoring_first_response = client.get("/api/v1/tutoring/history", params={"course_id": first_course["id"]}, headers=student_headers)
    assert tutoring_first_response.status_code == 200, tutoring_first_response.text
    assert {item["course_id"] for item in tutoring_first_response.json()["data"]} == {first_course["id"]}
    tutoring_second_response = client.get("/api/v1/tutoring/history", params={"course_id": second_course["id"]}, headers=student_headers)
    assert tutoring_second_response.status_code == 200, tutoring_second_response.text
    assert {item["course_id"] for item in tutoring_second_response.json()["data"]} == {second_course["id"]}
    tutoring_mixed_response = client.get("/api/v1/tutoring/history", headers=student_headers)
    assert tutoring_mixed_response.status_code == 200, tutoring_mixed_response.text
    assert tutoring_mixed_response.json()["data"] == []

    plans_first_response = client.get("/api/v1/learning/plans", params={"course_id": first_course["id"]}, headers=student_headers)
    assert plans_first_response.status_code == 200, plans_first_response.text
    assert {item["course_id"] for item in plans_first_response.json()["data"]} == {first_course["id"]}
    plans_second_response = client.get("/api/v1/learning/plans", params={"course_id": second_course["id"]}, headers=student_headers)
    assert plans_second_response.status_code == 200, plans_second_response.text
    assert {item["course_id"] for item in plans_second_response.json()["data"]} == {second_course["id"]}
    plans_mixed_response = client.get("/api/v1/learning/plans", headers=student_headers)
    assert plans_mixed_response.status_code == 200, plans_mixed_response.text
    assert plans_mixed_response.json()["data"] == []

    profile_response = client.patch(
        "/api/v1/student/profile",
        json={"nickname": "赵同学A", "school": "第一中学", "bio": "喜欢网络课程"},
        headers=student_headers,
    )
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["data"]["student_profile"]["school"] == "第一中学"

    notice_response = client.put(
        "/api/v1/student/notifications",
        json={"settings": [{"key": "lesson", "enabled": True}, {"key": "plan", "enabled": True, "time": "19:30"}]},
        headers=student_headers,
    )
    assert notice_response.status_code == 200, notice_response.text
    assert any(item["key"] == "plan" and item["time"] == "19:30" for item in notice_response.json()["data"])
