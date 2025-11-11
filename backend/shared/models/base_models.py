import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# =============================================================================
# Enums (mirroring a subset of SQL TYPEs for application logic)
# =============================================================================


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TransactionType(str, Enum):
    CHARGE = "CHARGE"
    REFUND = "REFUND"
    INITIAL = "INITIAL"


# =============================================================================
# User Models (Auth Service)
# =============================================================================


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Token Models (Auth Service)
# =============================================================================


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None
    email: Optional[EmailStr] = None


# =============================================================================
# Agent Models (Agent Orchestrator)
# =============================================================================


class Agent(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Document Models (Document Service)
# =============================================================================


class DocumentJob(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    file_path: str
    status: ProcessingStatus
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Billing Models (Billing Service)
# =============================================================================


class UserBalance(BaseModel):
    user_id: uuid.UUID
    balance: int
    last_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Transaction(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: int
    type: TransactionType
    description: Optional[str] = None
    related_job_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Generic API Responses
# =============================================================================


class Message(BaseModel):
    message: str
