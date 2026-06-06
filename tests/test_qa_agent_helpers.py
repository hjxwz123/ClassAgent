from app.services.qa import (
    ClassroomAgentPlan,
    _finalize_classroom_answer,
    _build_agent_retrieval_query,
    _extract_tables_from_text,
    _infer_question_type,
    _quiz_count_from_question,
    _quiz_show_answers,
    _quiz_type_counts_from_question,
    _slide_page_numbers_from_query,
    _strip_agent_answer_suffix,
)


def test_agent_detects_slide_page_numbers() -> None:
    assert _slide_page_numbers_from_query("第12张幻灯片讲了什么？") == [12]


def test_agent_prioritizes_table_question_type() -> None:
    assert (
        _infer_question_type(
            question="表格里 JPEG 和 PNG 有什么区别？",
            scope="specific",
            has_chapter_target=False,
            page_numbers=[],
            lesson_page_id=None,
        )
        == "table_question"
    )


def test_agent_treats_process_as_principle_not_figure() -> None:
    assert (
        _infer_question_type(
            question="JPEG 压缩流程是什么？",
            scope="specific",
            has_chapter_target=False,
            page_numbers=[],
            lesson_page_id=None,
        )
        == "principle"
    )
    assert (
        _infer_question_type(
            question="这张流程图是什么意思？",
            scope="specific",
            has_chapter_target=False,
            page_numbers=[],
            lesson_page_id=None,
        )
        == "figure_question"
    )


def test_agent_does_not_treat_complete_recovery_as_large_request() -> None:
    assert (
        _infer_question_type(
            question="第五章里 LZW 为什么能完整恢复原文？",
            scope="specific",
            has_chapter_target=True,
            page_numbers=[],
            lesson_page_id=None,
        )
        == "principle"
    )


def test_agent_detects_large_chapter_content_request() -> None:
    assert (
        _infer_question_type(
            question="告诉我第五章的所有内容",
            scope="specific",
            has_chapter_target=True,
            page_numbers=[],
            lesson_page_id=None,
        )
        == "large_chapter_request"
    )


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


def test_agent_quiz_request_options_parse_count_type_and_answers() -> None:
    question = "给我出2道选择题3道判断题，带答案和解析"

    assert _quiz_count_from_question(question) == 5
    assert _quiz_type_counts_from_question(question, total_count=5) == {
        "single_choice": 2,
        "judge": 3,
    }
    assert _quiz_show_answers(question) is True


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
