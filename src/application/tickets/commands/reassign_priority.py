"""Casos de uso CQRS de reasignación de técnico y ajuste de prioridad OR-03."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.domain.exceptions import (
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import calculate_sla_status, now_bogota, parse_iso_datetime
from src.domain.value_objects import PriorityMatrix, SLADeadline


@dataclass(frozen=True)
class ReassignTicketCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    new_tech_id: int
    reason: str
    expected_version: Optional[int] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class AdjustPriorityCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    impact: str
    urgency: str
    justification: str
    expected_version: Optional[int] = None
    ip_address: str = "127.0.0.1"


class ReassignTicketCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: ReassignTicketCommand) -> Dict[str, Any]:
        if cmd.actor.get("role") not in ("coordinador", "admin"):
            raise ForbiddenError("Solo Coordinador o Administrador pueden reasignar tickets.")
        if not cmd.reason or len(cmd.reason.strip()) < 5:
            raise ValidationDomainError(
                "La reasignación exige un motivo justificativo obligatorio (mínimo 5 caracteres)."
            )

        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError("No se puede reasignar un ticket cerrado o anulado.")

            tech = uow.users.get_by_id(cmd.new_tech_id)
            if not tech or tech["role"] != "tecnico" or not bool(tech.get("is_active", True)):
                raise ValidationDomainError("El técnico seleccionado no existe o no está activo.")

            now_iso = now_bogota().isoformat()
            prev_tech = ticket.get("assigned_tech_email") or "Sin asignar"
            new_status = "Asignado" if ticket["status"] == "Registrado" else ticket["status"]

            updated = uow.tickets.update(
                ticket["id"],
                {
                    "assigned_tech_id": int(tech["id"]),
                    "assigned_tech_email": tech["email"],
                    "area": tech.get("area") or ticket["area"],
                    "status": new_status,
                    "updated_at": now_iso,
                },
                expected_version=cmd.expected_version,
            )
            uow.users.update(int(tech["id"]), {"last_assigned_at": now_iso})
            uow.tickets.add_audit_event(
                {
                    "ticket_id": ticket["id"],
                    "actor_email": cmd.actor["email"],
                    "action": "Reasignación",
                    "old_status": ticket["status"],
                    "new_status": new_status,
                    "comment": f"De {prev_tech} a {tech['email']}. Motivo: {cmd.reason.strip()} (SLA intacto).",
                    "created_at": now_iso,
                }
            )
            uow.notifications.create(
                {
                    "user_email": tech["email"],
                    "ticket_number": ticket["ticket_number"],
                    "title": f"Ticket reasignado: {ticket['ticket_number']}",
                    "message": f"Motivo: {cmd.reason.strip()}",
                    "created_at": now_iso,
                }
            )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TICKET_REASSIGNED",
                    "entity": "tickets",
                    "entity_id": ticket["ticket_number"],
                    "old_value": prev_tech,
                    "new_value": f"{tech['email']} | {cmd.reason.strip()}",
                }
            )
            uow.commit()

        assert updated is not None
        updated["sla_status"] = calculate_sla_status(updated)
        return updated


class AdjustPriorityCommandHandler:
    """Ajusta Impacto/Urgencia bajo matriz OR-03 con justificación obligatoria (RF-05)."""

    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: AdjustPriorityCommand) -> Dict[str, Any]:
        if cmd.actor.get("role") not in ("coordinador", "admin"):
            raise ForbiddenError("Solo Coordinador o Administrador pueden ajustar la prioridad de un ticket.")
        if not cmd.justification or len(cmd.justification.strip()) < 10:
            raise ValidationDomainError(
                "El ajuste de prioridad exige una justificación obligatoria de al menos 10 caracteres."
            )

        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError("No se puede ajustar la prioridad de un ticket cerrado o anulado.")

            try:
                prio_matrix = PriorityMatrix.evaluate(
                    impact=cmd.impact,
                    urgency=cmd.urgency,
                    custom_sla_table=uow.catalog.get_sla_table() or None,
                )
            except ValueError as exc:
                raise ValidationDomainError(str(exc)) from exc

            created_dt = parse_iso_datetime(ticket.get("created_at")) or now_bogota()
            sla_deadline = SLADeadline.compute(prio_matrix, created_at=created_dt)
            now_iso = now_bogota().isoformat()
            old_prio = f"{ticket['priority']} ({ticket['impact']}x{ticket['urgency']})"
            new_prio = f"{prio_matrix.priority} ({prio_matrix.impact}x{prio_matrix.urgency})"

            updated = uow.tickets.update(
                ticket["id"],
                {
                    "impact": prio_matrix.impact,
                    "urgency": prio_matrix.urgency,
                    "priority": prio_matrix.priority,
                    "sla_response_hours": prio_matrix.sla_response_hours,
                    "sla_resolution_hours": prio_matrix.sla_resolution_hours,
                    "response_deadline": sla_deadline.response_deadline.isoformat(),
                    "resolution_deadline": sla_deadline.resolution_deadline.isoformat(),
                    "priority_justification": cmd.justification.strip(),
                    "updated_at": now_iso,
                },
                expected_version=cmd.expected_version,
            )
            uow.tickets.add_audit_event(
                {
                    "ticket_id": ticket["id"],
                    "actor_email": cmd.actor["email"],
                    "action": "Ajuste de prioridad OR-03",
                    "old_status": ticket["status"],
                    "new_status": ticket["status"],
                    "comment": f"De {old_prio} a {new_prio}. Justificación: {cmd.justification.strip()}",
                    "created_at": now_iso,
                }
            )
            for recipient in {ticket.get("requester_email"), ticket.get("assigned_tech_email")}:
                if recipient:
                    uow.notifications.create(
                        {
                            "user_email": recipient,
                            "ticket_number": ticket["ticket_number"],
                            "title": f"Prioridad ajustada en {ticket['ticket_number']}: {prio_matrix.priority}",
                            "message": f"Justificación: {cmd.justification.strip()}",
                            "category": "status",
                            "created_at": now_iso,
                        }
                    )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TICKET_PRIORITY_ADJUSTED",
                    "entity": "tickets",
                    "entity_id": ticket["ticket_number"],
                    "old_value": old_prio,
                    "new_value": f"{new_prio} | {cmd.justification.strip()}",
                }
            )
            uow.commit()

        assert updated is not None
        updated["sla_status"] = calculate_sla_status(updated)
        return updated
