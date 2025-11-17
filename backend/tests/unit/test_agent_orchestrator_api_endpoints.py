import os
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Environment defaults to satisfy settings validation during imports
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("BILLING_SERVICE_URL", "http://billing")
os.environ.setdefault("SECRET_KEY", "test-secret")

# Allow imports from the project
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.agent_orchestrator.application.exceptions import (  # noqa: E402
    AgentNotFoundError,
    InsufficientBalanceError,
)
from services.agent_orchestrator.infrastructure.web import api  # noqa: E402
from services.agent_orchestrator.infrastructure.dependencies import (  # noqa: E402
    get_orchestrator_service,
)
from services.agent_orchestrator.infrastructure.security import (  # noqa: E402
    get_current_user_id,
)


class FakeOrchestratorService:
    def __init__(self, result: str | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    def handle_chat_message(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID,
        user_message: str,
        conversation_history,
    ) -> str:
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result


def build_app(service: FakeOrchestratorService) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_orchestrator_service] = lambda: service
    app.dependency_overrides[get_current_user_id] = lambda: uuid.uuid4()
    return TestClient(app)


def test_chat_endpoint_returns_assistant_message():
    client = build_app(FakeOrchestratorService(result="Olá!"))
    response = client.post(
        "/chat",
        json={
            "agent_id": str(uuid.uuid4()),
            "user_message": "Oi",
            "conversation_history": [],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"assistant_message": "Olá!"}


def test_chat_endpoint_returns_404_for_missing_agent():
    client = build_app(FakeOrchestratorService(error=AgentNotFoundError("missing")))

    response = client.post(
        "/chat",
        json={
            "agent_id": str(uuid.uuid4()),
            "user_message": "Oi",
            "conversation_history": [],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "missing"


def test_chat_endpoint_returns_402_when_balance_insufficient():
    client = build_app(
        FakeOrchestratorService(error=InsufficientBalanceError("no-balance"))
    )

    response = client.post(
        "/chat",
        json={
            "agent_id": str(uuid.uuid4()),
            "user_message": "Oi",
            "conversation_history": [],
        },
    )

    assert response.status_code == 402
    assert response.json()["detail"] == "no-balance"
