"""Router REST v1 del Widget Flotante CASAGBI Agent (Nivel 0 + Tool Calling)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.application.ai_agent import ConfirmAgentDraftCommand, ProcessAgentTurnCommand
from src.infrastructure.composition import get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_current_user,
    get_optional_user,
)

router = APIRouter(prefix="/api/v1/agent", tags=["Agente IA Conversacional"])


class AgentHistoryTurn(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    simulate_failure: bool = False
    failed_attempts: int = 0
    history: Optional[List[AgentHistoryTurn]] = None
    email: Optional[str] = None
    selected_service: Optional[str] = None
    selected_sede: Optional[str] = None
    selected_location: Optional[str] = None
    selected_urgency: Optional[str] = None


class ConfirmAgentDraftRequest(BaseModel):
    title: str = Field(..., min_length=5)
    description: str
    service_name: str
    sede: str
    location: str
    urgency: str = "Media"
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    transcript: Optional[str] = None


@router.post("/chat")
def agent_chat(
    payload: AgentChatRequest,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    history_dicts = (
        [{"role": h.role, "content": h.content} for h in payload.history]
        if payload.history
        else None
    )
    return get_cqrs_bus().execute(
        ProcessAgentTurnCommand(
            user=current_user,
            message=payload.message,
            simulate_failure=payload.simulate_failure,
            failed_attempts=payload.failed_attempts,
            history=history_dicts,
            email=payload.email,
            selected_service=payload.selected_service,
            selected_sede=payload.selected_sede,
            selected_location=payload.selected_location,
            selected_urgency=payload.selected_urgency,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/confirm-draft", status_code=201)
def confirm_agent_draft(
    payload: ConfirmAgentDraftRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    created = get_cqrs_bus().execute(
        ConfirmAgentDraftCommand(
            actor=current_user,
            title=payload.title,
            description=payload.description,
            service_name=payload.service_name,
            sede=payload.sede,
            location=payload.location,
            urgency=payload.urgency,
            ai_suggested_service=payload.ai_suggested_service,
            ai_confidence=payload.ai_confidence,
            transcript=payload.transcript,
            ip_address=get_client_ip(request),
        )
    )
    return {"ticket": created}
