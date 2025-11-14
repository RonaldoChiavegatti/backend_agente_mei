"""Database models used by the Agent service."""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

try:  # pragma: no cover - optional dependency for tests
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:  # pragma: no cover - fallback for local unit tests
    from sqlalchemy.types import TypeDecorator

    class Vector(TypeDecorator):  # type: ignore[misc]
        """Fallback column type storing vectors as JSON when pgvector is absent."""

        impl = JSONB
        cache_ok = True

        def process_bind_param(self, value, dialect):  # pragma: no cover
            return value

        def process_result_value(self, value, dialect):  # pragma: no cover
            return value

from app.core.config import settings
from app.db.session import Base


class UserRagChunk(Base):
    """Chunk of text indexed for retrieval augmented generation."""

    __tablename__ = "user_rag_chunks"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source", "source_id", name="uq_rag_chunks_source"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions)
    )
    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
