"""Unit tests for :mod:`app.services.financial_summary`."""

from __future__ import annotations

import pathlib
import sys
import unittest
import uuid

TEST_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from app.services.financial_summary import FinancialSummaryBuilder
from app.services.repositories import DocumentRecord


class _StubDocumentRepository:
    def __init__(self, records):
        self.records = records
        self.received_user_id = None

    def list_completed_jobs(self, user_id):
        self.received_user_id = user_id
        return self.records


class FinancialSummaryBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()

    def test_aggregate_revenues_expenses_and_mei_details(self):
        records = [
            DocumentRecord(
                document_type="NOTA_FISCAL_EMITIDA",
                extracted_data=[{"valor": 1500.0}, {"valor": "500,00"}],
            ),
            DocumentRecord(
                document_type="DESPESA_DEDUTIVEL",
                extracted_data=[{"valor_total": "200,50"}],
            ),
            DocumentRecord(
                document_type="DASN_SIMEI",
                extracted_data={
                    "lucro_isento": "12.500,00",
                    "lucro_tributável": "3.500,75",
                },
            ),
        ]
        repository = _StubDocumentRepository(records)
        builder = FinancialSummaryBuilder(repository)

        summary = builder.build_summary(self.user_id)

        self.assertEqual(repository.received_user_id, self.user_id)
        self.assertAlmostEqual(summary.revenues.total, 1500.0 + 500.0 + 3500.75)
        self.assertAlmostEqual(summary.expenses.total, 200.50)
        self.assertEqual(summary.mei_info["lucro_isento"], 12500.0)
        self.assertAlmostEqual(summary.mei_info["lucro_tributavel"], 3500.75)
        self.assertIn("NOTA_FISCAL_EMITIDA", summary.revenues.breakdown)
        self.assertIn("DESPESA_DEDUTIVEL", summary.expenses.breakdown)

    def test_extracts_nested_amounts_in_complex_payloads(self):
        nested_payload = {
            "itens": [
                {"detalhes": {"valor_unitario": "100,00"}},
                {"parcelas": [{"montante": 200}]},
            ],
            "resumo": [
                {"valores": {"quantia": "50,00"}},
                {"subtotais": [{"total_liquido": 25}]},
            ],
        }
        records = [
            DocumentRecord(
                document_type="NOTA_FISCAL_EMITIDA",
                extracted_data=nested_payload,
            )
        ]
        repository = _StubDocumentRepository(records)
        builder = FinancialSummaryBuilder(repository)

        summary = builder.build_summary(self.user_id)

        expected_amount = 100.0 + 200.0 + 50.0 + 25.0
        self.assertAlmostEqual(summary.revenues.total, expected_amount)
        self.assertEqual(
            summary.revenues.breakdown["NOTA_FISCAL_EMITIDA"], expected_amount
        )

    def test_extract_values_from_nested_payloads(self):
        records = [
            DocumentRecord(
                document_type="NOTA_FISCAL_EMITIDA",
                extracted_data={
                    "dados": {
                        "itens": [
                            {"detalhes": {"valor": "1.200,00"}},
                            {"detalhes": {"montante": 300}},
                            {"detalhes": {"valores": ["150,25", 50]}},
                        ],
                        "resumo": {"subtotal": {"quantia_liquida": "99,75"}},
                    }
                },
            )
        ]
        repository = _StubDocumentRepository(records)
        builder = FinancialSummaryBuilder(repository)

        summary = builder.build_summary(self.user_id)

        expected_total = 1200.0 + 300.0 + 150.25 + 50.0 + 99.75
        self.assertAlmostEqual(summary.revenues.total, expected_total)
        self.assertEqual(summary.expenses.total, 0.0)
        self.assertIn("NOTA_FISCAL_EMITIDA", summary.revenues.breakdown)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
