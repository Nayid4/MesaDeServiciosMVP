"""Caso de uso CQRS de confirmación de borrador Human-in-the-Loop del Agente IA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.application.tickets import CreateTicketCommand, CreateTicketCommandHandler
from src.domain.exceptions import UnauthorizedError
from src.domain.ports import IUnitOfWork
from src.domain.rules import UPC_LOCATIONS, UPC_SEDES, UPC_SERVICE_CATALOG


@dataclass(frozen=True)
class ConfirmAgentDraftCommand(Command):
    actor: Optional[Dict[str, Any]]
    title: str
    description: str
    service_name: str
    sede: str
    location: str
    urgency: str
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    transcript: Optional[str] = None
    ip_address: str = "127.0.0.1"


class ConfirmAgentDraftCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory
        self._create_ticket_handler = CreateTicketCommandHandler(uow_factory)

    def handle(self, cmd: ConfirmAgentDraftCommand) -> Dict[str, Any]:
        if not cmd.actor or cmd.actor.get("role") == "public":
            raise UnauthorizedError(
                "Debe iniciar sesión con su cuenta institucional @unicesar.edu.co para radicar el ticket."
            )
        service_name = (
            cmd.service_name
            if cmd.service_name in UPC_SERVICE_CATALOG
            else list(UPC_SERVICE_CATALOG.keys())[0]
        )
        sede = cmd.sede if cmd.sede in UPC_SEDES else UPC_SEDES[0]
        location = cmd.location if cmd.location in UPC_LOCATIONS else UPC_LOCATIONS[0]
        urgency = cmd.urgency if cmd.urgency in ("Alta", "Media", "Baja") else "Media"

        description = (cmd.description or "").strip()
        if len(description) < 15:
            description = f"{description} — Caso escalado desde widget Agente IA CASAGBI.".strip()

        return self._create_ticket_handler.handle(
            CreateTicketCommand(
                actor=cmd.actor,
                title=cmd.title,
                description=description,
                ticket_type=UPC_SERVICE_CATALOG[service_name]["default_type"],
                service_name=service_name,
                sede=sede,
                location=location,
                urgency=urgency,
                ai_suggested_service=cmd.ai_suggested_service or service_name,
                ai_confidence=cmd.ai_confidence,
                ai_human_validated=True,
                initial_transcript=cmd.transcript,
                ip_address=cmd.ip_address,
            )
        )
