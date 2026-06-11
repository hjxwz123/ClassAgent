from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import drop_db, init_db, reset_engine
from app.main import create_app
from app.core.rate_limit import reset_rate_limits
from app.services.ai import ai_service
from app.services.email import email_service
from app.services.runtime_settings import invalidate_runtime_setting
from app.services import materials as material_services


def _parse_test_pages(path, material_type, db=None, filename=None, resume_task_id=None, on_progress=None):
    if on_progress:
        on_progress({"stage": "parsed", "status": "success", "progress": 100})
    counts = {"pptx": 2, "pdf": 1, "docx": 1, "txt": 2}
    text = "极限定义\n极限描述函数在某点附近的变化趋势。\n矩阵可以表示线性变换。\n连续函数在区间内没有跳跃。行列式反映缩放系数。"
    return [
        {
            "page_number": index,
            "page_title": f"测试解析第{index}页",
            "page_text": text,
        }
        for index in range(1, counts.get(material_type, 1) + 1)
    ]


def _generate_test_study_plan(*, goal, available_days, daily_minutes, course_name, db=None):
    today = date.today()
    return [
        {
            "title": f"{course_name} 第{index + 1}天学习任务",
            "task_date": (today + timedelta(days=index)).isoformat(),
            "task_type": "study_plan",
            "estimated_minutes": daily_minutes,
            "summary": f"围绕目标“{goal}”完成学习。",
        }
        for index in range(available_days)
    ]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    reset_engine(f"sqlite:///{db_path}")
    reset_rate_limits()
    # 运行时设置缓存按 key 全局缓存，跨测试用例换库后必须清空
    invalidate_runtime_setting()
    drop_db()
    init_db()
    app = create_app()
    with TestClient(app) as test_client:
        monkeypatch.setattr(material_services, "parse_material", _parse_test_pages)
        monkeypatch.setattr(ai_service, "summarize_lesson", lambda title, page_texts, db=None: f"{title}：测试摘要")
        monkeypatch.setattr(
            ai_service,
            "generate_page_script",
            lambda title=None, content="", db=None: f"{title or '本页内容'}的讲解脚本。",
        )
        monkeypatch.setattr(ai_service, "extract_knowledge_points", lambda text, db=None: ["极限定义", "矩阵", "线性变换"])
        monkeypatch.setattr(ai_service, "generate_common_mistakes", lambda knowledge_points, db=None: [])
        monkeypatch.setattr(ai_service, "generate_similar_questions", lambda knowledge_points, db=None: [])
        monkeypatch.setattr(ai_service, "generate_problem_guidance", lambda problem_text, level, contexts=None, db=None: "测试解析。")
        monkeypatch.setattr(ai_service, "generate_student_recommendation", lambda **kwargs: "测试学习建议。")
        monkeypatch.setattr(ai_service, "score_subjective_answer", lambda reference_keywords, user_answer, full_score, db=None: (full_score, "测试评分。"))
        monkeypatch.setattr(ai_service, "generate_study_plan", _generate_test_study_plan)
        monkeypatch.setattr(ai_service, "answer_question", lambda question, contexts, history=None, db=None: ("测试回答。", False, None))
        monkeypatch.setattr(ai_service, "answer_general_question", lambda question, history=None, db=None: ("测试通用回答。", None))
        monkeypatch.setattr(ai_service, "rewrite_retrieval_query", lambda question, history=None, db=None: question)
        monkeypatch.setattr(email_service, "send_password_reset_link", lambda db, to_email, link: None)
        monkeypatch.setattr(email_service, "send_registration_link", lambda db, to_email, link: None)
        monkeypatch.setattr(email_service, "send_password_reset_link_background", lambda to_email, link: None)
        monkeypatch.setattr(email_service, "send_registration_link_background", lambda to_email, link: None)
        yield test_client
    drop_db()
