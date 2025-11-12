"""High level orchestration for answering user questions."""

from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from app.services.embeddings import LocalEmbeddingClient
from app.services.financial_summary import (
    FinancialSummary,
    FinancialSummaryBuilder,
    format_currency,
)
from app.services.repositories import (
    MongoDocumentRepository,
    RagChunk,
    RagChunkRepository,
)


class AgentChatService:
    """Coordinate retrieval, aggregation and response composition."""

    def __init__(
        self,
        rag_repository: RagChunkRepository,
        summary_builder: FinancialSummaryBuilder,
        embedder: LocalEmbeddingClient,
        mongo_repository: MongoDocumentRepository | None = None,
        top_k: int = 5,
    ) -> None:
        self._rag_repository = rag_repository
        self._summary_builder = summary_builder
        self._embedder = embedder
        self._mongo_repository = mongo_repository
        self._top_k = top_k

    def answer_question(self, user_id: UUID, question: str) -> Tuple[str, dict]:
        summary = self._summary_builder.build_summary(user_id)
        query_embedding = self._embedder.embed_query(question)
        chunks = self._rag_repository.find_similar(
            user_id=user_id, embedding=query_embedding, limit=self._top_k
        )

        if self._mongo_repository is not None:
            mongo_docs = self._mongo_repository.fetch_recent_documents(
                user_id, limit=self._top_k
            )
            if mongo_docs:
                for doc in mongo_docs:
                    if not doc.extracted_text:
                        continue
                    doc_embedding = self._embedder.embed_query(doc.extracted_text)
                    similarity = self._embedder.cosine_similarity(
                        query_embedding, doc_embedding
                    )
                    chunks.append(
                        RagChunk(
                            id=f"mongo::{doc.document_id}",
                            source="mongo_document",
                            source_id=doc.document_id,
                            content=doc.extracted_text,
                            score=similarity,
                            metadata={"document_type": doc.document_type},
                        )
                    )

        chunks.sort(key=lambda item: item.score, reverse=True)
        chunks = chunks[: self._top_k]

        answer = self._compose_answer(question, summary, chunks)
        debug_payload = {
            "question": question,
            "financial_summary": summary.to_dict(),
            "chunks": [chunk.to_dict() for chunk in chunks],
        }
        return answer, debug_payload

    def _compose_answer(
        self, question: str, summary: FinancialSummary, chunks: List[RagChunk]
    ) -> str:
        intro_segments: List[str] = []

        if summary.has_revenues:
            nf_total = summary.revenues.breakdown.get("NOTA_FISCAL_EMITIDA")
            rendimentos_total = summary.revenues.breakdown.get("INFORME_RENDIMENTOS")
            lucro_tributavel = summary.mei_info.get("lucro_tributavel")

            revenue_parts: List[str] = []
            if nf_total:
                revenue_parts.append(
                    f"suas Notas Fiscais emitidas ({format_currency(nf_total)})"
                )
            if rendimentos_total:
                revenue_parts.append(
                    f"seus informes de rendimentos ({format_currency(rendimentos_total)})"
                )
            if lucro_tributavel:
                revenue_parts.append(
                    f"o lucro tributável declarado na DASN-SIMEI ({format_currency(lucro_tributavel)})"
                )

            if revenue_parts:
                intro_segments.append(
                    "Com base em " + " e ".join(revenue_parts)
                )

        if summary.has_mei_details and "lucro_isento" in summary.mei_info:
            intro_segments.append(
                f"considerando também o lucro isento informado na DASN-SIMEI ({format_currency(summary.mei_info['lucro_isento'])})"
            )

        if summary.has_expenses:
            despesas_total = summary.expenses.total
            intro_segments.append(
                f"e nas suas despesas dedutíveis ({format_currency(despesas_total)})"
            )

        if not intro_segments:
            intro_text = (
                "Não localizei dados consolidados dos seus documentos. Ainda assim, segue uma orientação geral."
            )
        else:
            intro_text = ", ".join(intro_segments) + ", segue uma orientação personalizada."

        chunk_summaries: List[str] = []
        for chunk in chunks:
            excerpt = chunk.content.strip().replace("\n", " ")
            if len(excerpt) > 220:
                excerpt = excerpt[:217] + "..."
            chunk_summaries.append(f"[{chunk.source}] {excerpt}")

        if chunk_summaries:
            context_text = "Principais trechos considerados: " + " | ".join(
                chunk_summaries
            )
        else:
            context_text = "Não localizamos trechos específicos dos seus documentos com o perfil buscado."

        guidance = (
            "Analise se os valores acima estão coerentes com suas obrigações fiscais e, em caso de dúvida, considere registrar todas as despesas e receitas na plataforma ou consultar um contador."
        )

        return (
            f"{intro_text}\n\n"
            f"Pergunta original: {question}\n"
            f"{context_text}\n\n"
            f"Recomendação: {guidance}"
        )
