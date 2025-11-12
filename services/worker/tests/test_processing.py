import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.processing import build_structured_data  # noqa: E402


@pytest.mark.parametrize(
    "document_type,nature",
    [
        ("NOTA_FISCAL_EMITIDA", "receita"),
        ("NOTA_FISCAL_RECEBIDA", "despesa"),
        ("DESPESA_DEDUTIVEL", "despesa"),
    ],
)
def test_build_structured_data_for_financial_documents(document_type, nature):
    text = (
        "Documento de teste - Valor total R$ 1.500,00 com data 10/03/2025 "
        "CNPJ 12.345.678/0001-00"
    )

    data = build_structured_data(text, document_type)

    assert isinstance(data, list)
    assert data[0]["natureza"] == nature
    assert data[0]["valor"] == pytest.approx(1500.0, 0.01)
    assert data[0]["data_competencia"] == "2025-03-10"
    assert data[0]["cnpj_emitente"] == "12.345.678/0001-00"
    assert data[0]["origem"] is not None


def test_build_structured_data_for_metadata_documents():
    text = "Documento de identidade do usuário ABC"

    data = build_structured_data(text, "DOC_IDENTIFICACAO")

    assert isinstance(data, dict)
    assert "metadata" in data
    assert data["metadata"]["document_type"] == "DOC_IDENTIFICACAO"
    assert "text_excerpt" in data["metadata"]
