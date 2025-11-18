import os
from pathlib import Path

import pytest


project_root = Path(__file__).parent.parent.parent
if str(project_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(project_root))

from services.agent_orchestrator.infrastructure.adapters.llm.stub_llm_provider import (
    StubLLMProvider,
)


@pytest.fixture(autouse=True)
def use_stub_llm(monkeypatch):
    monkeypatch.setenv("USE_STUB_LLM", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setenv("BILLING_SERVICE_URL", "http://billing")
    monkeypatch.setenv("SECRET_KEY", "secret")


def test_orchestrator_dependency_uses_stub_provider(monkeypatch):
    from services.agent_orchestrator.infrastructure.dependencies import (
        get_orchestrator_service,
    )

    class _DummyRepository:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyBilling:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "services.agent_orchestrator.infrastructure.dependencies.PostgresAgentRepository",
        lambda *args, **kwargs: _DummyRepository(),
    )
    monkeypatch.setattr(
        "services.agent_orchestrator.infrastructure.dependencies.HttpBillingService",
        lambda *args, **kwargs: _DummyBilling(),
    )

    service = get_orchestrator_service(db=None)

    assert isinstance(service.llm_provider, StubLLMProvider)
