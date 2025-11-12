from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_chat_service
from app.services.chat import AgentChatService

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    user_id: UUID
    question: str


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "agent"}


@router.post("/chat")
def chat(
    payload: ChatRequest, service: AgentChatService = Depends(get_chat_service)
):
    answer, debug_payload = service.answer_question(
        user_id=payload.user_id, question=payload.question
    )
    return {"answer": answer, "debug": debug_payload}
