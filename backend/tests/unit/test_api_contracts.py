import io
import os
import sys
import types
import uuid
from datetime import datetime
from typing import List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("GEMINI_API_KEY", "dummy")
os.environ.setdefault("BILLING_SERVICE_URL", "http://billing")
os.environ.setdefault("MINIO_ENDPOINT", "minio:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minio")
os.environ.setdefault("MINIO_SECRET_KEY", "minio")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

sys.modules.setdefault("minio", types.SimpleNamespace(Minio=object))
sys.modules.setdefault("minio.error", types.SimpleNamespace(S3Error=Exception))

from services.agent_orchestrator.application.exceptions import AgentNotFoundError, InsufficientBalanceError
from services.agent_orchestrator.infrastructure.dependencies import get_orchestrator_service
from services.agent_orchestrator.infrastructure.security import (
    get_current_user_id as auth_current_user,
)
from services.agent_orchestrator.infrastructure.web import api as orchestrator_api
from services.auth_service.application.exceptions import InvalidCredentialsError
from services.auth_service.infrastructure.dependencies import get_user_service
from services.auth_service.infrastructure.security import (
    get_current_user_id as auth_service_current_user,
)
from services.auth_service.infrastructure.web import api as auth_api
from services.billing_service.application.exceptions import UserNotFoundError
from services.billing_service.infrastructure.dependencies import get_billing_service
from services.billing_service.infrastructure.security import (
    get_current_user_id as billing_current_user,
)
from services.billing_service.infrastructure.web import api as billing_api
from services.document_service.application.exceptions import JobAccessForbiddenError, JobNotFoundError
from services.document_service.infrastructure.dependencies import get_document_service
from services.document_service.infrastructure.security import (
    get_current_user_id as documents_current_user,
)
from services.document_service.infrastructure.web import api as documents_api
from shared.models.base_models import (
    DocumentJob,
    DocumentType,
    ProcessingStatus,
    TokenUsageRecord,
    TokenUsageSummary,
)


auth_app = FastAPI()
auth_app.include_router(auth_api.router)

orchestrator_app = FastAPI()
orchestrator_app.include_router(orchestrator_api.router)

billing_app = FastAPI()
billing_app.include_router(billing_api.router)

documents_app = FastAPI()
documents_app.include_router(documents_api.router)


class _StubUser:
    def __init__(self, user_id: uuid.UUID):
        self.id = user_id
        self.full_name = "Test User"
        self.email = "user@example.com"
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class _StubUserService:
    def __init__(self, user_id: uuid.UUID, raise_on_login: bool = False):
        self._user_id = user_id
        self._raise_on_login = raise_on_login

    def register_user(self, full_name: str, email: str, password: str):
        return _StubUser(self._user_id)

    def get_user_profile(self, user_id: uuid.UUID):
        return _StubUser(user_id)

    def login(self, email: str, password: str):
        if self._raise_on_login:
            raise InvalidCredentialsError("Invalid credentials")
        return {"access_token": "token", "token_type": "bearer"}


class _StubOrchestratorService:
    def __init__(self, raise_insufficient: bool = False, raise_not_found: bool = False):
        self._raise_insufficient = raise_insufficient
        self._raise_not_found = raise_not_found

    def handle_chat_message(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID,
        user_message: str,
        conversation_history: List,
    ) -> str:
        if self._raise_not_found:
            raise AgentNotFoundError("Agent not found")
        if self._raise_insufficient:
            raise InsufficientBalanceError("Insufficient balance")
        return "Hello from agent"


def _stub_document_job(user_id: uuid.UUID) -> DocumentJob:
    return DocumentJob(
        id=uuid.uuid4(),
        user_id=user_id,
        file_path="/tmp/file.pdf",
        document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        status=ProcessingStatus.PROCESSING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class _StubDocumentService:
    def __init__(self, job_owner: uuid.UUID):
        self._job_owner = job_owner

    def start_document_processing(self, user_id, file_name, file_content, document_type):
        return _stub_document_job(user_id)

    def get_job_status(self, job_id: uuid.UUID, user_id: uuid.UUID):
        if user_id != self._job_owner:
            raise JobAccessForbiddenError("Forbidden access")
        return _stub_document_job(user_id)

    def get_user_jobs(self, user_id: uuid.UUID, document_type=None):
        return [_stub_document_job(user_id)]


class _StubBillingService:
    def __init__(self, success_charge: bool = True, known_user: uuid.UUID | None = None):
        self.success_charge = success_charge
        self.known_user = known_user or uuid.uuid4()

    def charge_user(self, user_id: uuid.UUID, amount: int, description: str):
        return self.success_charge

    def get_user_balance(self, user_id: uuid.UUID):
        if user_id != self.known_user:
            raise UserNotFoundError("User not found")
        return {"user_id": user_id, "balance": 100, "last_updated_at": datetime.utcnow()}

    def get_user_transactions(self, user_id: uuid.UUID):
        if user_id != self.known_user:
            raise UserNotFoundError("User not found")
        return [
            TokenUsageRecord(
                id=uuid.uuid4(),
                date=datetime.utcnow(),
                tokens=10,
                consultation_type="chat",
                description="Test charge",
                document_type="NOTA_FISCAL_EMITIDA",
            )
        ]

    def get_user_monthly_usage(self, user_id: uuid.UUID):
        return TokenUsageSummary(
            user_id=user_id,
            tokens_consumed=20,
            consultations_count=2,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
        )


def _clear_overrides(app):
    app.dependency_overrides.clear()


def test_auth_register_contract():
    user_id = uuid.uuid4()
    auth_app.dependency_overrides[get_user_service] = lambda: _StubUserService(user_id)
    client = TestClient(auth_app)

    response = client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": "user@example.com", "password": "secret"},
    )

    try:
        assert response.status_code == 201
        body = response.json()
        assert body["id"] == str(user_id)
        assert body["full_name"] == "Test User"
        assert body["email"] == "user@example.com"
    finally:
        _clear_overrides(auth_app)


