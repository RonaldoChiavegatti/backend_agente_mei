from fastapi import Depends
from sqlalchemy.orm import Session

from services.agent_orchestrator.infrastructure.database import get_db
from services.agent_orchestrator.application.ports.input.orchestrator_service import (
    OrchestratorService,
)
from services.agent_orchestrator.application.services.orchestrator_service_impl import (
    OrchestratorServiceImpl,
)
from services.agent_orchestrator.infrastructure.adapters.persistence.postgres_agent_repository import (
    PostgresAgentRepository,
)
from services.agent_orchestrator.infrastructure.adapters.llm.gemini_llm_provider import (
    GeminiLLMProvider,
)
from services.agent_orchestrator.infrastructure.adapters.llm.stub_llm_provider import (
    StubLLMProvider,
)
from services.agent_orchestrator.infrastructure.adapters.billing.http_billing_service import (
    HttpBillingService,
)
from services.agent_orchestrator.infrastructure.config import settings


def get_orchestrator_service(db: Session = Depends(get_db)) -> OrchestratorService:
    """
    Composition Root for the OrchestratorService.
    """
    agent_repo = PostgresAgentRepository(db)

    llm_provider = (
        StubLLMProvider()
        if settings.USE_STUB_LLM
        else GeminiLLMProvider(api_key=settings.GEMINI_API_KEY)
    )

    billing_service = HttpBillingService(base_url=settings.BILLING_SERVICE_URL)

    return OrchestratorServiceImpl(
        agent_repository=agent_repo,
        llm_provider=llm_provider,
        billing_service=billing_service,
    )
