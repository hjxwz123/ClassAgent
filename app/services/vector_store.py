from __future__ import annotations

import json
import re
from hashlib import sha1
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import KnowledgeChunk
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

    def _collection_name(self, db: Session, course_id: int) -> str:
        raw = f"course_{course_id}_{self._db_key(db)}"
        return re.sub(r"[^A-Za-z0-9_-]", "_", raw)[:120]

    def _collection(self, db: Session, course_id: int):
        return self._client.get_or_create_collection(
            name=self._collection_name(db, course_id),
            metadata={"hnsw:space": "cosine"},
        )

    def delete_material(self, db: Session, *, course_id: int, material_id: int) -> None:
        try:
            collection = self._client.get_collection(name=self._collection_name(db, course_id))
            collection.delete(where={"material_id": int(material_id)})
        except Exception:
            # Vector cleanup is best-effort. The relational database remains the
            # source of truth, so a stale or read-only vector store must not block
            # material deletion.
            return

    def upsert_chunks(self, db: Session, *, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        embeddings = ai_service.embed_texts(db, [chunk.content for chunk in chunks])
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding
            ids.append(f"chunk_{chunk.id}")
            documents.append(chunk.content)
            metadatas.append(
                {
                    "chunk_id": int(chunk.id),
                    "course_id": int(chunk.course_id),
                    "material_id": int(chunk.material_id or 0),
                    "lesson_page_id": int(chunk.lesson_page_id or 0),
                    "chapter_id": int(chunk.chapter_id or 0),
                    "title": chunk.title,
                    "source_meta": json.dumps(chunk.source_meta or {}, ensure_ascii=False),
                }
            )
            db.add(chunk)
        collection = self._collection(db, chunks[0].course_id)
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query_course(
        self,
        db: Session,
        *,
        course_id: int,
        query: str,
        chapter_id: int | None = None,
        lesson_page_id: int | None = None,
        limit: int | None = None,
    ) -> list[tuple[int, float | None]]:
        collection = self._collection(db, course_id)
        filters: list[dict] = []
        if chapter_id is not None:
            filters.append({"chapter_id": int(chapter_id)})
        if lesson_page_id is not None:
            filters.append({"lesson_page_id": int(lesson_page_id)})
        where = None
        if len(filters) == 1:
            where = filters[0]
        elif len(filters) > 1:
            where = {"$and": filters}
        embeddings = ai_service.embed_texts(db, [query])
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
