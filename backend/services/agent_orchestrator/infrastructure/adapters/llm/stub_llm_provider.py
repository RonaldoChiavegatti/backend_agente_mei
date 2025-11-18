from typing import List

from services.agent_orchestrator.application.domain.message import Message
from services.agent_orchestrator.application.ports.output.llm_provider import (
    LLMProvider,
)


class StubLLMProvider(LLMProvider):
    """In-memory LLM provider used for tests to avoid external requests."""

    def __init__(self, canned_response: str | None = None) -> None:
        self.canned_response = canned_response or "Stubbed LLM response"

    def generate_response(self, messages: List[Message]) -> str:
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                return f"[stub] {msg.content}"
        return self.canned_response
