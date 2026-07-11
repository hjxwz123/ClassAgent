from app.services.ai import ai_service
from app.services.runtime_config import RuntimeModelConfig


def test_embed_texts_batches_qwen_requests(monkeypatch):
    batch_sizes: list[int] = []

    class FakeResponse:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
            self.text = ""

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            inputs = list((json or {}).get("input") or [])
            batch_sizes.append(len(inputs))
            return FakeResponse(
                {
                    "data": [
                        {"embedding": [float(index), float(index + 1)]}
                        for index, _value in enumerate(inputs, start=1)
                    ]
                }
            )

    monkeypatch.setattr(
        "app.services.ai.get_default_model_config",
        lambda db, purpose: RuntimeModelConfig(
            id=1,
            provider="qwen",
            model_name="text-embedding-v4",
            purpose="embedding",
            endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key",
            extra_config={"dimensions": 2},
        ),
    )
    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)

    vectors = ai_service.embed_texts(None, [f"text-{index}" for index in range(23)])

    assert len(vectors) == 23
    assert batch_sizes == [10, 10, 3]


def test_task_model_plans_courseware_retrieval(monkeypatch):
    calls: list[dict] = []

    def fake_call_json(db, *, purpose, system_prompt, user_prompt, allow_fallback=True):
        calls.append({"purpose": purpose, "prompt": user_prompt})
        return {
            "keywords": ["霍夫曼算法", "前缀编码"],
            "search_phrases": ["霍夫曼算法 前缀编码", "Huffman coding"],
            "expanded_terms": ["最优二叉树"],
            "exclude_terms": ["帮我", "讲解"],
            "reason": "提取算法核心词",
        }

    monkeypatch.setattr(ai_service, "_call_json", fake_call_json)

    plan = ai_service.plan_courseware_retrieval(
        question="帮我讲解霍夫曼算法",
        question_type="concept",
        course_name="多媒体技术",
        chapter_titles=["数据压缩"],
        db=None,
    )

    assert calls[0]["purpose"] == "task"
    assert plan["keywords"] == ["霍夫曼算法", "前缀编码"]
    assert plan["search_phrases"][0] == "霍夫曼算法 前缀编码"
    assert "帮我" in plan["exclude_terms"]


def test_task_model_plans_full_qa_task(monkeypatch):
    calls: list[dict] = []

    def fake_call_json(db, *, purpose, system_prompt, user_prompt, allow_fallback=True):
        calls.append({"purpose": purpose, "system": system_prompt, "prompt": user_prompt})
        return {
            "scope": "course_overview",
            "question_type": "course_overview",
            "chapter_ids": [],
            "chapter_id": None,
            "page_numbers": [],
            "section_numbers": [],
            "keywords": ["编译原理", "复习"],
            "search_phrases": ["编译原理 复习提纲"],
            "expanded_terms": ["compiler principles"],
            "tools": ["get_chapter_summary", "get_section_summary", "quote_source"],
            "retrieval_query": "编译原理 复习提纲",
            "large_request": False,
            "quiz": {"count": None, "type_counts": {}, "show_answers": False},
            "reason": "课程复习请求",
        }

    monkeypatch.setattr(ai_service, "_call_json", fake_call_json)

    plan = ai_service.plan_qa_task(
        question="我该如何复习《编译原理》？",
        course_name="编译原理",
        chapters=[{"id": 1, "order_index": 1, "title": "词法分析"}],
        db=None,
    )

    assert calls[0]["purpose"] == "task"
    assert "问答任务规划器" in calls[0]["system"]
    assert plan["scope"] == "course_overview"
    assert plan["question_type"] == "course_overview"
    assert plan["retrieval_query"] == "编译原理 复习提纲"


