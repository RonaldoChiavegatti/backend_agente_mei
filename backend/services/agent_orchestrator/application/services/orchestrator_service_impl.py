import uuid
from typing import List

from services.agent_orchestrator.application.domain.message import Message
from services.agent_orchestrator.application.ports.input.orchestrator_service import (
    OrchestratorService,
)
from services.agent_orchestrator.application.ports.output.agent_repository import (
    AgentRepository,
)
from services.agent_orchestrator.application.ports.output.llm_provider import (
    LLMProvider,
)
from services.agent_orchestrator.application.ports.output.billing_service import (
    BillingService,
)
from services.agent_orchestrator.application.exceptions import (
    AgentNotFoundError,
    InsufficientBalanceError,
)


class OrchestratorServiceImpl(OrchestratorService):
    """
    Concrete implementation of the OrchestratorService.
    Contains the core RAG (Retrieval-Augmented Generation) logic.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        llm_provider: LLMProvider,
        billing_service: BillingService,
    ):
        self.agent_repository = agent_repository
        self.llm_provider = llm_provider
        self.billing_service = billing_service

    def _construct_prompt(self, context_docs: List[str]) -> str:
        """Helper function to construct the system prompt for the LLM."""
        if context_docs:
            context = "\n\n".join(context_docs)
        else:
            context = "Nenhum conhecimento específico foi encontrado para esta pergunta."

        prompt = f"""
        Você é um agente de IA especialista em contabilidade para Microempreendedores Individuais (MEI) no Brasil.
        Utilize o contexto abaixo para responder de forma amigável, objetiva e sempre em português brasileiro.
        Se a resposta não estiver no contexto, informe que você não possui dados suficientes.

        Contexto:
        ---
        {context}
        ---
        """
        return prompt.strip()

    def handle_chat_message(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID,
        user_message: str,
        conversation_history: List[Message],
    ) -> str:
        agent = self.agent_repository.get_agent_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent with ID {agent_id} not found.")

        relevant_knowledge = self.agent_repository.find_relevant_knowledge(
            agent_id=agent_id, query=user_message
        )
        context_docs = [doc.content for doc in relevant_knowledge]

        system_prompt = self._construct_prompt(context_docs)

        llm_messages: List[Message] = [Message(role="system", content=system_prompt)]

        if conversation_history:
            # Ensure we don't mutate the incoming history list when appending
            llm_messages.extend(
                Message(role=msg.role, content=msg.content)
                for msg in conversation_history
            )

        llm_messages.append(Message(role="user", content=user_message))

        assistant_response = self.llm_provider.generate_response(llm_messages)

        charge_amount = 10
        charge_description = f"Chat with agent {agent.name}"

        success = self.billing_service.charge_tokens(
            user_id=user_id, amount=charge_amount, description=charge_description
        )

        if not success:
            raise InsufficientBalanceError(
                "Could not process request due to insufficient balance."
            )

        return assistant_response
