"""DTO describing the MEI monthly revenue summary for the dashboard."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from services.document_service.application.dto.annual_revenue_summary import (
    AnnualRevenueSourceBreakdown,
)


class MonthlyRevenueSummaryResponse(BaseModel):
    """Payload exibido no dashboard com o faturamento mensal consolidado."""

    mes: int = Field(description="Mês considerado no cálculo (1-12).")
    ano: int = Field(description="Ano considerado no cálculo.")
    faturamento_total: float = Field(
        description="Somatório das receitas consideradas para o faturamento mensal."
    )
    faturamento_total_formatado: str = Field(
        description="Somatório das receitas formatado em reais."
    )
    limite_mensal: float = Field(
        default=6750.0,
        description="Limite mensal utilizado para comparação (R$ 6.750,00).",
    )
    limite_mensal_formatado: str = Field(
        description="Limite mensal formatado em reais para exibição."
    )
    destaque: str = Field(
        description="Mensagem principal exibida no dashboard com o comparativo mensal."
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
