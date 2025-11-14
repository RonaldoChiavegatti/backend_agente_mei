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
from app.services.corrections import CorrectionResult
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


class _CorrectionMongoRepository:
    def __init__(self, documents_by_type):
        self.documents = documents_by_type
        self.correction_calls = []

    def fetch_recent_documents(self, user_id, limit=5):  # pragma: no cover - unused
        return []

    def find_latest_by_type(self, user_id, document_type):
        payload = self.documents.get(document_type)
        if not payload:
            return None
        return MongoDocument(
            document_id=payload["id"],
            document_type=document_type,
            extracted_text=payload.get("text", ""),
            extracted_data=payload.get("data"),
        )

    def apply_correction(self, user_id, document_id, field, new_value):
        for doc_type, payload in self.documents.items():
            if payload["id"] != document_id:
                continue
            data = payload.setdefault("data", {})
            previous = data.get(field)
            data[field] = new_value
            payload["version"] = payload.get("version", 0) + 1
            result = CorrectionResult(
                document_id=document_id,
                document_type=doc_type,
                field=field,
                previous_value=previous,
                current_value=new_value,
                version=payload["version"],
                data_snapshot=dict(data),
            )
            self.correction_calls.append(
                (user_id, doc_type, document_id, field, new_value)
            )
            return result
        return None


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

    def test_updates_expense_value_via_correction(self):
        empty_summary = FinancialSummary(
            revenues=SummaryBucket(total=0.0, breakdown={}),
            expenses=SummaryBucket(total=0.0, breakdown={}),
            mei_info={},
        )
        summary_builder = _StubSummaryBuilder(empty_summary)
        rag_repo = _StubRagRepository([])
        mongo_repo = _CorrectionMongoRepository(
            {
                "DESPESA_DEDUTIVEL": {
                    "id": "expense-1",
                    "data": {"valor": 200.0, "categoria": "educação"},
                }
            }
        )

        service = AgentChatService(
            rag_repository=rag_repo,
            summary_builder=summary_builder,
            embedder=self.embedder,
            mongo_repository=mongo_repo,
            top_k=3,
        )

        answer, debug = service.answer_question(
            self.user_id, "Corrija a despesa dedutível para R$ 300,00"
        )

        self.assertIn("Atualizei", answer)
        self.assertIn("R$ 300,00", answer)
        self.assertTrue(debug["correction"]["applied"])
        self.assertEqual(debug["correction"]["current_value"], 300.0)
        self.assertEqual(
            mongo_repo.documents["DESPESA_DEDUTIVEL"]["data"]["valor"], 300.0
        )
        self.assertEqual(summary_builder.calls, [])

    def test_updates_lucro_tributavel_in_dasn(self):
        empty_summary = FinancialSummary(
            revenues=SummaryBucket(total=0.0, breakdown={}),
            expenses=SummaryBucket(total=0.0, breakdown={}),
            mei_info={},
        )
        summary_builder = _StubSummaryBuilder(empty_summary)
        rag_repo = _StubRagRepository([])
        mongo_repo = _CorrectionMongoRepository(
            {
                "DASN_SIMEI": {
                    "id": "dasn-1",
                    "data": {"lucro_tributavel": 12000.0, "lucro_isento": 8000.0},
                }
            }
        )

        service = AgentChatService(
            rag_repository=rag_repo,
            summary_builder=summary_builder,
            embedder=self.embedder,
            mongo_repository=mongo_repo,
            top_k=3,
        )

        answer, debug = service.answer_question(
            self.user_id, "Atualize o lucro tributável para R$ 15.500,00"
        )

        self.assertIn("lucro tributável", answer)
        self.assertTrue(debug["correction"]["applied"])
        self.assertEqual(debug["correction"]["current_value"], 15500.0)
        self.assertEqual(
            mongo_repo.documents["DASN_SIMEI"]["data"]["lucro_tributavel"], 15500.0
        )

    def test_reclassifies_note_to_health_expense(self):
        empty_summary = FinancialSummary(
            revenues=SummaryBucket(total=0.0, breakdown={}),
            expenses=SummaryBucket(total=0.0, breakdown={}),
            mei_info={},
        )
        summary_builder = _StubSummaryBuilder(empty_summary)
        rag_repo = _StubRagRepository([])
        mongo_repo = _CorrectionMongoRepository(
            {
                "NOTA_FISCAL_RECEBIDA": {
                    "id": "nf-1",
                    "data": {"categoria": "educação"},
                }
            }
        )

        service = AgentChatService(
            rag_repository=rag_repo,
            summary_builder=summary_builder,
            embedder=self.embedder,
            mongo_repository=mongo_repo,
            top_k=3,
        )

        answer, debug = service.answer_question(
            self.user_id,
            "Essa nota é despesa de saúde, não de educação",
        )

        self.assertIn("saúde", answer)
        self.assertTrue(debug["correction"]["applied"])
        self.assertEqual(
            mongo_repo.documents["NOTA_FISCAL_RECEBIDA"]["data"]["categoria"],
            "saúde",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
