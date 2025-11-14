"""FastAPI dependencies for the Agent service."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.billing_client import BillingClient
from app.services.chat import AgentChatService
from app.services.embeddings import LocalEmbeddingClient
from app.services.financial_summary import FinancialSummaryBuilder
from app.services.repositories import (
    DocumentRepository,
    MongoDocumentRepository,
    RagChunkRepository,
)


@lru_cache
def get_chat_service() -> AgentChatService:
    embedder = LocalEmbeddingClient(dimension=settings.embedding_dimensions)
    document_repository = DocumentRepository(SessionLocal)
    rag_repository = RagChunkRepository(SessionLocal)
    summary_builder = FinancialSummaryBuilder(document_repository)
    mongo_repository = MongoDocumentRepository()
    billing_client = BillingClient(
        base_url=settings.billing_service_url,
        timeout=settings.billing_timeout_seconds,
    )

    return AgentChatService(
        rag_repository=rag_repository,
        summary_builder=summary_builder,
        embedder=embedder,
        mongo_repository=mongo_repository,
        top_k=settings.rag_top_k,
        billing_client=billing_client,
    )
