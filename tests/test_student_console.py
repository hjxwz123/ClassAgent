from sqlalchemy import select

from app.core.enums import LessonStatus, MaterialCategory, MaterialType, ProcessStatus, QuizStatus, QuizType, QuestionType
from app.db import session as db_session
from app.db.models import CourseMaterial, Lesson, LessonPage, ProblemRecord, QAConversation, QARecord, Quiz, QuizQuestion, StudyPlan, User
from app.services import student as student_service
from app.services.learning import extract_reference_answer_value
from tests.auth_helpers import request_registration_token


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

    admin_headers = auth_headers(login_user(client, email="admin@classagent.com", password="Admin123456")["access_token"])
    announcement_resp = client.put("/api/v1/admin/system-settings/system.announcement", json={"value": "学生端公告"}, headers=admin_headers)
    assert announcement_resp.status_code == 200, announcement_resp.text
    enable_resp = client.put("/api/v1/admin/system-settings/system.announcement_enabled", json={"value": True}, headers=admin_headers)
    assert enable_resp.status_code == 200, enable_resp.text
    notifications_response = client.get("/api/v1/student/notifications", headers=student_headers)
    assert notifications_response.status_code == 200, notifications_response.text
    announcement = next(
        item
        for item in notifications_response.json()["data"]
        if item["type"] == "system_announcement" and item["message"] == "学生端公告"
    )
    assert announcement["unread"] is True
    read_response = client.post("/api/v1/student/notifications/read", json={"ids": [announcement["id"]]}, headers=student_headers)
    assert read_response.status_code == 200, read_response.text
    read_announcement = next(item for item in read_response.json()["data"] if item["id"] == announcement["id"])
    assert read_announcement["unread"] is False


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


def test_student_dashboard_recommendation_uses_daily_redis_cache(client, monkeypatch):
    student_headers, *_ = prepare_student_workspace(client)
    calls = []

    class FakeRedis:
        def __init__(self):
            self.values = {}

        def get(self, key):
            return self.values.get(key)

        def setex(self, key, ttl, value):
            self.values[key] = value

        def set(self, key, value, nx=False, ex=None):
            if nx and key in self.values:
                return None
            self.values[key] = value
            return True

        def delete(self, key):
            self.values.pop(key, None)

    cache = FakeRedis()

    def fake_recommendation(**kwargs):
        calls.append(kwargs)
        return f"今日建议 {len(calls)}"

    monkeypatch.setattr(student_service, "_student_recommendation_cache_client", lambda: cache)
    monkeypatch.setattr(student_service.ai_service, "generate_student_recommendation", fake_recommendation)

    # 首屏不再同步等待大模型：改为派发后台任务。测试为 Celery eager 模式，任务内联执行并写好缓存，
    # 本次响应即回填真实建议文案（生产异步模式下首屏会先返回兜底文案）。
    first_response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert first_response.status_code == 200, first_response.text
    assert first_response.json()["data"]["recommendation"]["text"] == "今日建议 1"

    second_response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["data"]["recommendation"]["text"] == "今日建议 1"
    assert len(calls) == 1

    refresh_response = client.get(
        "/api/v1/student/dashboard",
        params={"refresh_recommendation": True},
        headers=student_headers,
    )
    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.json()["data"]["recommendation"]["text"] == "今日建议 2"
    assert len(calls) == 2

    cached_response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert cached_response.status_code == 200, cached_response.text
    assert cached_response.json()["data"]["recommendation"]["text"] == "今日建议 2"
    assert len(calls) == 2


