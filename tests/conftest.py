from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import drop_db, init_db, reset_engine
from app.main import create_app
from app.services.ai import ai_service
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


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    reset_engine(f"sqlite:///{db_path}")
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
        monkeypatch.setattr(ai_service, "answer_question", lambda question, contexts, history=None, db=None: ("测试回答。", False, None))
        monkeypatch.setattr(ai_service, "answer_general_question", lambda question, history=None, db=None: ("测试通用回答。", None))
        monkeypatch.setattr(ai_service, "rewrite_retrieval_query", lambda question, history=None, db=None: question)
        yield test_client
    drop_db()
