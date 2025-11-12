import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status

from services.agent_orchestrator.application.ports.input.orchestrator_service import (
    OrchestratorService,
)
from services.agent_orchestrator.application.domain.message import Message
from services.agent_orchestrator.application.exceptions import (
    AgentNotFoundError,
    InsufficientBalanceError,
)
from services.agent_orchestrator.infrastructure.dependencies import (
    get_orchestrator_service,
)
from services.agent_orchestrator.infrastructure.security import get_current_user_id

router = APIRouter()


class ChatRequest(BaseModel):
    agent_id: uuid.UUID
    user_message: str
    conversation_history: Optional[List[Message]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    assistant_message: str


@router.post("/chat", response_model=ChatResponse)
def chat_with_agent(
    request: ChatRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: OrchestratorService = Depends(get_orchestrator_service),
):
    try:
        response_message = service.handle_chat_message(
            user_id=user_id,
            agent_id=request.agent_id,
            user_message=request.user_message,
            conversation_history=request.conversation_history,
        )
        return ChatResponse(assistant_message=response_message)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )
