from io import BytesIO

import pytest
from pptx import Presentation

from app.core.errors import AppError
from app.db import session as db_session
from app.db.models import QuizQuestion
from app.services.ai import ai_service, sanitize_quiz_source_text


def fake_quiz_questions(*, topic, source_text, count, db=None):
    items = [
        {
            "question_type": "single_choice",
            "stem": "矩阵可以表示线性变换，下列说法哪一项正确？",
            "options": ["矩阵可以表示线性变换", "矩阵只能表示图片", "矩阵与线性变换无关", "矩阵不需要理解条件"],
            "reference_answer": {"value": 0},
            "explanation": "课程资料明确提到矩阵可以表示线性变换。",
            "score": 10,
            "difficulty": "standard",
        },
        {
            "question_type": "judge",
            "stem": "判断：行列式可以反映线性变换中的缩放系数。",
            "options": ["正确", "错误"],
            "reference_answer": {"value": 0},
            "explanation": "课程资料提到行列式反映缩放系数。",
            "score": 10,
            "difficulty": "standard",
        },
        {
            "question_type": "short_answer",
            "stem": "请简述矩阵与线性变换之间的关系。",
            "options": None,
            "reference_answer": {"keywords": ["矩阵", "线性", "变换"]},
            "explanation": "应围绕矩阵可以表示线性变换展开。",
            "score": 20,
            "difficulty": "advanced",
        },
    ]
    return items[:count]


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


def test_learning_core_flow(client, monkeypatch):
    monkeypatch.setattr(ai_service, "generate_quiz_questions", fake_quiz_questions)
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
    assert "thinking_process" in qa_data

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
    assert "thinking_process" in history_resp.json()["data"][0]

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
    assert "knowledge_point_id" in wrong_resp.json()["data"][0]
    wrong_count_before = len(wrong_resp.json()["data"])

    wrong_practice_resp = client.post(
        "/api/v1/learning/wrong-questions/practice",
        params={"course_id": course["id"]},
        headers=student_headers,
    )
    assert wrong_practice_resp.status_code == 200, wrong_practice_resp.text
    wrong_practice = wrong_practice_resp.json()["data"]
    wrong_detail_resp = client.get(f"/api/v1/learning/quizzes/{wrong_practice['id']}", headers=student_headers)
    assert wrong_detail_resp.status_code == 200, wrong_detail_resp.text
    wrong_detail_questions = wrong_detail_resp.json()["data"]["questions"]
    assert wrong_detail_questions

    with db_session.SessionLocal() as db:
        answer_payload = []
        for item in wrong_detail_questions:
            stored_question = db.get(QuizQuestion, item["id"])
            reference = stored_question.reference_answer
            if isinstance(reference, dict):
                expected = reference.get("value", reference.get("answer", reference.get("correct_answer", reference.get("keywords", ""))))
            else:
                expected = reference
            if isinstance(expected, list):
                answer = " ".join(str(value) for value in expected) if item["question_type"] == "short_answer" else expected
            else:
                answer = expected
            answer_payload.append({"question_id": item["id"], "answer": answer})
    wrong_submit_resp = client.post(
        f"/api/v1/learning/quizzes/{wrong_practice['id']}/submit",
        json={"answers": answer_payload},
        headers=student_headers,
    )
    assert wrong_submit_resp.status_code == 200, wrong_submit_resp.text
    wrong_after_resp = client.get("/api/v1/learning/wrong-questions", params={"course_id": course["id"]}, headers=student_headers)
    assert wrong_after_resp.status_code == 200, wrong_after_resp.text
    wrong_after_items = wrong_after_resp.json()["data"]
    assert len(wrong_after_items) == wrong_count_before
    assert any(item["is_resolved"] for item in wrong_after_items)
    assert all(item["history_count"] >= 1 for item in wrong_after_items)

    practice_resp = client.post(
        "/api/v1/learning/quizzes/generate",
        json={
            "course_id": course["id"],
            "chapter_id": chapter["id"],
            "chapter_ids": [chapter["id"]],
            "title": "章节自练",
            "quiz_type": "practice",
            "question_count": 2,
            "prefer_weak_points": True,
        },
        headers=student_headers,
    )
    assert practice_resp.status_code == 200, practice_resp.text

    weak_resp = client.get("/api/v1/learning/weak-points", params={"course_id": course["id"]}, headers=student_headers)
    assert weak_resp.status_code == 200, weak_resp.text
    assert isinstance(weak_resp.json()["data"], list)

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
    assert records["recent_progress"]
    assert records["recent_qa"]
    assert records["recent_problems"]
    assert records["recent_attempts"]


