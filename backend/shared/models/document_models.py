"""Domain models shared across services for document storage and ledger data."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base_models import DocumentType


class DocumentStatus(str, Enum):
    """Processing lifecycle for a stored document."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class DocumentNature(str, Enum):
    """Financial impact of a document once normalised."""

    RECEITA = "receita"
    DESPESA = "despesa"
    META = "meta"


class Currency(str, Enum):
    """Supported monetary currencies."""

    BRL = "BRL"


class ConfidenceBand(str, Enum):
    """Confidence band used across OCR, parsing and normalisation stages."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DocumentSource(str, Enum):
    """Origin of the document inside the ingestion pipeline."""

    UPLOAD_WEB = "upload_web"
    UPLOAD_API = "upload_api"
    REPROCESS = "reprocess"
    CORRECTION = "correction"


class BoundingBox(BaseModel):
    """Bounding box coordinates for OCR extracted elements."""

    page: int = Field(ge=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=0)
    h: int = Field(ge=0)


class OCRBlock(BaseModel):
    """Single OCR block captured from a document page."""

    page: int = Field(ge=1)
    text: str
    bbox: Optional[BoundingBox] = None


class OCRQuality(BaseModel):
    """Metadata describing OCR quality metrics."""

    dpi: Optional[int] = Field(default=None, ge=0)
    skew: Optional[float] = None
    noise_score: Optional[float] = None


class OCRPayload(BaseModel):
    """Complete OCR payload persisted with the document."""

    engine: str
    lang: List[str] = Field(default_factory=list)
    pages: int = Field(ge=0)
    text: str
    blocks: List[OCRBlock] = Field(default_factory=list)
    quality: Optional[OCRQuality] = None


class ClassificationPayload(BaseModel):
    """Metadata about the automatic classification step."""

    model: str
    type_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    hints: List[str] = Field(default_factory=list)


class NormalizedPayload(BaseModel):
    """Normalised view consumed by downstream dashboards and ledgers."""

    nature: DocumentNature
    total_valor: Optional[float] = None
    moeda: Currency = Currency.BRL
    data_competencia: Optional[date] = None
    tags: List[str] = Field(default_factory=list)
    confidence: Optional[ConfidenceBand] = None


class VersionActorType(str, Enum):
    """Actor responsible for creating a new version."""

    SYSTEM = "system"
    USER = "user"


class VersionActor(BaseModel):
    """Identifies who created a document version."""

    type: VersionActorType
    user_id: Optional[uuid.UUID] = None


class DocumentVersion(BaseModel):
    """Tracks semantic updates on top of the extracted payload."""

    version: int = Field(ge=1)
    at: datetime
    by: VersionActor
    changes: Dict[str, Any] = Field(default_factory=dict)


class DocumentModel(BaseModel):
    """Represents a processed document stored in MongoDB."""

    id: uuid.UUID = Field(alias="_id")
    user_id: uuid.UUID

    filename: str
    mime_type: str
    bucket_key: str
    source: DocumentSource

    type: DocumentType
    status: DocumentStatus
    error: Optional[str] = None

    ocr: Optional[OCRPayload] = None
    classification: Optional[ClassificationPayload] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    normalized: Optional[NormalizedPayload] = None
    versions: List[DocumentVersion] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class LedgerOrigin(BaseModel):
    """Metadata that links ledger values back to the extracted payload."""

    field_path: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)


class LedgerEntryModel(BaseModel):
    """Normalised ledger entry consumed by dashboards."""

    id: uuid.UUID = Field(alias="_id")
    user_id: uuid.UUID
    document_id: uuid.UUID
    type: DocumentType
    nature: DocumentNature
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    valor: float
    moeda: Currency = Currency.BRL
    data_competencia: date
    origem: Optional[LedgerOrigin] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)
