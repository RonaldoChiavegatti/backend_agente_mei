"""Unit tests for the chat orchestration service."""

from __future__ import annotations

import pathlib
import sys
import unittest
import uuid

TEST_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from app.services.chat import AgentChatService
from app.services.embeddings import LocalEmbeddingClient
from app.services.financial_summary import FinancialSummary, SummaryBucket
from app.services.repositories import MongoDocument, RagChunk


class _StubRagRepository:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def find_similar(self, user_id, embedding, limit):
        self.calls.append((user_id, tuple(embedding), limit))
        return list(self.chunks)


class _StubSummaryBuilder:
    def __init__(self, summary):
        self.summary = summary
        self.calls = []

    def build_summary(self, user_id):
        self.calls.append(user_id)
        return self.summary


class _StubMongoRepository:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def fetch_recent_documents(self, user_id, limit=5):
        self.calls.append((user_id, limit))
        return list(self.documents)


class AgentChatServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.embedder = LocalEmbeddingClient(dimension=8)

    def test_compose_answer_with_financial_context(self):
        summary = FinancialSummary(
            revenues=SummaryBucket(
                total=2500.0,
                breakdown={
                    "NOTA_FISCAL_EMITIDA": 1500.0,
                    "INFORME_RENDIMENTOS": 1000.0,
                },
            ),
            expenses=SummaryBucket(total=700.0, breakdown={"DESPESA_DEDUTIVEL": 700.0}),
            mei_info={"lucro_isento": 5000.0, "lucro_tributavel": 1200.0},
        )

        rag_repo = _StubRagRepository(
            [
                RagChunk(
                    id="1",
                    source="user_rag_chunks",
                    source_id="chunk-1",
                    content="Resumo da nota fiscal emitida em janeiro",
                    score=0.9,
                    metadata={"document_type": "NOTA_FISCAL_EMITIDA"},
                )
            ]
        )
        summary_builder = _StubSummaryBuilder(summary)
        mongo_repo = _StubMongoRepository(
            [
                MongoDocument(
                    document_id="abc123",
                    document_type="NOTA_FISCAL_EMITIDA",
                    extracted_text="Venda de serviços no valor de R$ 1.500,00",
                )
            ]
        )

        service = AgentChatService(
            rag_repository=rag_repo,
            summary_builder=summary_builder,
            embedder=self.embedder,
            mongo_repository=mongo_repo,
            top_k=3,
        )

        answer, debug = service.answer_question(
            self.user_id, "Preciso pagar imposto adicional este mês?"
        )

        self.assertIn("Notas Fiscais emitidas", answer)
        self.assertIn("lucro tributável declarado na DASN-SIMEI", answer)
        self.assertIn("despesas dedutíveis", answer)
        self.assertIn("Pergunta original", answer)
        self.assertIn("Principais trechos considerados", answer)
        self.assertEqual(debug["financial_summary"]["revenues"]["total"], 2500.0)
        self.assertEqual(len(debug["chunks"]), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
