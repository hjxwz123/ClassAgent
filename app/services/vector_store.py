from __future__ import annotations

import json
import re
from hashlib import sha1
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import KnowledgeChunk, LessonPage
from app.services.ai import ai_service


class VectorStoreService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = str(self.settings.vector_store_provider or "chroma").lower()
        self.persist_dir: Path | None = None
        self._qdrant_models: Any | None = None
        if self.provider == "qdrant":
            self._init_qdrant()
        else:
            self.provider = "chroma"
            self._init_chroma()

    def _init_chroma(self) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.persist_dir = Path(self.settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _init_qdrant(self) -> None:
        try:
            from qdrant_client import QdrantClient, models
        except ImportError as exc:
            raise RuntimeError("启用 Qdrant 向量库需要安装 qdrant-client 依赖") from exc

        self._qdrant_models = models
        qdrant_url = str(self.settings.qdrant_url or "").strip()
        if qdrant_url.startswith("local:"):
            path = qdrant_url.removeprefix("local:").strip() or "storage/vectors/qdrant"
            self._client = QdrantClient(path=path, timeout=self.settings.qdrant_timeout_seconds)
            return
        self._client = QdrantClient(
            url=qdrant_url,
            api_key=self.settings.qdrant_api_key or None,
            timeout=self.settings.qdrant_timeout_seconds,
        )

    @property
    def provider_label(self) -> str:
        return "Qdrant" if self.provider == "qdrant" else "Chroma"

    def is_available(self) -> bool:
        if self.provider == "qdrant":
            self._client.get_collections()
            return True
        return bool(self.persist_dir and self.persist_dir.exists())

    def _db_key(self, db: Session) -> str:
        database_url = db.get_bind().url.render_as_string(hide_password=True)
        return sha1(database_url.encode("utf-8")).hexdigest()[:10]

    def _namespace(self) -> str:
        if self.provider != "qdrant":
            return ""
        return re.sub(r"[^A-Za-z0-9_-]", "_", self.settings.qdrant_collection_prefix).strip("_")[:32]

    def _collection_prefix(self, db: Session, course_id: int) -> str:
        base = f"course_{course_id}_{self._db_key(db)}"
        namespace = self._namespace()
        raw = f"{namespace}_{base}" if namespace else base
        return re.sub(r"[^A-Za-z0-9_-]", "_", raw)[:120]

    def _collection_name(self, db: Session, course_id: int, dimension: int | None = None) -> str:
        prefix = self._collection_prefix(db, course_id)
        if dimension is None:
            return prefix
        return f"{prefix[:112]}_d{dimension}"

    def _collection(self, db: Session, course_id: int, dimension: int):
        if self.provider == "qdrant":
            return self._qdrant_collection(db, course_id, dimension)
        return self._client.get_or_create_collection(
            name=self._collection_name(db, course_id, dimension),
            metadata={"hnsw:space": "cosine", "embedding_dimension": int(dimension)},
        )

    def _qdrant_collection(self, db: Session, course_id: int, dimension: int) -> str:
        name = self._collection_name(db, course_id, dimension)
        if self._qdrant_collection_exists(name):
            return name
        models = self._qdrant_models
        try:
            self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=int(dimension), distance=models.Distance.COSINE),
            )
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise
        self._ensure_qdrant_payload_indexes(name)
        return name

    def _qdrant_collection_exists(self, name: str) -> bool:
        try:
            return bool(self._client.collection_exists(collection_name=name))
        except AttributeError:
            try:
                self._client.get_collection(collection_name=name)
                return True
            except Exception:
                return False

    def _ensure_qdrant_payload_indexes(self, name: str) -> None:
        models = self._qdrant_models
        schema = getattr(models.PayloadSchemaType, "INTEGER", "integer")
        for field in ("chunk_id", "course_id", "material_id", "lesson_page_id", "lesson_id", "chapter_id"):
            try:
                self._client.create_payload_index(collection_name=name, field_name=field, field_schema=schema)
            except Exception:
                continue

    def _list_collection_names(self) -> list[str]:
        if self.provider == "qdrant":
            response = self._client.get_collections()
            collections = getattr(response, "collections", response)
        else:
            collections = self._client.list_collections()
        return [str(getattr(collection, "name", collection)) for collection in collections]

    def _course_collection_names(self, db: Session, course_id: int) -> list[str]:
        prefix = self._collection_prefix(db, course_id)
        try:
            names = self._list_collection_names()
        except Exception:
            return []
        return [name for name in names if name == prefix or name.startswith(f"{prefix}_d")]

    def _collection_count(self, collection) -> int:
        try:
            if self.provider == "qdrant":
                return int(self._client.count(collection_name=collection, exact=True).count)
            return int(collection.count())
        except Exception:
            return 0

    def _delete_collection(self, collection) -> None:
        if self.provider == "qdrant":
            self._client.delete_collection(collection_name=collection)
            return
        self._client.delete_collection(name=collection.name)

    def _embedding_dimension(self, embeddings: list[list[float]], *, expected_dimension: int | None = None) -> int:
        if not embeddings or not embeddings[0]:
            return 0
        dimension = len(embeddings[0])
        if expected_dimension is not None and dimension != expected_dimension:
            raise RuntimeError(f"Embedding dimension mismatch: expected {expected_dimension}, got {dimension}")
        for embedding in embeddings:
            if len(embedding) != dimension:
                raise RuntimeError("Embedding dimension mismatch inside batch")
        return dimension

    def _chunk_metadata(self, db: Session, *, chunks: list[KnowledgeChunk]) -> tuple[list[str], list[str], list[dict]]:
        page_ids = [int(chunk.lesson_page_id) for chunk in chunks if chunk.lesson_page_id]
        lesson_ids_by_page: dict[int, int] = {}
        if page_ids:
            lesson_ids_by_page = {
                int(page_id): int(lesson_id)
                for page_id, lesson_id in db.execute(select(LessonPage.id, LessonPage.lesson_id).where(LessonPage.id.in_(page_ids)))
            }
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        for chunk in chunks:
            source_meta = dict(chunk.source_meta or {})
            lesson_id = int(source_meta.get("lesson_id") or lesson_ids_by_page.get(int(chunk.lesson_page_id or 0), 0) or 0)
            ids.append(f"chunk_{chunk.id}")
            documents.append(chunk.content)
            metadatas.append(
                {
                    "chunk_id": int(chunk.id),
                    "course_id": int(chunk.course_id),
                    "material_id": int(chunk.material_id or 0),
                    "lesson_page_id": int(chunk.lesson_page_id or 0),
                    "lesson_id": lesson_id,
                    "chapter_id": int(chunk.chapter_id or 0),
                    "title": chunk.title,
                    "source_meta": json.dumps(source_meta, ensure_ascii=False),
                }
            )
        return ids, documents, metadatas

    def _upsert_precomputed(
        self,
        db: Session,
        *,
        chunks: list[KnowledgeChunk],
        embeddings: list[list[float]],
        collection,
    ) -> None:
        ids, documents, metadatas = self._chunk_metadata(db, chunks=chunks)
        if self.provider == "qdrant":
            models = self._qdrant_models
            points = [
                models.PointStruct(id=int(chunk.id), vector=embeddings[index], payload={**metadatas[index], "document": documents[index]})
                for index, chunk in enumerate(chunks)
            ]
            self._client.upsert(collection_name=collection, points=points, wait=True)
            return
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def _rebuild_course_collection(self, db: Session, *, course_id: int, collection, dimension: int) -> None:
        chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id)))
        if not chunks:
            return
        batch_size = 48
        for index in range(0, len(chunks), batch_size):
            batch = chunks[index : index + batch_size]
            embeddings = ai_service.embed_texts(db, [chunk.content for chunk in batch])
            if not embeddings:
                continue
            self._embedding_dimension(embeddings, expected_dimension=dimension)
            self._upsert_precomputed(db, chunks=batch, embeddings=embeddings, collection=collection)

    def _ensure_course_collection(self, db: Session, *, course_id: int, dimension: int):
        collection = self._collection(db, course_id, dimension)
        if self._collection_count(collection) == 0:
            self._rebuild_course_collection(db, course_id=course_id, collection=collection, dimension=dimension)
        return collection

    def delete_material(self, db: Session, *, course_id: int, material_id: int) -> None:
        # Vector cleanup is best-effort. The relational database remains the
        # source of truth, so a stale or read-only vector store must not block
        # material deletion.
        for name in self._course_collection_names(db, course_id):
            try:
                if self.provider == "qdrant":
                    models = self._qdrant_models
                    self._client.delete(
                        collection_name=name,
                        points_selector=models.FilterSelector(
                            filter=models.Filter(
                                must=[models.FieldCondition(key="material_id", match=models.MatchValue(value=int(material_id)))]
                            )
                        ),
                        wait=True,
                    )
                else:
                    collection = self._client.get_collection(name=name)
                    collection.delete(where={"material_id": int(material_id)})
            except Exception:
                continue

    def upsert_chunks(self, db: Session, *, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        embeddings = ai_service.embed_texts(db, [chunk.content for chunk in chunks])
        if not embeddings or not embeddings[0]:
            return
        dimension = self._embedding_dimension(embeddings)
        collection = self._collection(db, chunks[0].course_id, dimension)
        try:
            self._upsert_precomputed(db, chunks=chunks, embeddings=embeddings, collection=collection)
        except Exception as exc:
            if "dimension" not in str(exc).lower():
                raise
            self._delete_collection(collection)
            collection = self._collection(db, chunks[0].course_id, dimension)
            self._upsert_precomputed(db, chunks=chunks, embeddings=embeddings, collection=collection)

    def _db_collection_names(self, db: Session) -> list[str]:
        db_key = self._db_key(db)
        try:
            names = self._list_collection_names()
        except Exception:
            return []
        namespace = self._namespace()
        prefix = f"{re.escape(namespace)}_" if namespace else ""
        pattern = re.compile(rf"^{prefix}course_\d+_{re.escape(db_key)}(?:_d\d+)?$")
        return [name for name in names if pattern.fullmatch(name)]

    def indexed_chunk_ids(self, db: Session, *, course_id: int | None = None) -> set[int]:
        names = self._course_collection_names(db, course_id) if course_id is not None else self._db_collection_names(db)
        if self.provider == "qdrant":
            return self._qdrant_indexed_chunk_ids(names)
        seen_ids: set[str] = set()
        for name in names:
            try:
                collection = self._client.get_collection(name=name)
            except Exception:
                continue
            offset = 0
            page_size = 1000
            while True:
                try:
                    batch = collection.get(limit=page_size, offset=offset, include=[])
                except Exception:
                    try:
                        batch = collection.get(limit=page_size, offset=offset)
                    except Exception:
                        break
                ids = batch.get("ids") or []
                if not ids:
                    break
                seen_ids.update(str(item) for item in ids)
                if len(ids) < page_size:
                    break
                offset += len(ids)
        chunk_ids: set[int] = set()
        for item in seen_ids:
            if not item.startswith("chunk_"):
                continue
            try:
                chunk_ids.add(int(item.removeprefix("chunk_")))
            except ValueError:
                continue
        return chunk_ids

    def _qdrant_indexed_chunk_ids(self, names: list[str]) -> set[int]:
        chunk_ids: set[int] = set()
        for name in names:
            offset = None
            page_size = 1000
            while True:
                try:
                    points, offset = self._client.scroll(
                        collection_name=name,
                        limit=page_size,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )
                except Exception:
                    break
                if not points:
                    break
                for point in points:
                    payload = dict(getattr(point, "payload", None) or {})
                    raw_id = payload.get("chunk_id", getattr(point, "id", None))
                    try:
                        chunk_ids.add(int(raw_id))
                    except (TypeError, ValueError):
                        continue
                if offset is None:
                    break
        return chunk_ids

    def indexed_chunk_count(self, db: Session, *, course_id: int | None = None) -> int:
        return len(self.indexed_chunk_ids(db, course_id=course_id))

    def query_course(
        self,
        db: Session,
        *,
        course_id: int,
        query: str,
        chapter_id: int | None = None,
        lesson_id: int | None = None,
        lesson_page_id: int | None = None,
        limit: int | None = None,
    ) -> list[tuple[int, float | None]]:
        embeddings = ai_service.embed_texts(db, [query])
        if not embeddings or not embeddings[0]:
            return []
        dimension = len(embeddings[0])
        collection = self._ensure_course_collection(db, course_id=course_id, dimension=dimension)
        filters: list[dict] = []
        if chapter_id is not None:
            filters.append({"chapter_id": int(chapter_id)})
        if lesson_id is not None:
            filters.append({"lesson_id": int(lesson_id)})
        if lesson_page_id is not None:
            filters.append({"lesson_page_id": int(lesson_page_id)})
        if self.provider == "qdrant":
            return self._qdrant_query(
                collection=collection,
                query_embedding=embeddings[0],
                filters=filters,
                limit=limit or self.settings.vector_query_limit,
            )
        where = None
        if len(filters) == 1:
            where = filters[0]
        elif len(filters) > 1:
            where = {"$and": filters}
        try:
            result = collection.query(
                query_embeddings=embeddings,
                n_results=limit or self.settings.vector_query_limit,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:
            if "dimension" not in str(exc).lower():
                raise
            self._delete_collection(collection)
            collection = self._ensure_course_collection(db, course_id=course_id, dimension=dimension)
            result = collection.query(
                query_embeddings=embeddings,
                n_results=limit or self.settings.vector_query_limit,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        rows: list[tuple[int, float | None]] = []
        for index, metadata in enumerate(metadatas):
            if not metadata:
                continue
            distance = float(distances[index]) if index < len(distances) and distances[index] is not None else None
            if distance is not None and distance > self.settings.vector_max_distance:
                continue
            rows.append((int(metadata["chunk_id"]), distance))
        return rows

    def _qdrant_filter(self, filters: list[dict]):
        if not filters:
            return None
        models = self._qdrant_models
        conditions = [
            models.FieldCondition(key=str(key), match=models.MatchValue(value=int(value)))
            for item in filters
            for key, value in item.items()
        ]
        return models.Filter(must=conditions)

    def _qdrant_query(
        self,
        *,
        collection: str,
        query_embedding: list[float],
        filters: list[dict],
        limit: int,
    ) -> list[tuple[int, float | None]]:
        query_filter = self._qdrant_filter(filters)
        if hasattr(self._client, "query_points"):
            result = self._client.query_points(
                collection_name=collection,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            points = getattr(result, "points", result)
        else:
            points = self._client.search(
                collection_name=collection,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        rows: list[tuple[int, float | None]] = []
        for point in points:
            payload = dict(getattr(point, "payload", None) or {})
            raw_id = payload.get("chunk_id", getattr(point, "id", None))
            try:
                chunk_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            score = getattr(point, "score", None)
            distance = None if score is None else 1.0 - float(score)
            if distance is not None and distance > self.settings.vector_max_distance:
                continue
            rows.append((chunk_id, distance))
        return rows


vector_store = VectorStoreService()
