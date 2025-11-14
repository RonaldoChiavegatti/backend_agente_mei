"""Repositories used to access structured and unstructured data sources."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, List, Optional
from uuid import UUID

from bson import ObjectId
from pymongo import MongoClient
from sqlalchemy import Select, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import UserRagChunk
if TYPE_CHECKING:  # pragma: no cover
    from app.services.corrections import CorrectionResult


@dataclass
class DocumentRecord:
    """Structured document representation retrieved from PostgreSQL."""

    document_type: str
    extracted_data: object


@dataclass
class RagChunk:
    """Chunk retrieved from the vector store."""

    id: str
    source: str
    source_id: str
    content: str
    score: float
    metadata: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata or {},
        }


@dataclass
class MongoDocument:
    """Representation of a MongoDB document chunk."""

    document_id: str
    document_type: Optional[str]
    extracted_text: str
    extracted_data: object | None = None
    extracted_data_history: List[dict] = field(default_factory=list)
    updated_at: Optional[datetime] = None


class DocumentRepository:
    """Access structured financial data extracted from documents."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def list_completed_jobs(self, user_id: UUID) -> List[DocumentRecord]:
        statement = text(
            """
            SELECT document_type::text AS document_type, extracted_data
            FROM document_processing_jobs
            WHERE user_id = :user_id
              AND status::text = 'concluido'
            """
        )

        with contextlib.closing(self._session_factory()) as session:
            rows = session.execute(statement, {"user_id": str(user_id)}).mappings()
            return [
                DocumentRecord(
                    document_type=row["document_type"],
                    extracted_data=row["extracted_data"],
                )
                for row in rows
            ]


class RagChunkRepository:
    """Access user chunk embeddings stored in PostgreSQL."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def find_similar(
        self, user_id: UUID, embedding: List[float], limit: int
    ) -> List[RagChunk]:
        with contextlib.closing(self._session_factory()) as session:
            statement: Select = (
                select(
                    UserRagChunk,
                    UserRagChunk.embedding.cosine_distance(embedding).label(
                        "distance"
                    ),
                )
                .where(UserRagChunk.user_id == user_id)
                .order_by(UserRagChunk.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            rows = session.execute(statement).all()

            chunks: List[RagChunk] = []
            for record, distance in rows:
                similarity = 1.0 - float(distance or 0.0)
                chunks.append(
                    RagChunk(
                        id=str(record.id),
                        source=record.source,
                        source_id=record.source_id,
                        content=record.content,
                        score=similarity,
                        metadata=record.chunk_metadata,
                    )
                )
            return chunks

    def upsert_chunks(
        self,
        session: Session,
        user_id: UUID,
        source: str,
        payloads: Iterable[tuple[str, str, List[float], Optional[dict]]],
    ) -> None:
        for source_id, content, embedding, metadata in payloads:
            stmt = (
                insert(UserRagChunk)
                .values(
                    user_id=user_id,
                    source=source,
                    source_id=source_id,
                    content=content,
                    embedding=embedding,
                    metadata=metadata,
                )
                .on_conflict_do_update(
                    constraint="uq_rag_chunks_source",
                    set_={
                        "content": content,
                        "embedding": embedding,
                        "metadata": metadata,
                    },
                )
            )
            session.execute(stmt)


class MongoDocumentRepository:
    """Access OCR text stored in MongoDB."""

    def __init__(self) -> None:
        self._url = settings.mongo_url
        self._db_name = settings.mongo_db
        self._collection = settings.mongo_collection_documents

    def fetch_recent_documents(
        self, user_id: UUID, limit: int = 5
    ) -> List[MongoDocument]:
        client = MongoClient(self._url)
        try:
            collection = client[self._db_name][self._collection]
            cursor = (
                collection.find(
                    {
                        "user_id": str(user_id),
                        "extracted_text": {"$ne": None},
                    }
                )
                .sort("updated_at", -1)
                .limit(limit)
            )
            documents: List[MongoDocument] = []
            for doc in cursor:
                documents.append(
                    MongoDocument(
                        document_id=str(doc.get("_id")),
                        document_type=doc.get("document_type"),
                        extracted_text=doc.get("extracted_text", ""),
                        extracted_data=doc.get("extracted_data"),
                        extracted_data_history=doc.get(
                            "extracted_data_history", []
                        ),
                        updated_at=doc.get("updated_at"),
                    )
                )
            return documents
        finally:
            client.close()

    def find_latest_by_type(
        self, user_id: UUID, document_type: str
    ) -> MongoDocument | None:
        client = MongoClient(self._url)
        try:
            collection = client[self._db_name][self._collection]
            query = {"document_type": document_type}
            if user_id is not None:
                query["user_id"] = str(user_id)

            cursor = collection.find(query).sort("updated_at", -1).limit(1)
            doc = next(cursor, None)
            if not doc:
                return None

            return MongoDocument(
                document_id=str(doc.get("_id")),
                document_type=doc.get("document_type"),
                extracted_text=doc.get("extracted_text", ""),
                extracted_data=doc.get("extracted_data"),
                extracted_data_history=doc.get("extracted_data_history", []),
                updated_at=doc.get("updated_at"),
            )
        finally:
            client.close()

    def apply_correction(
        self,
        *,
        user_id: UUID,
        document_id: str,
        field: str,
        new_value,
    ) -> "CorrectionResult | None":
        client = MongoClient(self._url)
        try:
            collection = client[self._db_name][self._collection]
            try:
                object_id = ObjectId(document_id)
            except Exception:
                return None

            query = {"_id": object_id}
            if user_id is not None:
                query["user_id"] = str(user_id)

            document = collection.find_one(query)
            if not document:
                return None

            extracted_data = document.get("extracted_data") or {}
            if not isinstance(extracted_data, dict):
                extracted_data = {"value": extracted_data}

            previous_value = extracted_data.get(field)
            updated_data = dict(extracted_data)
            updated_data[field] = new_value

            history: list[dict] = document.get("extracted_data_history", [])
            version_number = len(history) + 1
            now = datetime.utcnow()

            version_entry = {
                "version": version_number,
                "author_type": "user",
                "author_id": str(user_id),
                "created_at": now,
                "data_snapshot": updated_data,
                "changes": [
                    {
                        "field_path": field,
                        "previous_value": previous_value,
                        "current_value": new_value,
                    }
                ],
            }

            collection.update_one(
                query,
                {
                    "$set": {
                        "extracted_data": updated_data,
                        "updated_at": now,
                    },
                    "$push": {"extracted_data_history": version_entry},
                },
            )

            from app.services.corrections import CorrectionResult

            return CorrectionResult(
                document_id=str(document.get("_id")),
                document_type=document.get("document_type"),
                field=field,
                previous_value=previous_value,
                current_value=new_value,
                version=version_number,
                data_snapshot=updated_data,
            )
        finally:
            client.close()
