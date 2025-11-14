import uuid
from typing import List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from shared.models.base_models import (
    UserBalance as UserBalanceResponse,
    Transaction as TransactionResponse,
    TokenUsageSummary as TokenUsageSummaryResponse,
)
from services.billing_service.application.ports.input.billing_service import (
    BillingService,
)
from services.billing_service.application.exceptions import UserNotFoundError
from services.billing_service.infrastructure.dependencies import get_billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])


class ChargeRequest(BaseModel):
    user_id: uuid.UUID
    amount: int
    description: str


@router.post("/charge-tokens", status_code=status.HTTP_200_OK)
def charge_tokens_endpoint(
    request: ChargeRequest, service: BillingService = Depends(get_billing_service)
):
    """
    Internal endpoint to charge a user for token usage.
    """
    success = service.charge_user(
        user_id=request.user_id, amount=request.amount, description=request.description
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient balance or user not found.",
        )
    return {"status": "success"}


@router.get("/balance/{user_id}", response_model=UserBalanceResponse)
def get_balance_endpoint(
    user_id: uuid.UUID, service: BillingService = Depends(get_billing_service)
):
    try:
        balance = service.get_user_balance(user_id=user_id)
        return balance
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/transactions/{user_id}", response_model=List[TransactionResponse])
def get_transactions_endpoint(
    user_id: uuid.UUID, service: BillingService = Depends(get_billing_service)
):
    try:
        transactions = service.get_user_transactions(user_id=user_id)
        return transactions
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/monthly-usage/{user_id}", response_model=TokenUsageSummaryResponse
)
def get_monthly_usage_endpoint(
    user_id: uuid.UUID, service: BillingService = Depends(get_billing_service)
):
    usage = service.get_user_monthly_usage(user_id=user_id)
    return usage
