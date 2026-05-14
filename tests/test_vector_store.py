from types import SimpleNamespace

import pytest

from app.services.vector_store import VectorStoreService


class FakeQdrantModels:
    @staticmethod
    def MatchValue(*, value):
        return SimpleNamespace(value=value)

    @staticmethod
    def FieldCondition(*, key, match):
        return SimpleNamespace(key=key, match=match)

    @staticmethod
    def Filter(*, must):
        return SimpleNamespace(must=must)


class FakeQdrantClient:
    def __init__(self, *, points):
        self.points = points
        self.query_call = None

    def query_points(self, **kwargs):
        self.query_call = kwargs
        return SimpleNamespace(points=self.points)


def _fake_qdrant_service(*, points, vector_max_distance=0.9):
    service = VectorStoreService.__new__(VectorStoreService)
    service.provider = "qdrant"
    service.settings = SimpleNamespace(vector_max_distance=vector_max_distance)
    service._qdrant_models = FakeQdrantModels
    service._client = FakeQdrantClient(points=points)
    return service


def test_qdrant_query_converts_score_to_existing_distance_contract():
    service = _fake_qdrant_service(points=[SimpleNamespace(payload={"chunk_id": 12}, score=0.82)])

    rows = service._qdrant_query(
        collection="classagent_course_1_db_d3",
        query_embedding=[0.1, 0.2, 0.3],
        filters=[{"course_id": 1}, {"chapter_id": 2}],
        limit=5,
    )

    assert rows == [(12, pytest.approx(0.18))]
    query_filter = service._client.query_call["query_filter"]
    assert [(condition.key, condition.match.value) for condition in query_filter.must] == [("course_id", 1), ("chapter_id", 2)]


def test_qdrant_query_keeps_existing_max_distance_threshold():
    service = _fake_qdrant_service(
        points=[
            SimpleNamespace(payload={"chunk_id": 1}, score=0.9),
            SimpleNamespace(payload={"chunk_id": 2}, score=0.2),
        ],
        vector_max_distance=0.5,
    )

    rows = service._qdrant_query(collection="collection", query_embedding=[0.1], filters=[], limit=5)

    assert rows == [(1, pytest.approx(0.1))]
