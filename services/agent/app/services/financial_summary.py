"""Aggregate structured data to provide financial summaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional
from uuid import UUID

import re
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

        values: list[float] = []
        target_fragments = ("valor", "total", "montante", "quantia")

        def has_target(text: Optional[str]) -> bool:
            if not text:
                return False
            return any(fragment in text for fragment in target_fragments)

        def is_container(node: object) -> bool:
            if isinstance(node, Mapping):
                return True
            if isinstance(node, set):
                return True
            return isinstance(node, Sequence) and not isinstance(
                node, (str, bytes, bytearray)
            )

        def visit(node: object, has_target_context: bool = False) -> None:
            if node is None:
                return

            if isinstance(node, Mapping):
                for key, value in node.items():
                    normalized_key = _normalize_key(str(key))
                    key_matches = has_target(normalized_key)
                    active_context = normalized_key if key_matches else context_key

                    if not isinstance(value, (dict, list, tuple, set)):
                        should_use_value = False

                        if key_matches:
                            should_use_value = not _is_identifier_like(
                                normalized_key, value
                            )
                        elif active_context is not None and has_target(active_context):
                            should_use_value = not _is_identifier_like(
                                normalized_key, value
                            )

                        if should_use_value:
                            amount = _coerce_amount(value)
                            if amount is not None:
                                values.append(amount)
                        continue

                    if key_matches or next_context:
                        amount = _coerce_amount(value)
                        if amount is not None:
                            values.append(amount)
                return

            if isinstance(node, set) or (
                isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray))
            ):
                for item in node:
                    if is_container(item):
                        visit(item, has_target_context)
                        continue

                    amount = _coerce_amount(item)
                    if amount is not None and (
                        context_key is None
                        or (
                            has_target(context_key)
                            and not _is_identifier_like(None, item)
                        )
                    ):
                    if amount is not None and has_target_context:
                        values.append(amount)
                return

            amount = _coerce_amount(node)
            if amount is not None and (
                context_key is None
                or (
                    has_target(context_key)
                    and not _is_identifier_like(None, node)
                )
            ):
            if amount is not None and has_target_context:
                values.append(amount)

        visit(payload)
        if not values:
            fallback_amount = _coerce_amount(payload)
            if fallback_amount is not None:
                values.append(fallback_amount)
        return values

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


def _contains_token(text: str, token: str) -> bool:
    """Return True if the token appears as a whole word within the text."""

    pattern = rf"(?:^|[^a-z0-9]){re.escape(token)}(?:[^a-z0-9]|$)"
    return re.search(pattern, text) is not None


def _is_identifier_like(key: Optional[str], value: object) -> bool:
    """Heuristics to detect metadata fields that should not be treated as amounts."""

    if key:
        normalized_key = key.lower()
        substring_exclusions = {
            "chave",
            "metadata",
            "metadado",
            "identificador",
            "identificacao",
            "codigo",
            "cod",
            "numero",
            "num",
        }

        if any(fragment in normalized_key for fragment in substring_exclusions):
            return True

        if _contains_token(normalized_key, "id"):
            return True

    if isinstance(value, str):
        digits_only = value.strip().replace(" ", "")
        if digits_only.isdigit() and len(digits_only) >= 8:
            return True

    return False
