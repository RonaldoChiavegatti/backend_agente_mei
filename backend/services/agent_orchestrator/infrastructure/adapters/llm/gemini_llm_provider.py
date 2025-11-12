from typing import List
import httpx

from services.agent_orchestrator.application.domain.message import Message
from services.agent_orchestrator.application.ports.output.llm_provider import (
    LLMProvider,
)


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    ):
        self.api_key = api_key
        self.api_url = f"{api_url}?key={self.api_key}"

    def generate_response(self, messages: List[Message]) -> str:
        contents = [
            {
                "role": msg.role,
                "parts": [{"text": msg.content}],
            }
            for msg in messages
        ]
        payload = {"contents": contents}

        try:
            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, timeout=30.0)
                response.raise_for_status()
                api_response = response.json()
                return api_response["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            raise ConnectionError(
                f"LLM API request failed with status {e.response.status_code}: {e.response.text}"
            )
        except (httpx.RequestError, KeyError, IndexError) as e:
            raise ConnectionError(
                f"Failed to communicate with LLM API or parse response: {e}"
            )
