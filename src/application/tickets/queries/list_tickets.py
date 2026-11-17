"""Consultas CQRS de bandeja de tickets (estándar y paginada con SQL LIMIT/OFFSET)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.application.common import Query
from src.application.common.cqrs_bus import serialize_paged_result
from src.domain.common.pagination import PageRequest, PagedResult
from src.domain.ports import IUnitOfWork
from src.domain.rules import calculate_sla_status


@dataclass(frozen=True)
class ListTicketsQuery(Query):
    actor: Dict[str, Any]
    status: Optional[str] = None
    priority: Optional[str] = None
    sede: Optional[str] = None
    service_name: Optional[str] = None
    search: Optional[str] = None
    unassigned_only: bool = False
    sla_risk_only: bool = False
    sort_by: str = "priority_asc_deadline_asc"
    limit: int = 300


@dataclass(frozen=True)
class ListTicketsPaginatedQuery(Query):
    actor: Dict[str, Any]
    page: int = 1
    page_size: int = 10
    status: Optional[str] = None
    priority: Optional[str] = None
    sede: Optional[str] = None
    service_name: Optional[str] = None
    search: Optional[str] = None
    unassigned_only: bool = False
    sort_by: str = "priority"


def _actor_ticket_scope(actor: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    role = actor.get("role")
    if role == "usuario":
        return int(actor["id"]), None
    if role == "tecnico":
        return None, int(actor["id"])
    return None, None


class ListTicketsQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListTicketsQuery) -> List[Dict[str, Any]]:
        requester_id, assigned_tech_id = _actor_ticket_scope(query.actor)
        with self._uow_factory() as uow:
            rows = uow.tickets.list_tickets(
                requester_id=requester_id,
                assigned_tech_id=assigned_tech_id,
                status=query.status,
                priority=query.priority,
                sede=query.sede,
                service_name=query.service_name,
                search=query.search,
                limit=query.limit,
            )

        for row in rows:
            row["sla_status"] = calculate_sla_status(row)

        if query.unassigned_only:
            rows = [
                r
                for r in rows
                if not r.get("assigned_tech_id") or r.get("status") == "Registrado"
            ]
        if query.sla_risk_only:
            rows = [
                r
                for r in rows
                if (r.get("sla_status") or {}).get("semaphore") in ("Amarillo", "Rojo")
                or r.get("priority") == "P1 Crítica"
            ]

        prio_rank = {"P1 Crítica": 1, "P2 Alta": 2, "P3 Media": 3, "P4 Baja": 4}
        sort_by = (query.sort_by or "priority_asc_deadline_asc").strip().lower()
        if sort_by == "deadline_asc":
            rows.sort(
                key=lambda r: (
                    1 if r.get("status") in ("Cerrado", "Anulado", "Resuelto") else 0,
                    float((r.get("sla_status") or {}).get("remaining_hours", 9999.0)),
                    prio_rank.get(r.get("priority", ""), 9),
                    -int(r["id"]),
                )
            )
        elif sort_by == "priority_asc":
            rows.sort(
                key=lambda r: (
                    prio_rank.get(r.get("priority", ""), 9),
                    float((r.get("sla_status") or {}).get("remaining_hours", 9999.0)),
                    -int(r["id"]),
                )
            )
        elif sort_by == "created_desc":
            rows.sort(key=lambda r: -int(r["id"]))
        else:
            rows.sort(
                key=lambda r: (
                    1 if r.get("status") in ("Cerrado", "Anulado", "Resuelto") else 0,
                    prio_rank.get(r.get("priority", ""), 9),
                    float((r.get("sla_status") or {}).get("remaining_hours", 9999.0)),
                    -int(r["id"]),
                )
            )
        return rows


class ListTicketsPaginatedQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListTicketsPaginatedQuery) -> Dict[str, Any]:
        requester_id, assigned_tech_id = _actor_ticket_scope(query.actor)
        page_req = PageRequest(page=query.page, page_size=query.page_size)
        sql_sort = (
            "sla"
            if "deadline" in (query.sort_by or "")
            else "priority"
            if "priority" in (query.sort_by or "")
            else None
        )
        with self._uow_factory() as uow:
            paged = uow.tickets.list_tickets_paginated(
                page_req,
                requester_id=requester_id,
                assigned_tech_id=assigned_tech_id,
                status=query.status,
                priority=query.priority,
                sede=query.sede,
                service_name=query.service_name,
                search=query.search,
                unassigned_only=query.unassigned_only,
                sort_by=sql_sort,
            )

        for row in paged.items:
            row["sla_status"] = calculate_sla_status(row)

        return serialize_paged_result(
            PagedResult(
                items=paged.items,
                total=paged.total,
                page=paged.page,
                page_size=paged.page_size,
                pages=paged.pages,
            )
        )
