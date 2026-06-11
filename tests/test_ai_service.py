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
