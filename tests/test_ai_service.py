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


def test_task_model_handles_retrieval_rewrite_and_scope_classification(monkeypatch):
    calls: list[dict] = []

    def fake_call_json(db, *, purpose, system_prompt, user_prompt, allow_fallback=True):
        calls.append({"purpose": purpose, "prompt": user_prompt})
        if "检索意图分类器" in system_prompt:
            return {"scope": "specific", "chapter_id": None, "confidence": 0.9, "reason": "具体算法问题"}
        return {"retrieval_query": "霍夫曼算法 前缀编码", "keywords": ["霍夫曼算法", "前缀编码"]}

    monkeypatch.setattr(ai_service, "_call_json", fake_call_json)

    rewritten = ai_service.rewrite_retrieval_query(question="帮我讲解霍夫曼算法", db=None)
    scope = ai_service.classify_qa_question_scope(
        question="帮我讲解霍夫曼算法",
        course_name="多媒体技术",
        chapters=[],
        db=None,
    )

    assert rewritten.startswith("霍夫曼算法 前缀编码")
    assert scope["scope"] == "specific"
    assert [call["purpose"] for call in calls] == ["task", "task"]
