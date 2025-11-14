"""DTOs describing the basic counters rendered in the dashboard."""
from typing import List

from pydantic import BaseModel, Field


class DashboardCounter(BaseModel):
    """Represents a single metric counter displayed in the dashboard."""

    key: str = Field(..., description="Identificador interno da métrica.")
    title: str = Field(..., description="Título amigável exibido no dashboard.")
    subtitle: str = Field(
        ..., description="Contexto adicional sobre o período considerado na métrica."
    )
    value: int = Field(..., description="Valor numérico calculado para a métrica.")


class DashboardBasicMetricsResponse(BaseModel):
    """Payload com os contadores básicos exibidos no dashboard."""

    reference_year: int = Field(
        ..., description="Ano utilizado como referência para as métricas de documentos."
    )
    reference_month: int = Field(
        ..., description="Mês utilizado como referência para as métricas mensais."
    )
    counters: List[DashboardCounter] = Field(
        default_factory=list,
        description="Coleção de contadores calculados para o dashboard.",
    )
