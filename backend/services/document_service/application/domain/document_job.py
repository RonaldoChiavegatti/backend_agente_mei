import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    PENDING = "pendente"
    PROCESSING = "processando"
    COMPLETED = "concluido"
    FAILED = "falhou"


class DocumentType(str, Enum):
    NOTA_FISCAL_EMITIDA = "NOTA_FISCAL_EMITIDA"
    NOTA_FISCAL_RECEBIDA = "NOTA_FISCAL_RECEBIDA"
    INFORME_BANCARIO = "INFORME_BANCARIO"
    DESPESA_DEDUTIVEL = "DESPESA_DEDUTIVEL"
    INFORME_RENDIMENTOS = "INFORME_RENDIMENTOS"
    DASN_SIMEI = "DASN_SIMEI"
    RECIBO_IR_ANTERIOR = "RECIBO_IR_ANTERIOR"
    DOC_IDENTIFICACAO = "DOC_IDENTIFICACAO"
    COMPROVANTE_ENDERECO = "COMPROVANTE_ENDERECO"

class ExtractedDataAuthor(str, Enum):
    SYSTEM = "system"
    USER = "user"


class ExtractedDataChange(BaseModel):
    field_path: str
    previous_value: Any = None
    current_value: Any = None


class ExtractedDataVersion(BaseModel):
    version: int
    author_type: ExtractedDataAuthor
    created_at: datetime = Field(default_factory=datetime.utcnow)
    author_id: Optional[uuid.UUID] = None
    data_snapshot: Dict[str, Any] = Field(default_factory=dict)
    changes: List[ExtractedDataChange] = Field(default_factory=list)


def _flatten_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return {}
    return {"value": payload}


def _compute_changes(
    previous: Any, current: Any, prefix: str = ""
) -> List[ExtractedDataChange]:
    changes: List[ExtractedDataChange] = []

    if isinstance(previous, dict) and isinstance(current, dict):
        keys = set(previous.keys()) | set(current.keys())
        for key in sorted(keys):
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            prev_value = previous.get(key)
            curr_value = current.get(key)

            if isinstance(prev_value, dict) and isinstance(curr_value, dict):
                changes.extend(_compute_changes(prev_value, curr_value, next_prefix))
            elif prev_value != curr_value:
                changes.append(
                    ExtractedDataChange(
                        field_path=next_prefix,
                        previous_value=prev_value,
                        current_value=curr_value,
                    )
                )
        return changes

    if previous != current:
        changes.append(
            ExtractedDataChange(
                field_path=prefix or "__root__",
                previous_value=previous,
                current_value=current,
            )
        )

    return changes


class DocumentJob(BaseModel):
    """
    Represents the DocumentJob domain entity within the document service's bounded context.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    file_path: str  # Path in the object storage
    document_type: DocumentType
    status: ProcessingStatus = ProcessingStatus.PROCESSING
    extracted_data: Optional[Dict[str, Any]] = None
    extracted_data_history: List[ExtractedDataVersion] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def record_version(
        self,
        new_data: Dict[str, Any],
        author_type: ExtractedDataAuthor,
        author_id: Optional[uuid.UUID] = None,
    ) -> None:
        current_payload = _flatten_payload(new_data)
        previous_payload = _flatten_payload(self.extracted_data or {})

        changes = _compute_changes(previous_payload, current_payload)

        if not changes and previous_payload == current_payload:
            return

        version_number = len(self.extracted_data_history) + 1
        now = datetime.utcnow()

        version_entry = ExtractedDataVersion(
            version=version_number,
            author_type=author_type,
            author_id=author_id,
            created_at=now,
            data_snapshot=current_payload,
            changes=changes,
        )

        self.extracted_data = current_payload
        self.extracted_data_history.append(version_entry)
        self.updated_at = now
