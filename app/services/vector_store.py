from __future__ import annotations

import json
import re
from hashlib import sha1
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import KnowledgeChunk, LessonPage
from app.services.ai import ai_service


class VectorStoreService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.persist_dir = Path(self.settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _db_key(self, db: Session) -> str:
        database_url = db.get_bind().url.render_as_string(hide_password=True)
        return sha1(database_url.encode("utf-8")).hexdigest()[:10]

    def _collection_prefix(self, db: Session, course_id: int) -> str:
        raw = f"course_{course_id}_{self._db_key(db)}"
        return re.sub(r"[^A-Za-z0-9_-]", "_", raw)[:120]

    def _collection_name(self, db: Session, course_id: int, dimension: int | None = None) -> str:
        prefix = self._collection_prefix(db, course_id)
        if dimension is None:
            return prefix
        return f"{prefix[:112]}_d{dimension}"

    def _collection(self, db: Session, course_id: int, dimension: int):
        return self._client.get_or_create_collection(
            name=self._collection_name(db, course_id, dimension),
            metadata={"hnsw:space": "cosine", "embedding_dimension": int(dimension)},
        )

    def _course_collection_names(self, db: Session, course_id: int) -> list[str]:
        prefix = self._collection_prefix(db, course_id)
        names: list[str] = []
        try:
            collections = self._client.list_collections()
        except Exception:
            return names
        for collection in collections:
            name = getattr(collection, "name", str(collection))
            if name == prefix or name.startswith(f"{prefix}_d"):
                names.append(name)
        return names

    def _collection_count(self, collection) -> int:
        try:
            return int(collection.count())
        except Exception:
            return 0

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

    def _upsert_precomputed(
        self,
        db: Session,
        *,
        chunks: list[KnowledgeChunk],
        embeddings: list[list[float]],
        collection,
    ) -> None:
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
            self._client.delete_collection(name=collection.name)
            collection = self._collection(db, chunks[0].course_id, dimension)
            self._upsert_precomputed(db, chunks=chunks, embeddings=embeddings, collection=collection)

    def _db_collection_names(self, db: Session) -> list[str]:
        db_key = self._db_key(db)
        names: list[str] = []
        try:
            collections = self._client.list_collections()
        except Exception:
            return names
        pattern = re.compile(rf"^course_\d+_{re.escape(db_key)}(?:_d\d+)?$")
        for collection in collections:
            name = getattr(collection, "name", str(collection))
            if pattern.fullmatch(name):
                names.append(name)
        return names

    def indexed_chunk_count(self, db: Session, *, course_id: int | None = None) -> int:
        names = self._course_collection_names(db, course_id) if course_id is not None else self._db_collection_names(db)
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
        return len(seen_ids)

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
            self._client.delete_collection(name=collection.name)
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


vector_store = VectorStoreService()