def test_student_dashboard_first_load_never_blocks_on_ai(client, monkeypatch):
    """生产（异步）语义：每日首次进入首屏时缓存必未命中，但不得同步调用大模型；
    应立即返回确定性兜底文案并派发后台任务。"""
    student_headers, *_ = prepare_student_workspace(client)
    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key):
            return store.get(key)

        def setex(self, key, ttl, value):
            store[key] = value

        def set(self, key, value, nx=False, ex=None):
            if nx and key in store:
                return None
            store[key] = value
            return True

        def delete(self, key):
            store.pop(key, None)

    monkeypatch.setattr(student_service, "_student_recommendation_cache_client", lambda: FakeRedis())

    ai_calls = []
    monkeypatch.setattr(
        student_service.ai_service,
        "generate_student_recommendation",
        lambda **kwargs: ai_calls.append(kwargs) or "AI 生成建议",
    )
    # 模拟生产异步：派发不内联执行（后台 worker 才会真正生成），首屏此刻缓存仍为空。
    dispatched = []
    monkeypatch.setattr(
        student_service,
        "_dispatch_student_recommendation",
        lambda **kwargs: dispatched.append(kwargs),
    )

    response = client.get("/api/v1/student/dashboard", headers=student_headers)
    assert response.status_code == 200, response.text
    recommendation = response.json()["data"]["recommendation"]
    assert recommendation["status"] == "generating"
    assert recommendation["text"]  # 兜底文案非空
    assert recommendation["text"] != "AI 生成建议"
    assert ai_calls == []  # 关键：首屏没有任何同步大模型调用
    assert len(dispatched) == 1  # 已派发后台生成任务


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

    duplicate_submit_response = client.post(
        f"/api/v1/learning/quizzes/{quiz_id}/submit",
        json={"answers": [{"question_id": question_id, "answer": 1}]},
        headers=student_headers,
    )
    assert duplicate_submit_response.status_code == 400, duplicate_submit_response.text
    assert "只能作答一次" in duplicate_submit_response.json()["message"]

    quiz_list_response = client.get("/api/v1/learning/quizzes", params={"course_id": first_course["id"]}, headers=student_headers)
    assert quiz_list_response.status_code == 200, quiz_list_response.text
    listed_quiz = next(item for item in quiz_list_response.json()["data"] if item["id"] == quiz_id)
    assert listed_quiz["has_attempted"] is True
    assert listed_quiz["latest_attempt"]["id"] == result["attempt"]["id"]
    assert listed_quiz["latest_attempt"]["correct_count"] == 1
    assert listed_quiz["latest_attempt"]["total_count"] == 2

    attempts_response = client.get(f"/api/v1/learning/quizzes/{quiz_id}/attempts", headers=student_headers)
    assert attempts_response.status_code == 200, attempts_response.text
    assert attempts_response.json()["data"][0]["id"] == result["attempt"]["id"]

    attempt_detail_response = client.get(f"/api/v1/learning/attempts/{result['attempt']['id']}", headers=student_headers)
    assert attempt_detail_response.status_code == 200, attempt_detail_response.text
    attempt_detail = attempt_detail_response.json()["data"]
    assert attempt_detail["quiz"]["id"] == quiz_id
    assert attempt_detail["answers"][0]["question"]["stem"] == "TCP 的主要特性是？"

    # 未作答 ≠ 做错：本次提交仅答对第 1 题、第 2 题跳过未答，跳过的题不进错题本（不污染薄弱点统计）。
    wrong_after_skip = client.get("/api/v1/learning/wrong-questions", params={"course_id": first_course["id"]}, headers=student_headers)
    assert wrong_after_skip.status_code == 200, wrong_after_skip.text
    assert wrong_after_skip.json()["data"] == []

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

    # 故意答错(选 index 0「无连接」，正确为 index 1「可靠传输」)，以产生一条真实错题。
    alias_submit_response = client.post(
        f"/api/v1/learning/quizzes/{alias_quiz_id}/submit",
        json={"answers": [{"question_id": alias_question_id, "answer": 0}]},
        headers=student_headers,
    )
    assert alias_submit_response.status_code == 200, alias_submit_response.text
    alias_result = alias_submit_response.json()["data"]
    assert alias_result["score"] == 0
    assert alias_result["answers"][0]["correct_answer"] == "可靠传输"
    assert extract_reference_answer_value({"key": "A"}) == "A"
    assert extract_reference_answer_value({"text": "格式奖励是二值设计"}) == "格式奖励是二值设计"
    assert extract_reference_answer_value({"key_points": ["归约", "产生式"]}) == ["归约", "产生式"]

    wrong_first_response = client.get("/api/v1/learning/wrong-questions", params={"course_id": first_course["id"]}, headers=student_headers)
    assert wrong_first_response.status_code == 200, wrong_first_response.text
    wrong_first_items = wrong_first_response.json()["data"]
    # 只有真正答错的 alias 题进错题本；主测验里"未作答"的判断题不应被计为答错。
    assert {item["question"]["id"] for item in wrong_first_items} == {alias_question_id}
    assert {item["question"]["course_id"] for item in wrong_first_items} == {first_course["id"]}
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
    notice_settings = notice_response.json()["data"]
    assert [item["key"] for item in notice_settings] == ["lesson", "quiz", "qa", "teacher", "system"]
    assert all("time" not in item for item in notice_settings)
    assert next(item for item in notice_settings if item["key"] == "lesson")["enabled"] is True

    profile_after_notice_response = client.get("/api/v1/student/profile", headers=student_headers)
    assert profile_after_notice_response.status_code == 200, profile_after_notice_response.text
    profile_notice_settings = profile_after_notice_response.json()["data"]["notification_settings"]
    assert [item["key"] for item in profile_notice_settings] == ["lesson", "quiz", "qa", "teacher", "system"]
