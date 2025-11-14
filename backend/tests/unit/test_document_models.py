import sys
import uuid
from datetime import date, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.models.base_models import DocumentType
from shared.models.document_models import (
    ClassificationPayload,
    ConfidenceBand,
    Currency,
    DocumentModel,
    DocumentNature,
    DocumentSource,
    DocumentStatus,
    LedgerEntryModel,
    LedgerOrigin,
    NormalizedPayload,
    OCRBlock,
    OCRPayload,
)


def _build_sample_document_kwargs():
    document_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.utcnow()

    return {
        "_id": document_id,
        "user_id": user_id,
        "filename": "NF_000123_2025-03-10.pdf",
        "mime_type": "application/pdf",
        "bucket_key": "uploads/2025/03/10/abc123.pdf",
        "source": DocumentSource.UPLOAD_WEB,
        "type": DocumentType.NOTA_FISCAL_EMITIDA,
        "status": DocumentStatus.PROCESSED,
        "ocr": OCRPayload(
            engine="tesseract-5.4.0",
            lang=["por"],
            pages=2,
            text="Texto completo concatenado...",
            blocks=[
                OCRBlock(page=1, text="R$ 1.500,00"),
            ],
        ),
        "classification": ClassificationPayload(
            model="doc-type-classifier@v1", type_confidence=0.93
        ),
        "extracted_data": {
            "numero_nf": "12345",
            "valor_total_nf": 1500.0,
        },
        "normalized": NormalizedPayload(
            nature=DocumentNature.RECEITA,
            total_valor=1500.0,
            moeda=Currency.BRL,
            data_competencia=date(2025, 3, 10),
            tags=["nf_emitida", "servico"],
            confidence=ConfidenceBand.MEDIUM,
        ),
        "created_at": now,
        "updated_at": now,
    }


def test_document_model_parses_specification_payload():
    payload = _build_sample_document_kwargs()

    document = DocumentModel(**payload)

    assert document.id == payload["_id"]
    assert document.status is DocumentStatus.PROCESSED
    assert document.normalized is not None
    assert document.normalized.nature is DocumentNature.RECEITA
    assert document.ocr is not None
    assert document.ocr.blocks[0].text == "R$ 1.500,00"


def test_normalized_payload_defaults_and_validation():
    normalized = NormalizedPayload(nature=DocumentNature.META)

    assert normalized.total_valor is None
    assert normalized.moeda is Currency.BRL
    assert normalized.tags == []
    assert normalized.confidence is None


def test_ledger_entry_model_round_trip():
    document_payload = _build_sample_document_kwargs()
    document = DocumentModel(**document_payload)

    entry = LedgerEntryModel(
        _id=uuid.uuid4(),
        user_id=document.user_id,
        document_id=document.id,
        type=document.type,
        nature=DocumentNature.RECEITA,
        categoria="servico",
        descricao="Serviço de manutenção - NF 12345",
        valor=1500.0,
        moeda=Currency.BRL,
        data_competencia=date(2025, 3, 10),
        origem=LedgerOrigin(field_path="extracted_data.itens[0].valor_total"),
        tags=["nf_emitida"],
        created_at=document.created_at,
        updated_at=document.updated_at,
    )

    assert entry.nature is DocumentNature.RECEITA
    assert entry.origem is not None
    assert entry.origem.field_path == "extracted_data.itens[0].valor_total"


def test_document_model_requires_valid_status():
    payload = _build_sample_document_kwargs()
    payload["status"] = "unknown"

    with pytest.raises(ValueError):
        DocumentModel(**payload)