def test_quiz_generation_requires_ai_questions(monkeypatch):
    monkeypatch.setattr(ai_service, "_call_chat", lambda *args, **kwargs: None)
    clean = sanitize_quiz_source_text(
        "![d03903cfb024ca7b18336cdcfff771e3.jpeg](https://classagent.oss-cn-beijing.aliyuncs.com/a.png)\n"
        "## 语法制导翻译概述\n语义分析的任务包括语义检查和翻译。"
    )
    assert "https" not in clean
    assert "d03903cfb024" not in clean
    assert "jpeg" not in clean
    assert "语义分析" in clean
    with pytest.raises(AppError) as exc:
        ai_service.generate_quiz_questions(topic="语法制导翻译", source_text=clean, count=1)
    assert "AI 出题失败" in exc.value.detail["message"]


def test_quiz_generation_normalizes_ai_reference_answer(monkeypatch):
    def ai_content(*args, **kwargs):
        return (
            '{"items":[{"question_type":"single_choice",'
            '"stem":"属性文法三元组 A=(G,C,F) 中，F 表示什么？",'
            '"options":["上下文无关文法","属性的计算规则","属性的有穷集","词法分析规则"],'
            '"reference_answer":{"correct_option":"B"},'
            '"explanation":"资料中说明 F 是关于属性的计算规则。",'
            '"score":10,"difficulty":"standard"}]}'
        )

    monkeypatch.setattr(ai_service, "_call_chat", ai_content)
    questions = ai_service.generate_quiz_questions(
        topic="属性文法",
        source_text="属性文法定义为 A=(G,C,F)，其中 F 是关于属性的计算规则。",
        count=1,
    )
    assert questions[0]["reference_answer"] == {"value": 1}


def test_quiz_generation_rejects_direct_fact_short_answer(monkeypatch):
    def ai_content(*args, **kwargs):
        return (
            '{"items":[{"question_type":"short_answer",'
            '"stem":"在自底向上的语法分析中，语义动作在何时执行？",'
            '"options":null,'
            '"reference_answer":{"keywords":["归约","产生式","语义动作"]},'
            '"explanation":"资料中说明自底向上分析在规约时执行语义动作。",'
            '"score":10,"difficulty":"standard"}]}'
        )

    monkeypatch.setattr(ai_service, "_call_chat", ai_content)
    with pytest.raises(AppError) as exc:
        ai_service.generate_quiz_questions(
            topic="语法制导翻译",
            source_text="自底向上的分析中，语义动作和产生式关联，当用产生式进行归约时执行。",
            count=1,
        )
    assert "有效题目不足" in exc.value.detail["message"]


