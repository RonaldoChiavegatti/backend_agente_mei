"""Helpers for extracting text and financial data from documents."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:  # pragma: no cover - optional dependency guards
    import pytesseract
except ImportError as import_error:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    _PYTESSERACT_IMPORT_ERROR = import_error
else:  # pragma: no cover
    _PYTESSERACT_IMPORT_ERROR = None

try:  # pragma: no cover
    from pdf2image import convert_from_bytes
except ImportError as import_error:  # pragma: no cover
    convert_from_bytes = None  # type: ignore[assignment]
    _PDF2IMAGE_IMPORT_ERROR = import_error
else:  # pragma: no cover
    _PDF2IMAGE_IMPORT_ERROR = None

try:  # pragma: no cover
    from PIL import Image
except ImportError as import_error:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    _PIL_IMPORT_ERROR = import_error
else:  # pragma: no cover
    _PIL_IMPORT_ERROR = None

logger = logging.getLogger(__name__)

_CURRENCY_REGEX = re.compile(
    r"(?:R\$)?\s*((?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{2}|\.\d{2}))(?![\d/])"
)
_DATE_REGEX = re.compile(r"(\d{2}/\d{2}/\d{4})")
_CNPJ_REGEX = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

_REVENUE_TYPES = {
    "NOTA_FISCAL_EMITIDA",
    "INFORME_BANCARIO",
    "INFORME_RENDIMENTOS",
    "DASN_SIMEI",
}

_EXPENSE_TYPES = {
    "NOTA_FISCAL_RECEBIDA",
    "DESPESA_DEDUTIVEL",
}

_ORIGIN_MAP = {
    "NOTA_FISCAL_EMITIDA": "nota",
    "NOTA_FISCAL_RECEBIDA": "nota",
    "INFORME_BANCARIO": "banco",
    "DESPESA_DEDUTIVEL": "despesa",
    "INFORME_RENDIMENTOS": "rendimentos",
    "DASN_SIMEI": "lucro_mei",
}


def extract_text_from_bytes(
    file_bytes: bytes, filename: str, language: str = "por"
) -> str:
    """Run OCR on the provided file using Tesseract."""

    if pytesseract is None or Image is None:
        raise RuntimeError(
            "Dependências do Tesseract não instaladas: "
            f"pytesseract={_PYTESSERACT_IMPORT_ERROR}, PIL={_PIL_IMPORT_ERROR}"
        )

    suffix = Path(filename).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        image = Image.open(BytesIO(file_bytes))
        return pytesseract.image_to_string(image, lang=language)

    if suffix == ".pdf":
        if convert_from_bytes is None:
            raise RuntimeError(
                "Conversão de PDF para imagem indisponível: "
                f"pdf2image={_PDF2IMAGE_IMPORT_ERROR}"
            )
        images = convert_from_bytes(file_bytes)
        text_segments = [
            pytesseract.image_to_string(image, lang=language)
            for image in images
        ]
        return "\n".join(segment.strip() for segment in text_segments if segment.strip())

    raise ValueError(f"Formato de arquivo não suportado para OCR: {suffix}")


def build_structured_data(
    text: str, document_type: Optional[str]
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Transform free text into structured financial data."""

    doc_type = (document_type or "").upper()
    nature = _determine_nature(doc_type)

    if nature is None:
        snippet = text.strip()
        if len(snippet) > 1000:
            snippet = snippet[:1000]
        return {
            "metadata": {
                "document_type": doc_type or "DESCONHECIDO",
                "text_excerpt": snippet,
            }
        }

    amount = _extract_amount(text)
    competence_date = _extract_date(text)
    cnpj = _extract_cnpj(text)

    entry: Dict[str, Any] = {
        "tipo_documento": doc_type,
        "natureza": nature,
        "origem": _ORIGIN_MAP.get(doc_type, "documento"),
        "valor": amount,
        "data_competencia": competence_date,
        "cnpj_emitente": cnpj,
    }

    return [entry]


def _determine_nature(document_type: str) -> Optional[str]:
    if document_type in _REVENUE_TYPES:
        return "receita"
    if document_type in _EXPENSE_TYPES:
        return "despesa"
    return None


def _extract_amount(text: str) -> Optional[float]:
    values: List[float] = []
    for match in _CURRENCY_REGEX.finditer(text):
        raw_value = match.group(1)
        parsed = _parse_currency(raw_value)
        if parsed is not None:
            values.append(parsed)

    if not values:
        return None

    return max(values)


def _parse_currency(raw_value: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d,\.]", "", raw_value)
    if not cleaned:
        return None

    # If we have both separators, assume Brazilian notation (thousand separator ".", decimal ",").
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(",") > 1 and "." not in cleaned:
        parts = cleaned.split(",")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    elif cleaned.count(".") > 1 and "," not in cleaned:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        logger.debug("Não foi possível converter o valor monetário: %s", raw_value)
        return None


def _extract_date(text: str) -> Optional[str]:
    for match in _DATE_REGEX.finditer(text):
        candidate = match.group(1)
        try:
            parsed = datetime.strptime(candidate, "%d/%m/%Y")
            return parsed.date().isoformat()
        except ValueError:
            continue
    return None


def _extract_cnpj(text: str) -> Optional[str]:
    match = _CNPJ_REGEX.search(text)
    if match:
        return match.group(0)
    return None
