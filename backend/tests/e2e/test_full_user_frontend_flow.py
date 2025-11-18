import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient

# Ensure required settings are present for service imports
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("MINIO_ENDPOINT", "localhost")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("BILLING_SERVICE_URL", "http://localhost:8004")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

# Stub external clients that are not needed for the integration test setup
if "minio" not in sys.modules:
    import types

    minio_module = types.ModuleType("minio")
    minio_module.Minio = object
    minio_error_module = types.ModuleType("minio.error")
    minio_error_module.S3Error = Exception
    sys.modules["minio"] = minio_module
    sys.modules["minio.error"] = minio_error_module

from services.agent_orchestrator.application.domain.agent import Agent as DomainAgent
from services.agent_orchestrator.application.domain.knowledge import Knowledge
from services.agent_orchestrator.application.domain.message import Message
from services.agent_orchestrator.application.exceptions import AgentNotFoundError
from services.agent_orchestrator.application.ports.output.agent_repository import (  # noqa: E402
    AgentRepository,
)
from services.agent_orchestrator.application.ports.output.billing_service import (  # noqa: E402
    BillingService as OrchestratorBillingService,
)
from services.agent_orchestrator.application.ports.output.llm_provider import (  # noqa: E402
    LLMProvider,
)
from services.agent_orchestrator.application.services.orchestrator_service_impl import (  # noqa: E402
    OrchestratorServiceImpl,
)
from services.agent_orchestrator.infrastructure.dependencies import (  # noqa: E402
    get_orchestrator_service,
)
from services.agent_orchestrator.infrastructure.security import (  # noqa: E402
    get_current_user_id as orchestrator_current_user,
)
from services.agent_orchestrator.infrastructure.web import api as orchestrator_api
from services.auth_service.application.ports.input.user_service import (  # noqa: E402
    UserService,
)
from services.auth_service.infrastructure.dependencies import (  # noqa: E402
    get_user_service,
)
from services.auth_service.infrastructure.web import api as auth_api
from services.auth_service.infrastructure.security import (  # noqa: E402
    get_current_user_id as auth_current_user,
)
from services.billing_service.application.exceptions import (  # noqa: E402
    UserNotFoundError,
)
from services.billing_service.application.ports.input.billing_service import (  # noqa: E402
    BillingService,
)
from services.billing_service.infrastructure.dependencies import (  # noqa: E402
    get_billing_service,
)
from services.billing_service.infrastructure.security import (  # noqa: E402
    get_current_user_id as billing_current_user,
)
from services.billing_service.infrastructure.web import api as billing_api
from services.document_service.application.domain.document_job import (  # noqa: E402
    DocumentType,
    ProcessingStatus,
)
from services.document_service.application.ports.input.document_service import (  # noqa: E402
    DocumentService,
)
from services.document_service.infrastructure.dependencies import (  # noqa: E402
    get_document_service,
)
from services.document_service.infrastructure.security import (  # noqa: E402
    get_current_user_id as document_current_user,
)
from services.document_service.infrastructure.web import api as document_api
from shared.models.base_models import (
    DocumentJob,
    Token,
    TokenUsageRecord,
    User,
    UserBalance,
)


