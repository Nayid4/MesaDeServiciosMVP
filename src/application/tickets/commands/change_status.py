"""Casos de uso CQRS de transición de estado ITIL, pausa SLA y calificación CSAT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.application.tickets.ticket_helpers import authorize_ticket_access
from src.domain.exceptions import (
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import (
    calculate_sla_status,
    now_bogota,
    parse_iso_datetime,
    validate_csat_rating,
    validate_reopen_window,
    validate_state_transition,
)


@dataclass(frozen=True)
class TransitionTicketCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    new_status: str
    comment: Optional[str] = None
    diagnosis: Optional[str] = None
    solution: Optional[str] = None
    closing_category: Optional[str] = None
    expected_version: Optional[int] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class RateTicketCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    csat_score: int
    csat_comment: Optional[str] = None
    confirm_close: bool = True
    expected_version: Optional[int] = None
    ip_address: str = "127.0.0.1"


class TransitionTicketCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: TransitionTicketCommand) -> Dict[str, Any]:
        role = cmd.actor.get("role")
        if role == "director":
            raise ForbiddenError("El rol Director no ejecuta transiciones operativas.")

        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)
            current_status = ticket["status"]

            if role == "usuario":
                allowed_user_next = (
                    ("Cerrado", "Reabierto")
                    if current_status == "Resuelto"
                    else ("Anulado",)
                    if current_status == "Registrado"
                    else ()
                )
                if cmd.new_status not in allowed_user_next:
                    raise ForbiddenError(
                        "Como usuario institucional solo puede confirmar cierre o reabrir un ticket Resuelto."
                    )

            try:
                validate_state_transition(
                    current_status=current_status,
                    new_status=cmd.new_status,
                    comment=cmd.comment,
                    diagnosis=cmd.diagnosis,
                    solution=cmd.solution,
                    closing_category=cmd.closing_category,
                )
                if current_status == "Resuelto" and cmd.new_status == "Reabierto":
                    validate_reopen_window(ticket.get("resolved_at"))
            except ValueError as exc:
                raise InvalidTransitionError(str(exc)) from exc

            now_dt = now_bogota()
            now_iso = now_dt.isoformat()
            updates: Dict[str, Any] = {"status": cmd.new_status, "updated_at": now_iso}

            if current_status == "En espera" and ticket.get("paused_at"):
                paused_dt = parse_iso_datetime(ticket["paused_at"])
                if paused_dt:
                    delta = max(0, int((now_dt - paused_dt).total_seconds()))
                    updates["paused_seconds"] = int(ticket.get("paused_seconds") or 0) + delta
                updates["paused_at"] = None
            if cmd.new_status == "En espera":
                updates["paused_at"] = now_iso
            if cmd.new_status == "En atención" and not ticket.get("first_response_at"):
                updates["first_response_at"] = now_iso
            if cmd.new_status == "Resuelto":
                updates["resolved_at"] = now_iso
                updates["diagnosis"] = (cmd.diagnosis or "").strip()
                updates["solution"] = (cmd.solution or "").strip()
                if cmd.closing_category:
                    updates["closing_category"] = cmd.closing_category
            if cmd.new_status == "Cerrado":
                updates["closed_at"] = now_iso

            updated = uow.tickets.update(
                ticket["id"], updates, expected_version=cmd.expected_version
            )
            action_label = (
                "Pausa SLA"
                if cmd.new_status == "En espera"
                else "Resolución técnica"
                if cmd.new_status == "Resuelto"
                else "Reapertura"
                if cmd.new_status == "Reabierto"
                else f"Cambio de estado a {cmd.new_status}"
            )
            uow.tickets.add_audit_event(
                {
                    "ticket_id": ticket["id"],
                    "actor_email": cmd.actor["email"],
                    "action": action_label,
                    "old_status": current_status,
                    "new_status": cmd.new_status,
                    "comment": (cmd.comment or cmd.diagnosis or f"Estado actualizado a {cmd.new_status}").strip(),
                    "created_at": now_iso,
                }
            )
            target_email = (
                ticket["requester_email"]
                if cmd.actor["email"] != ticket["requester_email"]
                else ticket.get("assigned_tech_email")
            )
            if target_email:
                uow.notifications.create(
                    {
                        "user_email": target_email,
                        "ticket_number": ticket["ticket_number"],
                        "title": f"Ticket {ticket['ticket_number']}: {cmd.new_status}",
                        "message": f"Actualizado por {cmd.actor['email']}.",
                        "category": "status",
                        "created_at": now_iso,
                    }
                )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TICKET_TRANSITION",
                    "entity": "tickets",
                    "entity_id": ticket["ticket_number"],
                    "old_value": current_status,
                    "new_value": cmd.new_status,
                }
            )
            uow.commit()

        assert updated is not None
        updated["sla_status"] = calculate_sla_status(updated)
        return updated


class RateTicketCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: RateTicketCommand) -> Dict[str, Any]:
        validate_csat_rating(cmd.csat_score, cmd.csat_comment)
        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            if int(ticket["requester_id"]) != int(cmd.actor["id"]) and cmd.actor.get("role") != "admin":
                raise ForbiddenError("Solo el solicitante dueño del ticket puede calificar el servicio.")

            now_iso = now_bogota().isoformat()
            old_status = ticket["status"]
            updates: Dict[str, Any] = {
                "csat_score": int(cmd.csat_score),
                "csat_comment": (cmd.csat_comment or "").strip() or None,
                "updated_at": now_iso,
            }
            if cmd.confirm_close and old_status == "Resuelto":
                updates["status"] = "Cerrado"
                updates["closed_at"] = now_iso
            elif old_status not in ("Resuelto", "Cerrado"):
                raise InvalidTransitionError(
                    "Solo puede confirmar cierre y calificar tickets en estado Resuelto o Cerrado."
                )

            updated = uow.tickets.update(
                ticket["id"], updates, expected_version=cmd.expected_version
            )
            assert updated is not None
            uow.tickets.add_audit_event(
                {
                    "ticket_id": ticket["id"],
                    "actor_email": cmd.actor["email"],
                    "action": "Cierre y Calificación CSAT",
                    "old_status": old_status,
                    "new_status": updated["status"],
                    "comment": f"Calificación: {cmd.csat_score}/5 estrellas. {cmd.csat_comment or ''}".strip(),
                    "created_at": now_iso,
                }
            )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TICKET_RATED_CLOSED",
                    "entity": "tickets",
                    "entity_id": ticket["ticket_number"],
                    "old_value": old_status,
                    "new_value": f"{updated['status']} | CSAT={cmd.csat_score}",
                }
            )
            uow.commit()

        updated["sla_status"] = calculate_sla_status(updated)
        return updated
