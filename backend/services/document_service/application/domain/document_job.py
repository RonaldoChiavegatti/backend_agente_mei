import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

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
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