def test_auth_login_invalid_credentials_error():
    auth_app.dependency_overrides[get_user_service] = lambda: _StubUserService(uuid.uuid4(), True)
    client = TestClient(auth_app)

    response = client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "bad"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    finally:
        _clear_overrides(auth_app)


def test_auth_profile_requires_authorization_header():
    client = TestClient(auth_app)

    response = client.get("/auth/profile")

    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"] or "Missing" in response.json()["detail"]


def test_chat_contract_and_insufficient_balance_error():
    user_id = uuid.uuid4()
    orchestrator_app.dependency_overrides[get_orchestrator_service] = (
        lambda: _StubOrchestratorService()
    )
    orchestrator_app.dependency_overrides[auth_current_user] = lambda: user_id
    client = TestClient(orchestrator_app)

    payload = {"agent_id": str(uuid.uuid4()), "user_message": "Hello", "conversation_history": []}
    ok_response = client.post("/chat", json=payload, headers={"Authorization": "Bearer token"})
    assert ok_response.status_code == 200
    assert ok_response.json() == {"assistant_message": "Hello from agent"}

    orchestrator_app.dependency_overrides[get_orchestrator_service] = (
        lambda: _StubOrchestratorService(raise_insufficient=True)
    )
    insufficient = client.post("/chat", json=payload, headers={"Authorization": "Bearer token"})
    try:
        assert insufficient.status_code == 402
        assert "balance" in insufficient.json()["detail"].lower()
    finally:
        _clear_overrides(orchestrator_app)


def test_documents_upload_and_list_contracts():
    user_id = uuid.uuid4()
    documents_app.dependency_overrides[documents_current_user] = lambda: user_id
    documents_app.dependency_overrides[get_document_service] = (
        lambda: _StubDocumentService(job_owner=user_id)
    )
    client = TestClient(documents_app)

    try:
        boundary = "---api-contract-boundary"
        multipart_body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="test.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
            "data\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="document_type"\r\n\r\n'
            f"{DocumentType.NOTA_FISCAL_EMITIDA.value}\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        upload_response = client.post(
            "/documents/upload",
            content=multipart_body,
            headers={
                "Authorization": "Bearer token",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        assert upload_response.status_code == 202
        upload_body = upload_response.json()
        assert upload_body["user_id"] == str(user_id)
        assert upload_body["status"] == ProcessingStatus.PROCESSING.value

        list_response = client.get(
            "/documents/jobs",
            headers={"Authorization": "Bearer token"},
        )
        assert list_response.status_code == 200
        jobs = list_response.json()
        assert isinstance(jobs, list)
        assert jobs and jobs[0]["document_type"] == DocumentType.NOTA_FISCAL_EMITIDA.value
    finally:
        _clear_overrides(documents_app)


def test_documents_requires_token_for_jobs():
    _clear_overrides(documents_app)
    client = TestClient(documents_app)
    response = client.get("/documents/jobs")
    assert response.status_code == 401
    assert "Missing" in response.json()["detail"]


def test_billing_contracts_and_security_checks():
    user_id = uuid.uuid4()
    billing_service = _StubBillingService(success_charge=True, known_user=user_id)
    billing_app.dependency_overrides[get_billing_service] = lambda: billing_service
    billing_app.dependency_overrides[billing_current_user] = lambda: user_id
    client = TestClient(billing_app)

    charge_response = client.post(
        "/billing/charge-tokens",
        json={"user_id": str(user_id), "amount": 10, "description": "test"},
    )
    assert charge_response.status_code == 200
    assert charge_response.json() == {"status": "success"}

    billing_app.dependency_overrides[get_billing_service] = lambda: _StubBillingService(
        success_charge=False, known_user=user_id
    )
    failed_charge = client.post(
        "/billing/charge-tokens",
        json={"user_id": str(user_id), "amount": 10, "description": "test"},
    )
    assert failed_charge.status_code == 402
    assert "Insufficient" in failed_charge.json()["detail"]

    transactions = client.get(
        f"/billing/transactions/{user_id}", headers={"Authorization": "Bearer token"}
    )
    summary = client.get(
        f"/billing/monthly-usage/{user_id}", headers={"Authorization": "Bearer token"}
    )
    try:
        assert transactions.status_code == 200
        record = transactions.json()[0]
        assert {"id", "date", "tokens", "consultation_type", "description"}.issubset(record.keys())

        assert summary.status_code == 200
        summary_body = summary.json()
        assert summary_body["user_id"] == str(user_id)
        assert "tokens_consumed" in summary_body
    finally:
        _clear_overrides(billing_app)


def test_billing_rejects_mismatched_user_and_missing_token():
    user_id = uuid.uuid4()
    other_id = uuid.uuid4()
    billing_app.dependency_overrides[get_billing_service] = lambda: _StubBillingService(
        known_user=user_id
    )
    billing_app.dependency_overrides[billing_current_user] = lambda: other_id
    client = TestClient(billing_app)

    forbidden = client.get(
        f"/billing/transactions/{user_id}", headers={"Authorization": "Bearer token"}
    )
    billing_app.dependency_overrides.pop(billing_current_user, None)
    unauthenticated = TestClient(billing_app).get(f"/billing/transactions/{user_id}")

    try:
        assert forbidden.status_code == 403
        assert unauthenticated.status_code == 401
    finally:
        _clear_overrides(billing_app)
