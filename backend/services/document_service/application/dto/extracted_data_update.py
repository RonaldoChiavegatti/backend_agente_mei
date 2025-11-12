"""DTO for manual corrections of extracted payloads."""
from typing import Any, Dict

from pydantic import BaseModel, Field


class ExtractedDataUpdateRequest(BaseModel):
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Novo payload completo corrigido pelo usuário.",
    )
