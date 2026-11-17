"""Consultas CQRS de detalle de ticket, mensajes de chat, vista pública y resumen."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from src.application.common import Query
from src.application.tickets.ticket_helpers import (
    authorize_ticket_access,
    sanitize_for_guest,
)
from src.domain.exceptions import NotFoundError
from src.domain.ports import IUnitOfWork
from src.domain.rules import (
    ASSIGNED_LOAD_STATUSES,
    VALID_TRANSITIONS,
    calculate_sla_status,
    mask_email,
)
from src.domain.value_objects import TicketCode
from src.metrics import compute_itil_kpis


@dataclass(frozen=True)
class ListTicketMessagesQuery(Query):
    actor: Dict[str, Any]
    ticket_id: int
    after_id: int = 0


@dataclass(frozen=True)
class GetTicketDetailQuery(Query):
    actor: Dict[str, Any]
    ticket_id: int


@dataclass(frozen=True)
class GetPublicTicketQuery(Query):
    ticket_number: str


@dataclass(frozen=True)
class GetPublicSummaryQuery(Query):
    pass


def compute_technician_workloads(uow: IUnitOfWork) -> List[Dict[str, Any]]:
    """Calcula la carga actual de tickets abiertos por técnico activo."""
    techs = uow.users.list_users(role="tecnico", is_active=True)
    all_tickets = uow.tickets.list_tickets(limit=1000)
    open_by_tech: Dict[int, int] = {}
    for t in all_tickets:
        tid = t.get("assigned_tech_id")
        if tid is not None and t.get("status") in ASSIGNED_LOAD_STATUSES:
            open_by_tech[int(tid)] = open_by_tech.get(int(tid), 0) + 1
    loads = [
        {
            "id": int(u["id"]),
            "email": u["email"],
            "full_name": u["full_name"],
            "area": u.get("area"),
            "sede": u.get("sede"),
            "open_tickets_count": open_by_tech.get(int(u["id"]), 0),
        }
        for u in techs
    ]
    loads.sort(key=lambda x: (x["open_tickets_count"], x["full_name"]))
    return loads


class ListTicketMessagesQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListTicketMessagesQuery) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            ticket = uow.tickets.get_by_id(query.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{query.ticket_id} no encontrado.")
            authorize_ticket_access(query.actor, ticket)
            msgs = uow.tickets.get_messages(ticket["id"], after_id=query.after_id)

        if query.actor.get("role") == "invitado":
            for m in msgs:
                m["sender_email"] = mask_email(m.get("sender_email", ""))

        return {
            "ticket_id": ticket["id"],
            "chat_read_only": ticket["status"] in ("Cerrado", "Anulado"),
            "messages": msgs,
        }


class GetTicketDetailQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetTicketDetailQuery) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            ticket = uow.tickets.get_by_id(query.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{query.ticket_id} no encontrado.")
            authorize_ticket_access(query.actor, ticket)

            audit_events = uow.tickets.get_audit_events(ticket["id"])
            messages = uow.tickets.get_messages(ticket["id"])
            uow.tickets.mark_messages_read(ticket["id"], query.actor["email"])
            uow.commit()
            techs = compute_technician_workloads(uow)

        ticket["sla_status"] = calculate_sla_status(ticket)
        if query.actor.get("role") == "invitado":
            clean_ticket, clean_events, clean_messages = sanitize_for_guest(
                ticket, audit_events, messages
            )
            return {
                "ticket": clean_ticket,
                "audit_events": clean_events,
                "messages": clean_messages,
                "valid_transitions": [],
                "chat_read_only": ticket["status"] in ("Cerrado", "Anulado"),
                "available_technicians": [],
            }
        return {
            "ticket": ticket,
            "audit_events": audit_events,
            "messages": messages,
            "valid_transitions": VALID_TRANSITIONS.get(ticket["status"], []),
            "chat_read_only": ticket["status"] in ("Cerrado", "Anulado"),
            "available_technicians": techs,
        }


class GetPublicTicketQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetPublicTicketQuery) -> Dict[str, Any]:
        TicketCode(query.ticket_number)
        code = query.ticket_number.strip().upper()
        with self._uow_factory() as uow:
            ticket = uow.tickets.get_by_number(code)
            if not ticket:
                raise NotFoundError(f"No existe ningún ticket registrado con el radicado {code}.")
            events = uow.tickets.get_audit_events(ticket["id"])

        sanitized_timeline = [
            {
                "action": e["action"],
                "old_status": e.get("old_status"),
                "new_status": e.get("new_status"),
                "comment": re.sub(
                    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                    "[correo protegido]",
                    e.get("comment") or "",
                ),
                "created_at": e["created_at"],
            }
            for e in events
        ]
        return {
            "ticket_number": ticket["ticket_number"],
            "legacy_ticket_number": ticket.get("legacy_ticket_number"),
            "title": ticket["title"],
            "service_name": ticket["service_name"],
            "area": ticket["area"],
            "sede": ticket["sede"],
            "location": ticket["location"],
            "priority": ticket["priority"],
            "status": ticket["status"],
            "sla_status": calculate_sla_status(ticket),
            "created_at": ticket["created_at"],
            "resolution_deadline": ticket.get("resolution_deadline"),
            "timeline": sanitized_timeline,
        }


class GetPublicSummaryQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, _query: GetPublicSummaryQuery) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            tickets = uow.tickets.list_tickets(limit=1000)
            services = uow.catalog.list_services(active_only=True)
            sla_table = uow.catalog.get_sla_table()

        kpis = compute_itil_kpis(tickets)
        return {
            "metrics": {
                "total_tickets": kpis["total_tickets"],
                "resolved_or_closed": kpis["resolved_or_closed"],
                "sla_compliance_pct": kpis["sla_compliance_pct"],
                "avg_first_response_min": kpis["avg_first_response_min"],
                "avg_csat": kpis["avg_csat"],
            },
            "services": services,
            "sla_levels": sla_table,
        }