def test_qa_stream_falls_back_to_regular_answer_when_upstream_stream_fails(client, monkeypatch):
    course, _chapter, lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import qa as qa_service

    lesson_detail_resp = client.get(f"/api/v1/lessons/{lesson_id}", headers=student_headers)
    assert lesson_detail_resp.status_code == 200, lesson_detail_resp.text
    first_page_id = lesson_detail_resp.json()["data"]["pages"][0]["id"]

    def fail_stream(**kwargs):
        raise RuntimeError("stream unavailable")

    def fallback_answer(**kwargs):
        return "非流式回退回答：矩阵可以表示线性变换。这个结论说明矩阵不仅是数字表格，还可以描述向量在空间中的旋转、缩放和投影。", False, "非流式回退思考过程"

    monkeypatch.setattr(qa_service.ai_service, "stream_answer_question", fail_stream)
    monkeypatch.setattr(qa_service.ai_service, "answer_question", fallback_answer)

    with client.stream(
        "POST",
        "/api/v1/qa/ask/stream",
        json={"course_id": course["id"], "lesson_page_id": first_page_id, "question": "矩阵可以表示什么"},
        headers=student_headers,
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200, body
    assert "event: error" not in body
    assert "非流式回退回答" in body
    assert "非流式回退思考过程" in body
    assert "event: final" in body
    assert body.count("event: delta") >= 2


def test_qa_uses_chapter_context_for_chapter_overview_when_vector_search_misses(client, monkeypatch):
    course, chapter, _lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import qa as qa_service

    captured: dict[str, list[str]] = {}
    monkeypatch.setattr(qa_service, "search_course_knowledge", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        qa_service.ai_service,
        "classify_qa_question_scope",
        lambda **kwargs: {"scope": "chapter_overview", "chapter_id": chapter["id"], "confidence": 0.95, "reason": "test"},
    )

    def answer_question(**kwargs):
        captured["contexts"] = list(kwargs["contexts"])
        return "已根据章节资料生成重点。", False, None

    monkeypatch.setattr(qa_service.ai_service, "answer_question", answer_question)
    response = client.post(
        "/api/v1/qa/ask",
        json={"course_id": course["id"], "question": "第一章 的重点是什么？"},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["is_out_of_scope"] is False
    assert data["sources"]
    assert captured["contexts"]
    assert any(item.startswith("章节：") for item in captured["contexts"])
    assert any("资料片段：" in item or "页面内容：" in item or "资料：" in item for item in captured["contexts"])


def test_qa_uses_course_context_for_course_overview_when_vector_search_misses(client, monkeypatch):
    course, _chapter, _lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import qa as qa_service

    captured: dict[str, list[str]] = {}
    monkeypatch.setattr(qa_service, "search_course_knowledge", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        qa_service.ai_service,
        "classify_qa_question_scope",
        lambda **kwargs: {"scope": "course_overview", "chapter_id": None, "confidence": 0.95, "reason": "test"},
    )

    def answer_question(**kwargs):
        captured["contexts"] = list(kwargs["contexts"])
        return "已根据课程资料生成整体重点。", False, None

    monkeypatch.setattr(qa_service.ai_service, "answer_question", answer_question)
    response = client.post(
        "/api/v1/qa/ask",
        json={"course_id": course["id"], "question": "这门课的重点是什么？"},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["is_out_of_scope"] is False
    assert data["sources"]
    assert captured["contexts"]
    assert any(item.startswith("课程：") for item in captured["contexts"])
    assert any("章节结构：" in item or "资料片段：" in item or "页面内容：" in item or "资料：" in item for item in captured["contexts"])


def test_qa_falls_back_to_database_chunks_when_vector_store_is_readonly(client, monkeypatch):
    course, _chapter, _lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import knowledge as knowledge_service
    from app.services import qa as qa_service

    captured: dict[str, list[str]] = {}
    readonly_error = RuntimeError("Error updating collection: Database error: error returned from database: (code: 1032) attempt to write a readonly database")
    monkeypatch.setattr(knowledge_service.vector_store, "query_course", lambda *args, **kwargs: (_ for _ in ()).throw(readonly_error))
    monkeypatch.setattr(knowledge_service.vector_store, "upsert_chunks", lambda *args, **kwargs: (_ for _ in ()).throw(readonly_error))
    monkeypatch.setattr(
        qa_service.ai_service,
        "classify_qa_question_scope",
        lambda **kwargs: {"scope": "specific", "chapter_id": None, "confidence": 0.9, "reason": "test"},
    )

    def answer_question(**kwargs):
        captured["contexts"] = list(kwargs["contexts"])
        return "已根据数据库知识切片回答。", False, None

    monkeypatch.setattr(qa_service.ai_service, "answer_question", answer_question)
    response = client.post(
        "/api/v1/qa/ask",
        json={"course_id": course["id"], "question": "矩阵可以表示什么？"},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["is_out_of_scope"] is False
    assert captured["contexts"]
    assert data["sources"]


def test_qa_image_attachment_uploads_and_participates_in_stream_answer(client, monkeypatch):
    course, _chapter, _lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import qa as qa_service
    from app.services.ai import ChatDelta

    captured: dict[str, str] = {}
    monkeypatch.setattr(qa_service.ocr_service, "recognize", lambda upload, db=None: "矩阵可以表示线性变换")

    def stream_answer(**kwargs):
        captured["question"] = kwargs["question"]
        yield ChatDelta("content", "图片中提到矩阵可以表示线性变换。")

    monkeypatch.setattr(qa_service.ai_service, "stream_answer_question", stream_answer)

    upload_resp = client.post(
        "/api/v1/qa/attachments/image",
        data={"course_id": str(course["id"])},
        files={"file": ("matrix.png", b"fake-image", "image/png")},
        headers=student_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    attachment = upload_resp.json()["data"]
    assert attachment["filename"] == "matrix.png"
    assert attachment["ocr_text"] == "矩阵可以表示线性变换"

    with client.stream(
        "POST",
        "/api/v1/qa/ask/stream",
        json={"course_id": course["id"], "question": "帮我看图", "attachments": [attachment]},
        headers=student_headers,
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200, body
    assert "event: error" not in body
    assert "图片中提到矩阵" in body
    assert "matrix.png" in body
    assert "OCR识别内容" in captured["question"]
    assert "矩阵可以表示线性变换" in captured["question"]

    history_resp = client.get("/api/v1/qa/history", params={"course_id": course["id"]}, headers=student_headers)
    assert history_resp.status_code == 200, history_resp.text
    assert history_resp.json()["data"][0]["attachments"][0]["filename"] == "matrix.png"


def test_knowledge_points_use_local_explanations(client, monkeypatch):
    course, chapter, _lesson_id, _teacher_headers, student_headers = bootstrap_course_with_material(client)

    from app.services import knowledge as knowledge_service

    monkeypatch.setattr(knowledge_service.ai_service, "extract_knowledge_points", lambda text, db=None: ["矩阵"])

    def fail_explanation_call(**kwargs):
        raise AssertionError("knowledge explanations should not call the model synchronously")

    monkeypatch.setattr(knowledge_service.ai_service, "generate_knowledge_explanation", fail_explanation_call)

    response = client.get(
        "/api/v1/learning/knowledge-points",
        params={"course_id": course["id"], "chapter_id": chapter["id"]},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    point = response.json()["data"][0]
    assert point["name"] == "矩阵"
    assert point["content_by_level"]["standard"]["definition"].startswith("矩阵")
