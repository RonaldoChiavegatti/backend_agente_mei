"""Pydantic DTOs for detailed document extraction responses."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.document_service.application.domain.document_job import (
    DocumentType,
    ProcessingStatus,
)


class ExtractedDataChangeResponse(BaseModel):
    field_path: str
    previous_value: Any = None
    current_value: Any = None


class ExtractedDataVersionResponse(BaseModel):
    version: int
    author_type: str
    created_at: datetime
    author_id: Optional[uuid.UUID] = None
    data_snapshot: Dict[str, Any] = Field(default_factory=dict)
    changes: List[ExtractedDataChangeResponse] = Field(default_factory=list)


class DocumentDetailsResponse(BaseModel):
    """Structured response representing extracted data for a processed document."""

    id: uuid.UUID
    document_type: DocumentType
    document_label: str
    status: ProcessingStatus
    source_group: str = Field(
        description="Slug que agrupa a origem dos dados (ex.: nota_fiscal, informes_financeiros)."
    )
    source_group_label: str = Field(
        description="Nome legível da origem principal dos dados extraídos."
    )
    origem_legivel: str = Field(
        description="Mensagem legível indicando de qual tipo de documento vieram os dados."
    )
    valor: Optional[float] = Field(
        default=None, description="Valor monetário identificado no documento."
    )
    valor_formatado: Optional[str] = Field(
        default=None, description="Valor monetário formatado em reais."
    )
    data: Optional[str] = Field(
        default=None, description="Data relevante do documento em formato ISO (AAAA-MM-DD)."
    )
    data_formatada: Optional[str] = Field(
        default=None, description="Data relevante do documento formatada (DD/MM/AAAA)."
    )
    natureza: Optional[str] = Field(
        default=None, description="Natureza financeira (receita ou despesa)."
    )
    categoria: Optional[str] = Field(
        default=None,
        description="Categoria resumida, como 'faturamento MEI' ou 'rendimento bancário'.",
    )
    resumo: Optional[str] = Field(
        default=None,
        description="Resumo legível combinando tipo de documento, data e valores extraídos.",
    )
    extras: Dict[str, Dict[str, Optional[str]]] = Field(
        default_factory=dict,
        description="Campos adicionais relevantes para o documento (ex.: lucro isento).",
    )
    raw_extracted_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Payload bruto recebido do processo de extração para depuração.",
    )
    history: List[ExtractedDataVersionResponse] = Field(
        default_factory=list,
        description="Histórico de versões manuais ou automáticas do payload extraído.",
    )
    created_at: datetime
    updated_at: datetime
