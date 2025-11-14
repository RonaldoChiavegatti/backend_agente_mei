import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TransactionType(str, Enum):
    CHARGE = "CHARGE"
    REFUND = "REFUND"
    INITIAL = "INITIAL"


class Transaction(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: int
    type: TransactionType
    description: Optional[str] = None
    related_job_id: Optional[uuid.UUID] = None
    created_at: datetime
