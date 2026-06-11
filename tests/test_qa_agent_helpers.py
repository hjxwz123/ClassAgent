from app.services.qa import (
    ClassroomAgentPlan,
    _finalize_classroom_answer,
    _build_agent_retrieval_query,
    _extract_tables_from_text,
    _strip_agent_answer_suffix,
    _valid_plan_chapter_ids,
    _valid_plan_question_type,
    _valid_plan_scope,
    _valid_plan_tools,
)


def test_agent_accepts_task_model_plan_enums_and_discards_invalid_values() -> None:
    assert _valid_plan_scope("course_overview") == "course_overview"
    assert _valid_plan_scope("unknown") == "specific"
    assert _valid_plan_question_type("table_question") == "table_question"
    assert _valid_plan_question_type("chat") == "specific"
    assert _valid_plan_chapter_ids([1, "2", 99, "bad"], {1, 2, 3}) == [1, 2]


def test_agent_uses_task_model_tools_with_safe_fallback() -> None:
    assert _valid_plan_tools(["extract_table", "search_courseware", "bad_tool"], "table_question") == [
        "extract_table",
        "search_courseware",
        "quote_source",
    ]
    assert _valid_plan_tools([], "table_question") == ["search_courseware", "quote_source"]


def test_agent_retrieval_query_keeps_courseware_terms_without_internal_labels() -> None:
    query = _build_agent_retrieval_query(
        question_for_ai="当前问题：请帮我详细讲解 LZW 为什么是无损压缩？",
        question_type="principle",
        keywords=["LZW", "无损压缩"],
        search_phrases=["LZW 无损压缩", "动态字典"],
        expanded_terms=["Lempel Ziv Welch"],
        chapter_ids=[5],
        page_numbers=[12],
        section_numbers=["5.2"],
    )

    assert "问题类型" not in query
    assert "目标章节ID" not in query
    assert "请帮我详细讲解" not in query
    assert "LZW" in query
    assert "动态字典" in query
    assert "第12页" in query


def test_agent_extracts_markdown_tables_as_structured_rows() -> None:
    tables = _extract_tables_from_text(
        """
| 格式 | 压缩方式 | 特点 |
| --- | --- | --- |
| JPEG | 有损压缩 | 适合照片 |
| PNG | 无损压缩 | 支持透明 |
"""
    )

    assert len(tables) == 1
    assert tables[0].columns == ["格式", "压缩方式", "特点"]
    assert tables[0].rows[0] == ["JPEG", "有损压缩", "适合照片"]


def test_agent_answer_appends_sources_and_followups_but_strips_from_history() -> None:
    plan = ClassroomAgentPlan(
        question_type="concept",
        scope="specific",
        keywords=["LZW"],
        search_phrases=["LZW"],
        expanded_terms=[],
        chapter_ids=[],
        chapter_id=None,
        page_numbers=[],
        section_numbers=[],
        tools=["search_courseware"],
        retrieval_query="LZW",
    )
    answer = _finalize_classroom_answer(
        "LZW 是无损压缩。",
        sources=[{"material_title": "第五章《数据压缩技术》", "page_number": 12, "excerpt": "LZW 通过动态字典记录重复字符串。"}],
        plan=plan,
        out_of_scope=False,
    )

    assert "来源：" in answer
    assert "第12页/幻灯片" in answer
    assert "动态字典" in answer
    assert "你还可以继续问" in answer
    assert _strip_agent_answer_suffix(answer) == "LZW 是无损压缩。"


def test_rerank_retrieval_pool_filters_below_min_score(monkeypatch):
    from app.services import qa as qa_module

    pool = ["doc-a", "doc-b", "doc-c", "doc-d", "doc-e"]
    monkeypatch.setattr(
        qa_module.ai_service,
        "rerank_documents",
        lambda *, query, documents, db, top_n=None: [(4, 0.92), (1, 0.6), (0, 0.1)],
    )
    monkeypatch.setattr(qa_module, "runtime_setting_float", lambda db, key, default, **kwargs: 0.25)

    result = qa_module._rerank_retrieval_pool(object(), question="极限", pool=pool)
    # 0.1 低于下限被丢弃，其余按相关性降序
    assert result == ["doc-e", "doc-b"]


def test_rerank_retrieval_pool_returns_empty_when_all_below_threshold(monkeypatch):
    from app.services import qa as qa_module

    pool = ["a", "b", "c", "d", "e"]
    monkeypatch.setattr(
        qa_module.ai_service,
        "rerank_documents",
        lambda *, query, documents, db, top_n=None: [(0, 0.05), (1, 0.02)],
    )
    monkeypatch.setattr(qa_module, "runtime_setting_float", lambda db, key, default, **kwargs: 0.25)

    # 全部弱相关 → 空池（资料不足），而不是退回原始顺序
    assert qa_module._rerank_retrieval_pool(object(), question="q", pool=pool) == []


def test_rerank_retrieval_pool_degrades_to_none(monkeypatch):
    from app.services import qa as qa_module

    monkeypatch.setattr(
        qa_module.ai_service,
        "rerank_documents",
        lambda *, query, documents, db, top_n=None: None,
    )
    # 模型未配置/调用失败 → None（保持原有拼接顺序）；池子过小同样 None
    assert qa_module._rerank_retrieval_pool(object(), question="q", pool=["a"] * 5) is None
    assert qa_module._rerank_retrieval_pool(object(), question="q", pool=["a", "b"]) is None