def test_task_model_handles_retrieval_rewrite_and_full_qa_plan(monkeypatch):
    calls: list[dict] = []

    def fake_call_json(db, *, purpose, system_prompt, user_prompt, allow_fallback=True):
        calls.append({"purpose": purpose, "prompt": user_prompt})
        if "问答任务规划器" in system_prompt:
            return {
                "scope": "specific",
                "question_type": "concept",
                "chapter_ids": [],
                "chapter_id": None,
                "keywords": ["霍夫曼算法", "前缀编码"],
                "search_phrases": ["霍夫曼算法 前缀编码"],
                "expanded_terms": [],
                "tools": ["search_courseware", "quote_source"],
                "retrieval_query": "霍夫曼算法 前缀编码",
                "large_request": False,
            }
        return {"retrieval_query": "霍夫曼算法 前缀编码", "keywords": ["霍夫曼算法", "前缀编码"]}

    monkeypatch.setattr(ai_service, "_call_json", fake_call_json)

    rewritten = ai_service.rewrite_retrieval_query(question="帮我讲解霍夫曼算法", db=None)
    plan = ai_service.plan_qa_task(
        question="帮我讲解霍夫曼算法",
        course_name="多媒体技术",
        chapters=[],
        db=None,
    )

    assert rewritten.startswith("霍夫曼算法 前缀编码")
    assert plan["question_type"] == "concept"
    assert [call["purpose"] for call in calls] == ["task", "task"]


def test_build_rerank_request_qwen_defaults_to_dashscope():
    from app.services.ai import RERANK_DASHSCOPE_ENDPOINT, build_rerank_request

    url, payload = build_rerank_request(
        provider="qwen",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_name="gte-rerank-v2",
        query="极限的定义",
        documents=["文档一", "文档二"],
        top_n=2,
    )
    assert url == RERANK_DASHSCOPE_ENDPOINT
    assert payload["model"] == "gte-rerank-v2"
    assert payload["input"] == {"query": "极限的定义", "documents": ["文档一", "文档二"]}
    assert payload["parameters"] == {"return_documents": False, "top_n": 2}


def test_build_rerank_request_custom_appends_rerank_path():
    from app.services.ai import build_rerank_request

    url, payload = build_rerank_request(
        provider="custom",
        endpoint="https://api.example.com/v1/",
        model_name="bge-reranker-v2-m3",
        query="q",
        documents=["a", "b"],
        top_n=1,
    )
    assert url == "https://api.example.com/v1/rerank"
    assert payload == {"model": "bge-reranker-v2-m3", "query": "q", "documents": ["a", "b"], "top_n": 1, "return_documents": False}


def test_build_rerank_request_qwen3_honors_workspace_domain():
    """百炼业务空间独立域名（{WorkspaceId}.<region>.maas.aliyuncs.com）不应被强制打回经典 dashscope 域名。"""
    from app.services.ai import build_rerank_request

    ws = "https://ws-abc123.cn-beijing.maas.aliyuncs.com"
    # qwen3-rerank：从配置的 compatible-mode base（同 host）推导兼容版 reranks
    url, payload = build_rerank_request(
        provider="qwen",
        endpoint=f"{ws}/compatible-mode/v1",
        model_name="qwen3-rerank",
        query="q",
        documents=["a", "b"],
        top_n=2,
    )
    assert url == f"{ws}/compatible-api/v1/reranks"
    assert sorted(payload) == ["documents", "instruct", "model", "query", "top_n"]

    # 直接配完整 reranks URL 也原样沿用
    url2, _ = build_rerank_request(
        provider="qwen",
        endpoint=f"{ws}/compatible-api/v1/reranks",
        model_name="qwen3-rerank",
        query="q",
        documents=["a", "b"],
        top_n=2,
    )
    assert url2 == f"{ws}/compatible-api/v1/reranks"

    # 其它 qwen 重排（gte-rerank-v2 等）走 DashScope 文本重排协议，同样按 host 推导
    url3, _ = build_rerank_request(
        provider="qwen",
        endpoint=f"{ws}/compatible-mode/v1",
        model_name="gte-rerank-v2",
        query="q",
        documents=["a", "b"],
        top_n=2,
    )
    assert url3 == f"{ws}/api/v1/services/rerank/text-rerank/text-rerank"


