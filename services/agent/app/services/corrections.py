"""Utilities to interpret chat corrections and describe the result."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.services.financial_summary import format_currency


@dataclass
class CorrectionCommand:
    """Structured representation of a correction request extracted from text."""

    document_type: str
    field: str
    value: Any
    value_text: str
    value_kind: str  # "currency", "date", "text"
    intent: str


@dataclass
class CorrectionResult:
    """Summary of the mutation applied to a MongoDB document."""

    document_id: str
    document_type: Optional[str]
    field: str
    previous_value: Any
    current_value: Any
    version: int
    data_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "field": self.field,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "version": self.version,
            "data_snapshot": self.data_snapshot,
        }


class CorrectionParser:
    """Extract actionable correction intents from a natural language message."""

    _CATEGORY_KEYWORDS = {
        "saude": "saúde",
        "educacao": "educação",
        "educacional": "educação",
        "transporte": "transporte",
        "alimentacao": "alimentação",
        "moradia": "moradia",
        "odontologico": "odontológica",
        "medico": "saúde",
        "medica": "saúde",
        "medicina": "saúde",
    }

    _DOCUMENT_LABELS = {
        "NOTA_FISCAL_EMITIDA": "nota fiscal emitida",
        "NOTA_FISCAL_RECEBIDA": "nota fiscal recebida",
        "DESPESA_DEDUTIVEL": "despesa dedutível",
        "DASN_SIMEI": "declaração DASN-SIMEI",
    }

    def parse(self, message: str) -> Optional[CorrectionCommand]:
        normalized = _normalize_text(message)
        if not normalized:
            return None

        document_type = self._detect_document_type(normalized)
        if not document_type:
            return None

        category = self._extract_category(normalized)
        if category:
            return CorrectionCommand(
                document_type=document_type,
                field="categoria",
                value=category,
                value_text=category,
                value_kind="text",
                intent="update_category",
            )

        if document_type == "DASN_SIMEI":
            lucro_field = self._detect_lucro_field(normalized)
            amount = _extract_currency(normalized)
            if lucro_field and amount is not None:
                value, value_text = amount
                return CorrectionCommand(
                    document_type=document_type,
                    field=lucro_field,
                    value=value,
                    value_text=value_text,
                    value_kind="currency",
                    intent="update_value",
                )
            return None

        date_value = _extract_date(normalized)
        if date_value:
            iso_value, pretty_text = date_value
            return CorrectionCommand(
                document_type=document_type,
                field="data",
                value=iso_value,
                value_text=pretty_text,
                value_kind="date",
                intent="update_date",
            )

        amount = _extract_currency(normalized)
        if amount is not None:
            value, value_text = amount
            target_field = "valor"
            if document_type == "DESPESA_DEDUTIVEL":
                target_field = "valor"
            return CorrectionCommand(
                document_type=document_type,
                field=target_field,
                value=value,
                value_text=value_text,
                value_kind="currency",
                intent="update_value",
            )

        nature = self._extract_nature(normalized)
        if nature:
            return CorrectionCommand(
                document_type=document_type,
                field="natureza",
                value=nature,
                value_text=nature,
                value_kind="text",
                intent="update_nature",
            )

        return None

    def describe(self, command: CorrectionCommand) -> str:
        """Return a human friendly label for the command."""

        doc_label = self._DOCUMENT_LABELS.get(command.document_type, "documento")
        field_label = _FIELD_LABELS.get(command.field, command.field)

        if command.value_kind == "currency":
            formatted_value = format_currency(float(command.value))
        elif command.value_kind == "date":
            formatted_value = command.value_text
        else:
            formatted_value = command.value_text

        return f"{doc_label} – {field_label}: {formatted_value}"

    def document_label(self, document_type: str) -> str:
        return self._DOCUMENT_LABELS.get(document_type, "documento")

    def field_label(self, field: str) -> str:
        return _FIELD_LABELS.get(field, field)

    def _detect_document_type(self, normalized: str) -> Optional[str]:
        if "dasn" in normalized or "lucro" in normalized:
            return "DASN_SIMEI"
        if "despesa dedut" in normalized or "dedutivel" in normalized:
            return "DESPESA_DEDUTIVEL"
        if "despesa" in normalized and "nota" not in normalized:
            return "DESPESA_DEDUTIVEL"
        if "nota" in normalized or "nf" in normalized:
            if "recebid" in normalized or "compra" in normalized or "fornecedor" in normalized:
                return "NOTA_FISCAL_RECEBIDA"
            if "despesa" in normalized:
                return "NOTA_FISCAL_RECEBIDA"
            return "NOTA_FISCAL_EMITIDA"
        if "receita" in normalized:
            return "NOTA_FISCAL_EMITIDA"
        return None

    def _extract_category(self, normalized: str) -> Optional[str]:
        for keyword, label in self._CATEGORY_KEYWORDS.items():
            if keyword in normalized:
                if "nao " in normalized and f"nao {keyword}" in normalized:
                    continue
                return label
        if "categoria" in normalized:
            after = normalized.split("categoria", 1)[1].strip()
            match = re.search(r"(saude|educacao|transporte|alimentacao|moradia)", after)
            if match:
                keyword = match.group(1)
                return self._CATEGORY_KEYWORDS.get(keyword, keyword)
        return None

    def _extract_nature(self, normalized: str) -> Optional[str]:
        if "receita" in normalized and "nao" not in normalized:
            return "receita"
        if "despesa" in normalized:
            if "nao e" in normalized and "despesa" in normalized.split("nao e", 1)[0]:
                return None
            return "despesa"
        return None

    def _detect_lucro_field(self, normalized: str) -> Optional[str]:
        if "tribut" in normalized:
            return "lucro_tributavel"
        if "isento" in normalized:
            return "lucro_isento"
        if "bruto" in normalized:
            return "receita_bruta_total"
        return None


_FIELD_LABELS = {
    "valor": "valor",
    "data": "data",
    "natureza": "natureza",
    "categoria": "categoria",
    "lucro_tributavel": "lucro tributável",
    "lucro_isento": "lucro isento",
    "receita_bruta_total": "receita bruta total",
}


def _normalize_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    normalized = unicodedata.normalize("NFKD", stripped)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _extract_currency(normalized: str) -> Optional[tuple[float, str]]:
    match = re.search(r"r?\$?\s*(\d{1,3}(?:[\.\s]\d{3})*,\d{2}|\d+[\.,]\d+|\d+)", normalized)
    if not match:
        return None
    raw_value = match.group(1)
    cleaned = raw_value.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        numeric = float(cleaned)
    except ValueError:
        return None
    pretty = raw_value
    if not pretty.startswith("R$"):
        pretty = f"R$ {raw_value}" if "," in raw_value else f"R$ {raw_value},00"
    return numeric, pretty


def _extract_date(normalized: str) -> Optional[tuple[str, str]]:
    match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", normalized)
    if not match:
        return None
    raw = match.group(1).replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.date().isoformat(), parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


__all__ = [
    "CorrectionCommand",
    "CorrectionParser",
    "CorrectionResult",
]