@dataclass
class FakeUser:
    id: uuid.UUID
    email: str
    full_name: str
    password: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeUserService(UserService):
    def __init__(self, token_store: Dict[str, uuid.UUID]):
        self.users: Dict[str, FakeUser] = {}
        self.token_store = token_store

    def register_user(self, full_name: str, email: str, password: str) -> User:
        if email in self.users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            )

        user = FakeUser(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            password=password,
        )
        self.users[email] = user
        return User.model_validate(user)

    def login(self, email: str, password: str) -> Token:
        if email not in self.users or self.users[email].password != password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        user_id = self.users[email].id
        access_token = f"token-{user_id}"
        self.token_store[access_token] = user_id
        return Token(access_token=access_token, token_type="bearer")

    def get_user_profile(self, user_id: uuid.UUID) -> User:
        for user in self.users.values():
            if user.id == user_id:
                return User.model_validate(user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


class FakeBillingService(BillingService, OrchestratorBillingService):
    def __init__(self, starting_balance: int = 100):
        self.starting_balance = starting_balance
        self.balances: Dict[uuid.UUID, int] = {}
        self.transactions: Dict[uuid.UUID, List[TokenUsageRecord]] = {}

    def _ensure_user(self, user_id: uuid.UUID) -> None:
        self.balances.setdefault(user_id, self.starting_balance)
        self.transactions.setdefault(user_id, [])

    def charge_user(self, user_id: uuid.UUID, amount: int, description: str) -> bool:
        self._ensure_user(user_id)
        if self.balances[user_id] < amount:
            return False

        self.balances[user_id] -= amount
        record = TokenUsageRecord(
            id=uuid.uuid4(),
            date=datetime.utcnow(),
            tokens=amount,
            consultation_type="chat",
            description=description,
            document_type=None,
        )
        self.transactions[user_id].append(record)
        return True

    def charge_tokens(self, user_id: uuid.UUID, amount: int, description: str) -> bool:
        return self.charge_user(user_id, amount, description)

    def get_user_balance(self, user_id: uuid.UUID):
        if user_id not in self.balances:
            raise UserNotFoundError("User not found")
        return UserBalance(
            user_id=user_id,
            balance=self.balances[user_id],
            last_updated_at=datetime.utcnow(),
        )

    def get_user_transactions(self, user_id: uuid.UUID):
        if user_id not in self.transactions:
            raise UserNotFoundError("User not found")
        return self.transactions[user_id]

    def get_user_monthly_usage(self, user_id: uuid.UUID):
        if user_id not in self.transactions:
            raise UserNotFoundError("User not found")
        total_tokens = sum(record.tokens for record in self.transactions[user_id])
        return {
            "user_id": user_id,
            "tokens_consumed": total_tokens,
            "consultations_count": len(self.transactions[user_id]),
            "start_date": datetime.utcnow() - timedelta(days=30),
            "end_date": datetime.utcnow(),
        }


@dataclass
class InMemoryDocumentJob:
    id: uuid.UUID
    user_id: uuid.UUID
    file_path: str
    document_type: DocumentType
    status: ProcessingStatus
    extracted_data: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeDocumentService(DocumentService):
    def __init__(self):
        self.jobs: Dict[uuid.UUID, InMemoryDocumentJob] = {}

    def start_document_processing(self, user_id, file_name, file_content, document_type):
        if not file_name:
            raise ValueError("Arquivo sem nome não pode ser processado.")
        if not file_content.read(1):
            raise ValueError("Arquivo vazio não pode ser processado.")
        file_content.seek(0)

        job = InMemoryDocumentJob(
            id=uuid.uuid4(),
            user_id=user_id,
            file_path=f"documents/{user_id}/{file_name}",
            document_type=document_type,
            status=ProcessingStatus.PROCESSING,
        )
        self.jobs[job.id] = job
        return DocumentJob.model_validate(job)

    def complete_job(self, job_id: uuid.UUID, extracted_data: Optional[dict] = None):
        job = self.jobs[job_id]
        job.status = ProcessingStatus.COMPLETED
        job.extracted_data = extracted_data or {"total": 1000}
        job.updated_at = datetime.now(timezone.utc)
        self.jobs[job_id] = job

    def get_job_status(self, job_id: uuid.UUID, user_id: uuid.UUID):
        job = self.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return DocumentJob.model_validate(job)

    def get_user_jobs(self, user_id: uuid.UUID, document_type: Optional[DocumentType] = None):
        jobs = [job for job in self.jobs.values() if job.user_id == user_id]
        if document_type:
            jobs = [job for job in jobs if job.document_type == document_type]
        return [DocumentJob.model_validate(job) for job in jobs]

    def get_job_details(self, job_id: uuid.UUID, user_id: uuid.UUID):  # pragma: no cover - unused
        return self.get_job_status(job_id, user_id)

    def update_extracted_data(self, job_id: uuid.UUID, user_id: uuid.UUID, payload: dict):  # pragma: no cover - unused
        self.complete_job(job_id, extracted_data=payload)
        return self.get_job_status(job_id, user_id)

    def get_annual_revenue_summary(self, user_id: uuid.UUID, year: Optional[int] = None):  # pragma: no cover - unused
        raise NotImplementedError

    def get_monthly_revenue_summary(self, user_id: uuid.UUID, year: Optional[int] = None, month: Optional[int] = None):  # pragma: no cover - unused
        raise NotImplementedError

    def get_basic_dashboard_metrics(self, user_id: uuid.UUID):  # pragma: no cover - unused
        raise NotImplementedError

    def get_job_by_id(self, job_id: uuid.UUID):  # pragma: no cover - unused
        return self.jobs.get(job_id)


class FakeLLM(LLMProvider):
    def generate_response(self, messages: List[Message]) -> str:
        return "Resposta gerada com sucesso."


class FakeAgentRepository(AgentRepository):
    def __init__(self):
        self.agent = DomainAgent(
            id=uuid.uuid4(),
            name="Agente Teste",
            description="Agente para testes end-to-end",
            category="demo",
            created_at=datetime.utcnow(),
        )

    def get_agent_by_id(self, agent_id: uuid.UUID):
        if agent_id == self.agent.id:
            return self.agent
        raise AgentNotFoundError(f"Agent with ID {agent_id} not found.")

    def find_relevant_knowledge(self, agent_id: uuid.UUID, query: str):
        if agent_id != self.agent.id:
            raise AgentNotFoundError(f"Agent with ID {agent_id} not found.")
        return [
            Knowledge(
                id=uuid.uuid4(),
                title="Guia rápido",
                content="Informação relevante",
            )
        ]


def encode_multipart_form(fields: Dict[str, str], file_field: str, filename: str, file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"Boundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.append(
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n"
            ).encode()
        )

    parts.append(
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
    )
    parts.append(file_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def build_authorization_dependency(token_store: Dict[str, uuid.UUID]):
    def get_user_from_token(request: Request):
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
        token = header.split(" ", 1)[1]
        user_id = token_store.get(token)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id

    return get_user_from_token


@pytest.fixture
def gateway_test_app():
    token_store: Dict[str, uuid.UUID] = {}
    billing_service = FakeBillingService()
    user_service = FakeUserService(token_store)
    document_service = FakeDocumentService()
    agent_repo = FakeAgentRepository()
    llm_provider = FakeLLM()
    orchestrator_service = OrchestratorServiceImpl(agent_repo, llm_provider, billing_service)

    app = FastAPI()
    app.include_router(auth_api.router)
    app.include_router(document_api.router)
    app.include_router(orchestrator_api.router)
    app.include_router(billing_api.router)

    auth_dependency = build_authorization_dependency(token_store)
    for dependency in (auth_current_user, document_current_user, orchestrator_current_user, billing_current_user):
        app.dependency_overrides[dependency] = auth_dependency

    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_document_service] = lambda: document_service
    app.dependency_overrides[get_orchestrator_service] = lambda: orchestrator_service
    app.dependency_overrides[get_billing_service] = lambda: billing_service

    return {
        "client": TestClient(app),
        "token_store": token_store,
        "user_service": user_service,
        "document_service": document_service,
        "billing_service": billing_service,
        "agent_repo": agent_repo,
    }