def test_build_rerank_request_qwen3_empty_endpoint_falls_back_to_classic():
    from app.services.ai import RERANK_DASHSCOPE_COMPAT_ENDPOINT, build_rerank_request

    url, _ = build_rerank_request(
        provider="qwen",
        endpoint="",
        model_name="qwen3-rerank",
        query="q",
        documents=["a", "b"],
        top_n=2,
    )
    assert url == RERANK_DASHSCOPE_COMPAT_ENDPOINT


def test_parse_rerank_results_supports_dashscope_and_standard():
    from app.services.ai import parse_rerank_results

    dashscope_body = {"output": {"results": [{"index": 1, "relevance_score": 0.32}, {"index": 0, "relevance_score": 0.91}]}}
    assert parse_rerank_results(dashscope_body) == [(0, 0.91), (1, 0.32)]

    standard_body = {"results": [{"index": 2, "score": 0.5}, {"index": 7, "relevance_score": 0.8}, {"index": "bad"}]}
    assert parse_rerank_results(standard_body) == [(7, 0.8), (2, 0.5)]

    assert parse_rerank_results({"results": []}) == []
    assert parse_rerank_results(None) == []


def test_rerank_documents_orders_and_limits(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"output": {"results": [{"index": 2, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.7}, {"index": 9, "relevance_score": 0.6}]}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            assert "rerank" in url
            assert json["parameters"]["top_n"] == 2
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.ai.get_default_model_config",
        lambda db, purpose, fallback_to_general=True: RuntimeModelConfig(
            id=1,
            provider="qwen",
            model_name="gte-rerank-v2",
            purpose="rerank",
            endpoint=None,
            api_key="sk-test",
            extra_config={"top_n": 2},
        ),
    )
    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)

    results = ai_service.rerank_documents(query="极限", documents=["a", "b", "c"], db=object())
    # 下标 9 越界被过滤，按分数降序并截到 top_n=2
    assert results == [(2, 0.9), (0, 0.7)]


def test_rerank_documents_returns_none_without_config(monkeypatch):
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose, fallback_to_general=True: None)
    assert ai_service.rerank_documents(query="极限", documents=["a", "b", "c"], db=object()) is None


# —— 模型调用瞬时错误重试 ——

import httpx
import pytest


def _qa_config():
    return RuntimeModelConfig(
        id=1,
        provider="qwen",
        model_name="qwen-plus",
        purpose="qa",
        endpoint="https://example.com/v1",
        api_key="k",
        extra_config={},
    )


class _JsonResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {"choices": [{"message": {"content": "已恢复"}}]}
        self.text = text

    def json(self):
        return self._payload

    def close(self):
        pass


def test_call_chat_retries_transient_connect_error(monkeypatch):
    """非流式：连接抖动前两次失败，第三次成功——应重试并返回正常内容。"""
    monkeypatch.setattr("app.services.ai.time.sleep", lambda _s: None)
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose: _qa_config())
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            calls["n"] += 1
            if calls["n"] < 3:
                raise httpx.ConnectError("connection reset")
            return _JsonResponse()

    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)
    result = ai_service._call_chat_with_meta(None, purpose="qa", system_prompt="s", user_prompt="u")
    assert result is not None and result.content == "已恢复"
    assert calls["n"] == 3


def test_call_chat_retries_on_503_status(monkeypatch):
    """非流式：先返回 503(可重试状态)，重试后 200 成功。"""
    monkeypatch.setattr("app.services.ai.time.sleep", lambda _s: None)
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose: _qa_config())
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return _JsonResponse(status_code=503, text="overloaded")
            return _JsonResponse()

    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)
    result = ai_service._call_chat_with_meta(None, purpose="qa", system_prompt="s", user_prompt="u")
    assert result is not None and result.content == "已恢复"
    assert calls["n"] == 2


