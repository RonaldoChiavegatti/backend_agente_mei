"""HTTP routes for the Billing service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import BillingTransaction
from app.db.session import get_session


class UsageRecord(BaseModel):
    """Payload received from the Agent service when logging usage."""

    user_id: UUID
    tokens: int = Field(..., ge=0)
    operation_type: str = Field(..., max_length=255)
    occurred_at: datetime

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "billing"}


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
def register_usage_transaction(
    payload: UsageRecord, db: Session = Depends(get_session)
):
    transaction = BillingTransaction(
        user_id=payload.user_id,
        tokens=payload.tokens,
        operation_type=payload.operation_type,
        occurred_at=payload.occurred_at,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return {"id": transaction.id}


@router.get("/summary")
def get_usage_summary(db: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    total_tokens = (
        db.query(func.coalesce(func.sum(BillingTransaction.tokens), 0))
        .scalar()
        or 0
    )
    total_requests = db.query(func.count(BillingTransaction.id)).scalar() or 0
    return {
        "month": now.strftime("%Y-%m"),
        "total_tokens": int(total_tokens),
        "total_requests": int(total_requests),
    }
