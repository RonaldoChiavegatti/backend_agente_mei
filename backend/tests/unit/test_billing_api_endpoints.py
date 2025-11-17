import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Environment defaults to satisfy settings validation during imports
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MINIO_ENDPOINT", "localhost")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Allow imports from the project
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.billing_service.application.exceptions import UserNotFoundError  # noqa: E402
from services.billing_service.infrastructure.dependencies import (  # noqa: E402
    get_billing_service,
)
from services.billing_service.infrastructure.web import api  # noqa: E402
from shared.models.base_models import (  # noqa: E402
    TokenUsageRecord,
    TokenUsageSummary,
    UserBalance,
)


class FakeBillingService:
    def __init__(
        self,
        *,
        balance: UserBalance | None = None,
        transactions: list[TokenUsageRecord] | None = None,
        summary: TokenUsageSummary | None = None,
        charge_success: bool = True,
        error: Exception | None = None,
    ) -> None:
        self.balance = balance
        self.transactions = transactions or []
        self.summary = summary
        self.charge_success = charge_success
        self.error = error

    def charge_user(self, user_id: uuid.UUID, amount: int, description: str) -> bool:
        if self.error:
            raise self.error
        return self.charge_success

    def get_user_balance(self, user_id: uuid.UUID) -> UserBalance:
        if self.error:
            raise self.error
        assert self.balance is not None
        return self.balance

    def get_user_transactions(self, user_id: uuid.UUID):
        if self.error:
            raise self.error
        return self.transactions

    def get_user_monthly_usage(self, user_id: uuid.UUID) -> TokenUsageSummary:
        if self.error:
            raise self.error
        assert self.summary is not None
        return self.summary


def build_app(service: FakeBillingService) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_billing_service] = lambda: service
    return TestClient(app)


def test_charge_tokens_endpoint_returns_success():
    client = build_app(FakeBillingService())

    response = client.post(
        "/billing/charge-tokens",
        json={
            "user_id": str(uuid.uuid4()),
            "amount": 10,
            "description": "Uso de tokens",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_charge_tokens_endpoint_handles_insufficient_balance():
    client = build_app(FakeBillingService(charge_success=False))

    response = client.post(
        "/billing/charge-tokens",
        json={
            "user_id": str(uuid.uuid4()),
            "amount": 999,
            "description": "Uso de tokens",
        },
    )

    assert response.status_code == 402
    assert response.json()["detail"] == "Insufficient balance or user not found."


def test_get_balance_endpoint_returns_payload():
    user_id = uuid.uuid4()
    balance = UserBalance(user_id=user_id, balance=150, last_updated_at=datetime.utcnow())
    client = build_app(FakeBillingService(balance=balance))

    response = client.get(f"/billing/balance/{user_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(user_id)
    assert payload["balance"] == 150


def test_get_balance_endpoint_returns_404_for_missing_user():
    client = build_app(FakeBillingService(error=UserNotFoundError("not found")))

    response = client.get(f"/billing/balance/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "not found"


def test_get_transactions_endpoint_returns_records():
    user_id = uuid.uuid4()
    record = TokenUsageRecord(
        id=uuid.uuid4(),
        date=datetime.utcnow(),
        tokens=42,
        consultation_type="chat",
        description="Teste",
        document_type=None,
    )
    client = build_app(FakeBillingService(transactions=[record]))

    response = client.get(f"/billing/transactions/{user_id}")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["tokens"] == 42
    assert body[0]["consultation_type"] == "chat"


def test_get_monthly_usage_endpoint_returns_summary():
    user_id = uuid.uuid4()
    summary = TokenUsageSummary(
        user_id=user_id,
        tokens_consumed=100,
        consultations_count=5,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
    )
    client = build_app(FakeBillingService(summary=summary))

    response = client.get(f"/billing/monthly-usage/{user_id}")

    assert response.status_code == 200
    result = response.json()
    assert result["tokens_consumed"] == 100
    assert result["consultations_count"] == 5