def test_full_frontend_flow_through_gateway(gateway_test_app):
    client: TestClient = gateway_test_app["client"]
    document_service: FakeDocumentService = gateway_test_app["document_service"]
    billing_service: FakeBillingService = gateway_test_app["billing_service"]
    agent_repo: FakeAgentRepository = gateway_test_app["agent_repo"]

    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Usuário E2E",
            "email": "e2e@example.com",
            "password": "senhaSegura123",
        },
    )
    assert register_response.status_code == status.HTTP_201_CREATED
    user_id = uuid.UUID(register_response.json()["id"])

    login_response = client.post(
        "/auth/login",
        data={"username": "e2e@example.com", "password": "senhaSegura123"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    billing_service._ensure_user(user_id)

    multipart_body, multipart_header = encode_multipart_form(
        {"document_type": DocumentType.NOTA_FISCAL_EMITIDA.value},
        file_field="file",
        filename="nota.pdf",
        file_bytes=b"conteudo",
        content_type="application/pdf",
    )
    upload_response = client.post(
        "/documents/upload",
        headers={**headers, "Content-Type": multipart_header},
        content=multipart_body,
    )
    assert upload_response.status_code == status.HTTP_202_ACCEPTED
    job_id = uuid.UUID(upload_response.json()["id"])

    document_service.complete_job(job_id, extracted_data={"valor": 200})
    job_status_response = client.get(f"/documents/jobs/{job_id}", headers=headers)
    assert job_status_response.status_code == status.HTTP_200_OK
    assert job_status_response.json()["status"] == ProcessingStatus.COMPLETED.value

    chat_response = client.post(
        "/chat",
        headers=headers,
        json={
            "agent_id": str(agent_repo.agent.id),
            "user_message": "Olá, tudo bem?",
            "conversation_history": [],
        },
    )
    assert chat_response.status_code == status.HTTP_200_OK
    assert "Resposta" in chat_response.json()["assistant_message"]

    balance_response = client.get(f"/billing/balance/{user_id}", headers=headers)
    assert balance_response.status_code == status.HTTP_200_OK
    assert balance_response.json()["balance"] == billing_service.starting_balance - 10

    transactions_response = client.get(
        f"/billing/transactions/{user_id}", headers=headers
    )
    assert transactions_response.status_code == status.HTTP_200_OK
    assert transactions_response.json()[0]["tokens"] == 10
    assert transactions_response.json()[0]["consultation_type"] == "chat"
