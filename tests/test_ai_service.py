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
