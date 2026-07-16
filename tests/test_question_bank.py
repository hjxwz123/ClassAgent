"""课程题库（检索优先 + 缺口补生成）行为测试。

覆盖设计核心约定：
- 跨用户复用：第二个学生同范围出题直接命中题库，零 LLM 调用；
- 按学生排重：同一学生不会二刷同一道库题，刷穿库存自动触发补生成、题库随之增长；
- 自定义要求跳过题库；教师出卷不检索但贡献题库；
- 跨课程硬隔离；无知识点标签的库题不进入章节圈定的请求（宁缺勿滥）；
- 作答结果经 bank_item_id 回流题库 attempt/correct 统计。
"""
from sqlalchemy import select

from app.db import session as db_session
from app.db.models import QuestionBankItem
from app.services.ai import ai_service
from tests.test_m3_m6_learning_flow import auth_headers, login_user, register_user

_STEM_COUNTER = {"value": 0}


def _letters(value: int) -> str:
    # 题库入库去重会把题干中的数字归一化，测试题干的唯一性必须用非数字字符表达
    return "".join("abcdefghij"[int(digit)] for digit in str(value))


def make_fake_generator(calls: list):
    def fake_generate(*, topic, source_text, count, type_counts=None, db=None, **kwargs):
        calls.append({"count": count, "type_counts": type_counts, "kwargs": kwargs})
        items = []
        for _ in range(int(count)):
            _STEM_COUNTER["value"] += 1
            marker = _letters(_STEM_COUNTER["value"])
            items.append(
                {
                    "question_type": "single_choice",
                    "stem": f"矩阵与线性变换生成题·变体{marker}：下列说法哪一项正确？",
                    "options": ["矩阵可以表示线性变换", "矩阵只能存图片", "矩阵与变换无关", "矩阵没有应用"],
                    "reference_answer": {"value": 0},
                    "explanation": "矩阵可以表示线性变换，其余选项均与课程资料矛盾。",
                    "score": 10,
                    "difficulty": "standard",
                }
            )
        return items

    return fake_generate


