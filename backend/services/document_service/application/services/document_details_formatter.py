"""Utilities to translate stored extraction payloads into API-friendly responses."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional

from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
)
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)


_DOCUMENT_LABELS: Dict[DocumentType, str] = {
    DocumentType.NOTA_FISCAL_EMITIDA: "Nota Fiscal emitida",
    DocumentType.NOTA_FISCAL_RECEBIDA: "Nota Fiscal recebida",
    DocumentType.INFORME_BANCARIO: "Informe bancário",
    DocumentType.INFORME_RENDIMENTOS: "Informe de rendimentos",
    DocumentType.DESPESA_DEDUTIVEL: "Documento de despesa dedutível",
    DocumentType.DASN_SIMEI: "DASN-SIMEI",
    DocumentType.RECIBO_IR_ANTERIOR: "Recibo do IR",
    DocumentType.DOC_IDENTIFICACAO: "Documento de identificação",
    DocumentType.COMPROVANTE_ENDERECO: "Comprovante de endereço",
}

_SOURCE_GROUP: Dict[DocumentType, str] = {
    DocumentType.NOTA_FISCAL_EMITIDA: "nota_fiscal",
    DocumentType.NOTA_FISCAL_RECEBIDA: "nota_fiscal",
    DocumentType.INFORME_BANCARIO: "informes_financeiros",
    DocumentType.INFORME_RENDIMENTOS: "informes_financeiros",
    DocumentType.DESPESA_DEDUTIVEL: "despesas_dedutiveis",
    DocumentType.DASN_SIMEI: "dasn_simei",
}

_SOURCE_GROUP_LABEL: Dict[DocumentType, str] = {
    DocumentType.NOTA_FISCAL_EMITIDA: "Notas Fiscais",
    DocumentType.NOTA_FISCAL_RECEBIDA: "Notas Fiscais",
    DocumentType.INFORME_BANCARIO: "Informes bancários",
    DocumentType.INFORME_RENDIMENTOS: "Informes de rendimentos",
    DocumentType.DESPESA_DEDUTIVEL: "Documentos de despesas dedutíveis",
    DocumentType.DASN_SIMEI: "DASN-SIMEI",
}

_DEFAULT_CATEGORY: Dict[DocumentType, str] = {
    DocumentType.NOTA_FISCAL_EMITIDA: "faturamento MEI",
    DocumentType.NOTA_FISCAL_RECEBIDA: "despesa operacional",
    DocumentType.INFORME_BANCARIO: "rendimento bancário",
    DocumentType.INFORME_RENDIMENTOS: "rendimento bancário",
    DocumentType.DESPESA_DEDUTIVEL: "despesa dedutível",
    DocumentType.DASN_SIMEI: "lucro MEI",
}

_DEFAULT_NATURE: Dict[DocumentType, str] = {
    DocumentType.NOTA_FISCAL_EMITIDA: "receita",
    DocumentType.INFORME_BANCARIO: "receita",
    DocumentType.INFORME_RENDIMENTOS: "receita",
    DocumentType.DASN_SIMEI: "receita",
    DocumentType.NOTA_FISCAL_RECEBIDA: "despesa",
    DocumentType.DESPESA_DEDUTIVEL: "despesa",
}

_VALUE_KEYS = (
    "valor",
    "value",
    "valor_total",
    "amount",
    "valor_bruto",
    "total",
)
_DATE_KEYS = (
    "data",
    "date",
    "data_competencia",
    "competencia",
    "data_emissao",
    "periodo",
)
_NATURE_KEYS = ("natureza", "tipo_natureza")
_CATEGORY_KEYS = ("categoria", "category", "tipo", "tipo_documento")
_CNPJ_KEYS = ("cnpj_emitente", "cnpj", "cnpj_origem")

_DASN_CURRENCY_FIELDS: Dict[str, str] = {
    "lucro_isento": "Lucro isento",
    "lucro_isento_mei": "Lucro isento",
    "lucro_tributavel": "Lucro tributável",
    "lucro_tributavel_mei": "Lucro tributável",
    "receita_bruta_total": "Receita bruta total",
}
_DASN_TEXT_FIELDS: Dict[str, str] = {
    "ano_calendario": "Ano-calendário",
    "periodo_apuracao": "Período de apuração",
}


def build_document_details(job: DocumentJob) -> DocumentDetailsResponse:
    """Create a :class:`DocumentDetailsResponse` from a persisted job."""

    entry = _extract_primary_entry(job.extracted_data)

    value = _parse_float(_extract_first(entry, _VALUE_KEYS))
    value_formatted = _format_currency(value)

    parsed_date = _parse_date(_extract_first(entry, _DATE_KEYS))
    iso_date = parsed_date.isoformat() if parsed_date else None
    pretty_date = parsed_date.strftime("%d/%m/%Y") if parsed_date else None

    nature = _extract_first(entry, _NATURE_KEYS)
    if isinstance(nature, str):
        nature = nature.strip().lower() or None
    nature = nature or _DEFAULT_NATURE.get(job.document_type)

    category = _extract_first(entry, _CATEGORY_KEYS)
    if isinstance(category, str):
        category = category.strip() or None
    category = category or _DEFAULT_CATEGORY.get(job.document_type)

    document_label = _DOCUMENT_LABELS.get(
        job.document_type, _titleize(job.document_type.value)
    )
    source_group = _SOURCE_GROUP.get(job.document_type, "documentos_auxiliares")
    source_group_label = _SOURCE_GROUP_LABEL.get(
        job.document_type, "Documentos auxiliares"
    )
    origem_legivel = f"Informações extraídas de {source_group_label}"

    extras: Dict[str, Dict[str, Optional[str]]] = {}

    if job.document_type == DocumentType.DASN_SIMEI:
        extras.update(_extract_dasn_fields(entry))

    cnpj = _extract_first(entry, _CNPJ_KEYS)
    if cnpj:
        extras.setdefault(
            "cnpj_emitente",
            {"label": "CNPJ", "valor": str(cnpj), "valor_formatado": str(cnpj)},
        )

    resumo = _build_summary(
        job.document_type,
        document_label,
        pretty_date,
        nature,
        value_formatted,
        extras,
    )

    raw_payload = job.extracted_data if isinstance(job.extracted_data, dict) else None

    return DocumentDetailsResponse(
        id=job.id,
        document_type=job.document_type,
        document_label=document_label,
        status=job.status,
        source_group=source_group,
        source_group_label=source_group_label,
        origem_legivel=origem_legivel,
        valor=value,
        valor_formatado=value_formatted,
        data=iso_date,
        data_formatada=pretty_date,
        natureza=nature,
        categoria=category,
        resumo=resumo,
        extras=extras,
        raw_extracted_data=raw_payload,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _extract_primary_entry(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        if "entries" in payload and isinstance(payload["entries"], Iterable):
            for item in payload["entries"]:
                if isinstance(item, dict):
                    return item
        return payload
    if isinstance(payload, Iterable) and not isinstance(payload, (str, bytes)):
        for item in payload:
            if isinstance(item, dict):
                return item
    return {}


def _extract_first(data: Dict[str, Any], keys: Iterable[str]) -> Any:
    lower_map = {str(key).lower(): key for key in data.keys()}
    for key in keys:
        if key in data:
            return data[key]
        lowered = key.lower()
        for existing_key in lower_map:
            if existing_key == lowered:
                original_key = lower_map[existing_key]
                return data[original_key]
    for existing_key, value in data.items():
        if existing_key.lower() in {k.lower() for k in keys}:
            return value
    return None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("R$", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif cleaned.count(".") > 1 and "," not in cleaned:
            parts = cleaned.split(".")
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _format_currency(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
    return None


def _extract_dasn_fields(entry: Dict[str, Any]) -> Dict[str, Dict[str, Optional[str]]]:
    extras: Dict[str, Dict[str, Optional[str]]] = {}

    for key, label in _DASN_CURRENCY_FIELDS.items():
        raw_value = _extract_first(entry, (key,))
        value = _parse_float(raw_value)
        extras[key] = {
            "label": label,
            "valor": None if value is None else f"{value}",
            "valor_formatado": _format_currency(value),
        }

    for key, label in _DASN_TEXT_FIELDS.items():
        raw_value = _extract_first(entry, (key,))
        if raw_value is not None:
            extras[key] = {
                "label": label,
                "valor": str(raw_value),
                "valor_formatado": str(raw_value),
            }

    filtered: Dict[str, Dict[str, Optional[str]]] = {}
    for key, values in extras.items():
        has_content = any(
            values.get(field)
            for field in ("valor", "valor_formatado")
            if field in values
        )
        if has_content:
            filtered[key] = values

    return filtered


def _build_summary(
    document_type: DocumentType,
    document_label: str,
    pretty_date: Optional[str],
    nature: Optional[str],
    value_formatted: Optional[str],
    extras: Dict[str, Dict[str, Optional[str]]],
) -> Optional[str]:
    base = document_label
    if pretty_date:
        base = f"{base} em {pretty_date}"

    if document_type == DocumentType.DASN_SIMEI:
        details = []
        isento = extras.get("lucro_isento") or extras.get("lucro_isento_mei")
        tributavel = extras.get("lucro_tributavel") or extras.get("lucro_tributavel_mei")
        if isento and isento.get("valor_formatado"):
            details.append(f"Lucro isento: {isento['valor_formatado']}")
        if tributavel and tributavel.get("valor_formatado"):
            details.append(f"Lucro tributável: {tributavel['valor_formatado']}")
        if details:
            if base:
                return f"{base} – {'; '.join(details)}"
            return "; ".join(details)
        return base or None

    if nature and value_formatted:
        detail = f"{nature.capitalize()}: {value_formatted}"
        return f"{base} – {detail}" if base else detail
    if value_formatted:
        detail = f"Valor: {value_formatted}"
        return f"{base} – {detail}" if base else detail
    return base or None


def _titleize(value: str) -> str:
    return value.replace("_", " ").title()
