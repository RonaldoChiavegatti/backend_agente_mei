"""DTOs describing the MEI annual revenue summary for the dashboard."""
from __future__ import annotations

import uuid
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AnnualRevenueSourceBreakdown(BaseModel):
    """Amount grouped by the type of document that contributed to the revenue."""

    document_type: str = Field(description="Tipo de documento considerado no somatório.")
    label: str = Field(description="Rótulo amigável para o tipo de documento.")
    total: float = Field(description="Somatório dos valores identificados para o tipo.")
    total_formatado: str = Field(
        description="Somatório em reais formatado usando notação brasileira."
    )
    documentos: List[uuid.UUID] = Field(
        default_factory=list,
        description="Identificadores dos documentos que contribuíram para o tipo.",
    )
    quantidade_documentos: int = Field(
        description="Quantidade de documentos considerados para o tipo."
    )


class AnnualRevenueLimitAlert(BaseModel):
    """Alert information triggered when the annual revenue approaches the limit."""

    nivel: Literal["atencao", "critico"] = Field(
        description="Nível de severidade do alerta para exibição no dashboard.",
    )
    mensagem: str = Field(
        description="Mensagem explicando o motivo do alerta e a ação recomendada.",
    )
    percentual_utilizado: float = Field(
        description="Percentual do limite anual que já foi utilizado.",
    )
    percentual_utilizado_formatado: str = Field(
        description="Percentual utilizado formatado em porcentagem para exibição.",
    )


class AnnualRevenueSummaryResponse(BaseModel):
    """Payload exibido no dashboard com o faturamento anual consolidado."""

    ano: int = Field(description="Ano-calendário considerado no cálculo.")
    faturamento_total: float = Field(
        description="Somatório das receitas consideradas para o faturamento anual."
    )
    faturamento_total_formatado: str = Field(
        description="Somatório das receitas formatado em reais."
    )
    limite_anual: float = Field(
        default=81000.0,
        description="Limite anual do MEI utilizado para comparação (R$ 81.000,00).",
    )
    limite_anual_formatado: str = Field(
        description="Limite anual formatado em reais para exibição."
    )
    destaque: str = Field(
        description="Mensagem principal a ser exibida no dashboard com o comparativo."
    )
    detalhamento: Dict[str, AnnualRevenueSourceBreakdown] = Field(
        default_factory=dict,
        description="Quebra por tipo de documento das receitas consideradas.",
    )
    observacoes: List[str] = Field(
        default_factory=list,
        description="Observações adicionais para orientar o usuário.",
    )
    documentos_considerados: List[str] = Field(
        default_factory=list,
        description="Lista textual dos tipos de documentos incluídos no cálculo.",
    )
    alerta_limite: Optional[AnnualRevenueLimitAlert] = Field(
        default=None,
        description="Alerta exibido quando o faturamento se aproxima ou ultrapassa o limite anual.",
    )