def test_call_chat_gives_up_after_max_retries(monkeypatch):
    """非流式：持续连接失败，重试耗尽后抛出(fallback 关闭时)。"""
    monkeypatch.setattr("app.services.ai.time.sleep", lambda _s: None)
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose: _qa_config())
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            calls["n"] += 1
            raise httpx.ConnectError("down")

    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)
    with pytest.raises(Exception):
        ai_service._call_chat_with_meta(None, purpose="qa", system_prompt="s", user_prompt="u")
    assert calls["n"] == ai_service._MODEL_RETRY_ATTEMPTS


class _FakeStream:
    def __init__(self, lines, status_code=200, content_type="text/event-stream"):
        self._lines = lines
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"error body"

    def iter_lines(self):
        yield from self._lines


def _sse_lines(*contents):
    out = []
    for c in contents:
        out.append('data: {"choices":[{"delta":{"content":"%s"}}]}' % c)
    out.append("data: [DONE]")
    return out


def test_stream_retries_before_first_delta(monkeypatch):
    """流式：首个 delta 产出前连接抖动，应重连并最终流出内容。"""
    monkeypatch.setattr("app.services.ai.time.sleep", lambda _s: None)
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose: _qa_config())
    monkeypatch.setattr(ai_service, "_generation_timeout", lambda db: 60.0)
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def stream(self, method, url, headers=None, json=None):
            calls["n"] += 1
            if calls["n"] < 2:
                raise httpx.ConnectError("reset before first token")
            return _FakeStream(_sse_lines("你好", "世界"))

    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)
    deltas = list(ai_service._stream_chat_with_meta(None, purpose="qa", system_prompt="s", user_prompt="u"))
    text = "".join(d.text for d in deltas if d.kind == "content")
    assert text == "你好世界"
    assert calls["n"] == 2


def test_stream_does_not_retry_after_emitting(monkeypatch):
    """流式：已产出内容后再断连，不能重连(否则重复输出)，应向上抛出。"""
    monkeypatch.setattr("app.services.ai.time.sleep", lambda _s: None)
    monkeypatch.setattr("app.services.ai.get_default_model_config", lambda db, purpose: _qa_config())
    monkeypatch.setattr(ai_service, "_generation_timeout", lambda db: 60.0)
    calls = {"n": 0}

    class _BreakingStream(_FakeStream):
        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"半句"}}]}'
            raise httpx.RemoteProtocolError("peer closed mid-stream")

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def stream(self, method, url, headers=None, json=None):
            calls["n"] += 1
            return _BreakingStream([])

    monkeypatch.setattr("app.services.ai.httpx.Client", FakeClient)
    got = []
    with pytest.raises(Exception):
        for d in ai_service._stream_chat_with_meta(None, purpose="qa", system_prompt="s", user_prompt="u"):
            got.append(d)
    # 只连了一次(未重连)，且把已产出的"半句"透传给了调用方
    assert calls["n"] == 1
    assert "".join(d.text for d in got if d.kind == "content") == "半句"


def test_log_ai_usage_never_propagates_on_write_failure(monkeypatch):
    """使用日志（分析用途）写失败绝不能拖垮已完成的主操作。

    复现线上事故：ai_usage_logs 表缺失时，出题任务在写使用日志处抛
    ProgrammingError，把已生成的 quiz 一起回滚（target_id=null、任务 failed）。
    修复后 log_ai_usage 在独立 session 写入并吞掉任何异常，绝不向调用方传播。
    """
    import app.db.session as db_session
    from app.services import usage as usage_mod

    def boom_session():
        raise RuntimeError("simulated: ai_usage_logs 写入路径失败（如表缺失）")

    monkeypatch.setattr(db_session, "SessionLocal", boom_session)
    # 不抛异常即通过（调用方主操作不受影响）
    usage_mod.log_ai_usage(
        db=None,
        module="quiz_generation",
        user_id=1,
        course_id=1,
        prompt_chars=24,
        completion_chars=364,
        success=True,
    )