def _setup_course(client, *, suffix: str, student_count: int = 2):
    register_user(
        client,
        email=f"bank-teacher-{suffix}@example.com",
        password="Teacher123",
        nickname=f"题库教师{suffix}",
        role="teacher",
        employee_no=f"TBANK{suffix}",
    )
    teacher_login = login_user(client, email=f"bank-teacher-{suffix}@example.com", password="Teacher123")
    teacher_headers = auth_headers(teacher_login["access_token"])
    course_resp = client.post(
        "/api/v1/courses",
        json={"name": f"题库验证课程{suffix}", "description": "矩阵、线性变换与行列式基础", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_resp.status_code == 200, course_resp.text
    course = course_resp.json()["data"]
    student_headers_list = []
    for index in range(student_count):
        email = f"bank-student-{suffix}-{index}@example.com"
        register_user(
            client,
            email=email,
            password="Student123",
            nickname=f"题库学生{suffix}{index}",
            role="student",
            student_no=f"SBANK{suffix}{index}",
        )
        student_login = login_user(client, email=email, password="Student123")
        headers = auth_headers(student_login["access_token"])
        join_resp = client.post("/api/v1/courses/join", json={"course_code": course["course_code"]}, headers=headers)
        assert join_resp.status_code == 200, join_resp.text
        student_headers_list.append(headers)
    return course, teacher_headers, student_headers_list


def _generate_practice(client, headers, *, course_id: int, title: str, count: int = 2, extra: dict | None = None):
    payload = {
        "course_id": course_id,
        "title": title,
        "quiz_type": "practice",
        "question_count": count,
        "difficulty": "mixed",
        **(extra or {}),
    }
    resp = client.post("/api/v1/learning/quizzes/generate", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("id"), data
    return data


def _quiz_stems(client, headers, quiz_id: int) -> list[str]:
    resp = client.get(f"/api/v1/learning/quizzes/{quiz_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return [item["stem"] for item in resp.json()["data"]["questions"]]


def _bank_rows(course_id: int) -> list[QuestionBankItem]:
    with db_session.SessionLocal() as db:
        return list(db.scalars(select(QuestionBankItem).where(QuestionBankItem.course_id == course_id)))


def test_second_student_reuses_bank_without_ai_call(client, monkeypatch):
    course, _teacher_headers, (s1, s2) = _setup_course(client, suffix="reuse")
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    first = _generate_practice(client, s1, course_id=course["id"], title="学生一练习")
    assert len(calls) == 1
    first_stems = set(_quiz_stems(client, s1, first["id"]))
    rows = _bank_rows(course["id"])
    assert len(rows) == 2
    assert all(row.origin == "generated" and row.status == "active" for row in rows)
    assert first["metadata_json"]["bank_hit_count"] == 0
    assert first["metadata_json"]["bank_ingested_count"] == 2

    second = _generate_practice(client, s2, course_id=course["id"], title="学生二练习")
    assert len(calls) == 1, "第二个学生同范围出题应完全命中题库，不再调用大模型"
    assert second["metadata_json"]["bank_hit_count"] == 2
    assert set(_quiz_stems(client, s2, second["id"])) == first_stems
    with db_session.SessionLocal() as db:
        usage_counts = list(db.scalars(select(QuestionBankItem.usage_count).where(QuestionBankItem.course_id == course["id"])))
    assert usage_counts == [1, 1]


def test_same_student_never_repeats_and_topup_grows_bank(client, monkeypatch):
    course, _teacher_headers, (s1, s2) = _setup_course(client, suffix="grow")
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    first = _generate_practice(client, s1, course_id=course["id"], title="第一次练习")
    assert len(calls) == 1
    first_stems = set(_quiz_stems(client, s1, first["id"]))

    # 同一学生再出题：库里两道都已在其名下练习中出现过，必须全量补生成而不是复用
    second = _generate_practice(client, s1, course_id=course["id"], title="第二次练习")
    assert len(calls) == 2
    assert calls[-1]["count"] == 2
    second_stems = set(_quiz_stems(client, s1, second["id"]))
    assert not (first_stems & second_stems), "同一学生绝不应拿到重复题"
    assert len(_bank_rows(course["id"])) == 4, "补生成的题应继续沉淀进题库"

    # 另一个学生要 4 道：库存 4 道对其全部未见，应零调用命中
    third = _generate_practice(client, s2, course_id=course["id"], title="学生二练习", count=4)
    assert len(calls) == 2
    assert third["metadata_json"]["bank_hit_count"] == 4


def test_custom_instructions_bypass_bank(client, monkeypatch):
    course, _teacher_headers, (s1, s2) = _setup_course(client, suffix="custom")
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    _generate_practice(client, s1, course_id=course["id"], title="常规练习")
    assert len(calls) == 1

    custom = _generate_practice(
        client, s2, course_id=course["id"], title="定制练习",
        extra={"custom_instructions": "多考察应用题，避免概念题"},
    )
    assert len(calls) == 2, "填写自定义要求时应跳过题库直接生成"
    assert calls[-1]["kwargs"].get("custom_instructions") == "多考察应用题，避免概念题"
    assert custom["metadata_json"]["bank_hit_count"] == 0


def test_teacher_generation_ingests_but_never_retrieves(client, monkeypatch):
    course, teacher_headers, (s1,) = _setup_course(client, suffix="teach", student_count=1)
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    _generate_practice(client, s1, course_id=course["id"], title="学生练习")
    assert len(calls) == 1

    resp = client.post(
        "/api/v1/learning/quizzes/generate",
        json={"course_id": course["id"], "title": "教师课程测验", "quiz_type": "course", "question_count": 2},
        headers=teacher_headers,
    )
    assert resp.status_code == 200, resp.text
    assert len(calls) == 2, "教师出卷应保持全新生成，不走题库检索"
    rows = _bank_rows(course["id"])
    assert len(rows) == 4
    assert sorted(row.origin for row in rows) == ["generated", "generated", "teacher", "teacher"]

    # 防泄题：教师出卷（可能是待审核/未发布的考卷）沉淀的题绝不能被学生练习检索到。
    # s1 已见自己练习的 2 道 generated 题，库里剩下的只有 teacher 来源——必须全量重新生成。
    again = _generate_practice(client, s1, course_id=course["id"], title="学生再次练习")
    assert len(calls) == 3, "库存只剩教师考卷题时必须重新生成，不得把考题喂给学生"
    assert again["metadata_json"]["bank_hit_count"] == 0


def test_bank_is_isolated_per_course(client, monkeypatch):
    course_a, teacher_headers, (s1,) = _setup_course(client, suffix="isoa", student_count=1)
    course_b_resp = client.post(
        "/api/v1/courses",
        json={"name": "题库隔离课程B", "description": "另一门课的资料", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_b_resp.status_code == 200, course_b_resp.text
    course_b = course_b_resp.json()["data"]
    join_resp = client.post("/api/v1/courses/join", json={"course_code": course_b["course_code"]}, headers=s1)
    assert join_resp.status_code == 200, join_resp.text
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    _generate_practice(client, s1, course_id=course_a["id"], title="课程A练习")
    assert len(calls) == 1
    result_b = _generate_practice(client, s1, course_id=course_b["id"], title="课程B练习")
    assert len(calls) == 2, "课程B题库为空，绝不允许检索到课程A的题"
    assert result_b["metadata_json"]["bank_hit_count"] == 0
    assert len(_bank_rows(course_a["id"])) == 2
    assert len(_bank_rows(course_b["id"])) == 2


def test_chapter_scoped_request_excludes_unlabeled_bank_items(client, monkeypatch):
    course, teacher_headers, (s1, s2) = _setup_course(client, suffix="scope")
    chapter_resp = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第一章", "description": "", "order_index": 1},
        headers=teacher_headers,
    )
    assert chapter_resp.status_code == 200, chapter_resp.text
    chapter = chapter_resp.json()["data"]
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    # 全课程生成：该课程没有知识点，入库的题 knowledge_point_id 为空（无标签题）
    _generate_practice(client, s1, course_id=course["id"], title="全课程练习")
    assert len(calls) == 1
    rows = _bank_rows(course["id"])
    assert len(rows) == 2 and all(row.knowledge_point_id is None for row in rows)

    # 章节圈定请求：无标签题不允许进入，必须重新生成（宁缺勿滥）
    scoped = _generate_practice(
        client, s2, course_id=course["id"], title="章节练习",
        extra={"chapter_id": chapter["id"], "chapter_ids": [chapter["id"]]},
    )
    assert len(calls) == 2, "章节圈定的请求不得检索到无知识点标签的库题"
    assert scoped["metadata_json"]["bank_hit_count"] == 0

    # 同一学生的全课程请求：库里 4 道，其中 2 道是其章节练习已见题，应恰好命中另外 2 道
    whole = _generate_practice(client, s2, course_id=course["id"], title="学生二全课程练习")
    assert len(calls) == 2
    assert whole["metadata_json"]["bank_hit_count"] == 2


def test_attempt_results_flow_back_to_bank_stats(client, monkeypatch):
    course, _teacher_headers, (s1, s2) = _setup_course(client, suffix="stats")
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    _generate_practice(client, s1, course_id=course["id"], title="建库练习")
    reused = _generate_practice(client, s2, course_id=course["id"], title="复用练习")
    assert reused["metadata_json"]["bank_hit_count"] == 2

    detail_resp = client.get(f"/api/v1/learning/quizzes/{reused['id']}", headers=s2)
    assert detail_resp.status_code == 200, detail_resp.text
    questions = detail_resp.json()["data"]["questions"]
    submit_resp = client.post(
        f"/api/v1/learning/quizzes/{reused['id']}/submit",
        json={"answers": [
            {"question_id": questions[0]["id"], "answer": 0},
            {"question_id": questions[1]["id"], "answer": 1},
        ]},
        headers=s2,
    )
    assert submit_resp.status_code == 200, submit_resp.text

    with db_session.SessionLocal() as db:
        rows = list(db.scalars(select(QuestionBankItem).where(QuestionBankItem.course_id == course["id"])))
    assert sorted(int(row.attempt_count) for row in rows) == [1, 1], "作答结果应回流题库统计"
    assert sorted(int(row.correct_count) for row in rows) == [0, 1], "正确答案 0/错误答案 1 应各计一次"


def test_skipped_answers_do_not_pollute_bank_stats(client, monkeypatch):
    course, _teacher_headers, (s1, s2) = _setup_course(client, suffix="skip")
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    _generate_practice(client, s1, course_id=course["id"], title="建库练习")
    reused = _generate_practice(client, s2, course_id=course["id"], title="漏答练习")
    assert reused["metadata_json"]["bank_hit_count"] == 2

    questions = client.get(f"/api/v1/learning/quizzes/{reused['id']}", headers=s2).json()["data"]["questions"]
    # 只答第一题，第二题漏答：漏答 ≠ 答错，不得计入库题作答统计（否则好题会被误判为"正确率过低"淘汰）
    submit_resp = client.post(
        f"/api/v1/learning/quizzes/{reused['id']}/submit",
        json={"answers": [{"question_id": questions[0]["id"], "answer": 0}]},
        headers=s2,
    )
    assert submit_resp.status_code == 200, submit_resp.text
    with db_session.SessionLocal() as db:
        rows = list(db.scalars(select(QuestionBankItem).where(QuestionBankItem.course_id == course["id"])))
    assert sorted(int(row.attempt_count) for row in rows) == [0, 1], "漏答的题不应计入 attempt_count"
    assert sorted(int(row.correct_count) for row in rows) == [0, 1]


def test_partial_bank_hit_respects_difficulty_quota(client, monkeypatch):
    course, _teacher_headers, (s1,) = _setup_course(client, suffix="quota", student_count=1)
    calls: list = []
    monkeypatch.setattr(ai_service, "generate_quiz_questions", make_fake_generator(calls))

    # 直接向题库塞 3 道纯易题（无知识点标签 → 仅全课程请求可见）
    from app.services.learning import _bank_stem_key

    easy_stems = [f"送分题变体{marker}：矩阵的行列式反映什么？" for marker in "甲乙丙"]
    with db_session.SessionLocal() as db:
        for stem in easy_stems:
            db.add(QuestionBankItem(
                course_id=course["id"], chapter_id=None, knowledge_point_id=None,
                question_type="single_choice", difficulty="easy", stem=stem,
                options=["缩放系数", "颜色", "字体", "音量"], reference_answer={"value": 0},
                explanation="行列式反映线性变换的缩放系数。", stem_key=_bank_stem_key(stem),
                origin="generated", status="active",
            ))
        db.commit()

    # 混合难度 3 道：易题配额只有 1，库存 3 道易题只允许命中 1 道，其余 2 道补生成保持 3:5:2 结构
    result = _generate_practice(client, s1, course_id=course["id"], title="难度配额练习", count=3)
    assert result["metadata_json"]["bank_hit_count"] == 1, "部分命中不得让一卷混合难度练习被易题挤满"
    assert len(calls) == 1 and calls[-1]["count"] == 2
