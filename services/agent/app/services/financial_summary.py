"""Aggregate structured data to provide financial summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional
from uuid import UUID

import unicodedata

from app.services.repositories import DocumentRepository


def format_currency(value: float) -> str:
    """Format numbers using Brazilian Real notation."""

    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class SummaryBucket:
    total: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)

    def add(self, key: str, amount: float) -> None:
        if amount is None:
            return
        self.total += amount
        self.breakdown[key] = self.breakdown.get(key, 0.0) + amount

    def to_dict(self) -> dict:
        return {"total": self.total, "breakdown": self.breakdown}


@dataclass
class FinancialSummary:
    revenues: SummaryBucket
    expenses: SummaryBucket
    mei_info: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "revenues": self.revenues.to_dict(),
            "expenses": self.expenses.to_dict(),
            "mei_info": self.mei_info,
        }

    @property
    def has_revenues(self) -> bool:
        return self.revenues.total > 0

    @property
    def has_expenses(self) -> bool:
        return self.expenses.total > 0

    @property
    def has_mei_details(self) -> bool:
        return bool(self.mei_info)


class FinancialSummaryBuilder:
    """Build aggregated financial data for a given user."""

    REVENUE_TYPES = {
        "NOTA_FISCAL_EMITIDA",
        "INFORME_RENDIMENTOS",
        "INFORME_BANCARIO",
        "DASN_SIMEI",
    }
    EXPENSE_TYPES = {
        "NOTA_FISCAL_RECEBIDA",
        "DESPESA_DEDUTIVEL",
    }

    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def build_summary(self, user_id: UUID) -> FinancialSummary:
        records = self._repository.list_completed_jobs(user_id)
        revenues = SummaryBucket()
        expenses = SummaryBucket()
        mei_info: Dict[str, float] = {}

        for record in records:
            document_type = (record.document_type or "").upper()
            extracted = record.extracted_data

            if document_type in self.REVENUE_TYPES:
                for value in self._extract_values(extracted):
                    revenues.add(document_type, value)

            if document_type in self.EXPENSE_TYPES:
                for value in self._extract_values(extracted):
                    expenses.add(document_type, value)

            if document_type == "DASN_SIMEI":
                mei_payload = self._extract_mei_payload(extracted)
                mei_info.update(mei_payload)
                if "lucro_tributavel" in mei_payload:
                    revenues.add("LUCRO_TRIBUTAVEL_DASN", mei_payload["lucro_tributavel"])

        return FinancialSummary(revenues=revenues, expenses=expenses, mei_info=mei_info)

    def _extract_values(self, payload: object) -> Iterable[float]:
        if payload is None:
            return []

        if isinstance(payload, list):
            values = []
            for item in payload:
                if isinstance(item, dict):
                    values.extend(self._extract_values(item))
            return values

        if isinstance(payload, dict):
            values = []
            for key, value in payload.items():
                normalized_key = _normalize_key(key)
                if any(fragment in normalized_key for fragment in ["valor", "total", "montante", "quantia"]):
                    amount = _coerce_amount(value)
                    if amount is not None:
                        values.append(amount)
            return values

        if isinstance(payload, (int, float)):
            return [float(payload)]

        if isinstance(payload, str):
            amount = _coerce_amount(payload)
            return [amount] if amount is not None else []

        return []

    def _extract_mei_payload(self, payload: object) -> Dict[str, float]:
        results: Dict[str, float] = {}
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = _normalize_key(key)
                if normalized_key in {"lucro_isento", "parcela_isenta"}:
                    amount = _coerce_amount(value)
                    if amount is not None:
                        results["lucro_isento"] = amount
                if normalized_key in {"lucro_tributavel", "lucro_tributavel_parcela"}:
                    amount = _coerce_amount(value)
                    if amount is not None:
                        results["lucro_tributavel"] = amount
        return results


def _normalize_key(key: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", key)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return normalized.replace(" ", "_")


def _coerce_amount(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("R$", "").replace(" ", "")
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None
