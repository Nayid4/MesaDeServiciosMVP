"""Mixin SQLAlchemy para consultas paginadas, filtros y bitácora de tickets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, case, desc, func, or_, select

from src.domain.common.pagination import PageRequest, PagedResult
from src.domain.rules import now_bogota
from src.infrastructure.persistence.models import TicketAuditEventORM, TicketORM
from src.infrastructure.persistence.repositories.base import (
    execute_paginated_query,
    model_to_dict,
)


class TicketQueriesMixin:
    """Provee listados filtrados, ordenamiento, paginación SQL y auditoría de tickets."""

    session: Any

    def _build_filtered_stmt(
        self,
        *,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        unassigned_only: bool = False,
        sort_by: Optional[str] = None,
    ) -> Any:
        stmt = select(TicketORM)
        if requester_id is not None:
            stmt = stmt.where(TicketORM.requester_id == int(requester_id))
        if assigned_tech_id is not None:
            stmt = stmt.where(TicketORM.assigned_tech_id == int(assigned_tech_id))
        if unassigned_only:
            stmt = stmt.where(TicketORM.assigned_tech_id.is_(None))
        if area:
            stmt = stmt.where(TicketORM.area == area)
        if status:
            stmt = stmt.where(TicketORM.status == status)
        if priority:
            stmt = stmt.where(TicketORM.priority == priority)
        if sede:
            stmt = stmt.where(TicketORM.sede == sede)
        if service_name:
            stmt = stmt.where(TicketORM.service_name == service_name)
        if search:
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(TicketORM.ticket_number).like(like),
                    func.lower(func.coalesce(TicketORM.legacy_ticket_number, "")).like(like),
                    func.lower(TicketORM.title).like(like),
                    func.lower(TicketORM.description).like(like),
                )
            )
        if sort_by == "priority":
            prio_rank = case(
                (TicketORM.priority == "P1", 1),
                (TicketORM.priority == "P2", 2),
                (TicketORM.priority == "P3", 3),
                (TicketORM.priority == "P4", 4),
                else_=5,
            )
            return stmt.order_by(asc(prio_rank), asc(TicketORM.resolution_deadline), desc(TicketORM.id))
        if sort_by == "sla":
            return stmt.order_by(asc(TicketORM.resolution_deadline), desc(TicketORM.id))
        return stmt.order_by(desc(TicketORM.id))

    def list_tickets(
        self,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            requester_id=requester_id,
            assigned_tech_id=assigned_tech_id,
            area=area,
            status=status,
            priority=priority,
            sede=sede,
            service_name=service_name,
            search=search,
        ).limit(limit)
        return [model_to_dict(t) for t in self.session.scalars(stmt).all()]

    def list_tickets_paginated(
        self,
        page_request: PageRequest,
        *,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        unassigned_only: bool = False,
        sort_by: Optional[str] = None,
    ) -> PagedResult[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            requester_id=requester_id,
            assigned_tech_id=assigned_tech_id,
            area=area,
            status=status,
            priority=priority,
            sede=sede,
            service_name=service_name,
            search=search,
            unassigned_only=unassigned_only,
            sort_by=sort_by,
        )
        return execute_paginated_query(self.session, stmt, TicketORM.id, page_request)

    def add_audit_event(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        obj = TicketAuditEventORM(
            ticket_id=int(entry["ticket_id"]),
            actor_email=entry["actor_email"],
            action=entry["action"],
            old_status=entry.get("old_status"),
            new_status=entry.get("new_status"),
            comment=entry.get("comment"),
            created_at=entry.get("created_at") or now_bogota().isoformat(),
        )
        self.session.add(obj)
        self.session.flush()
        return model_to_dict(obj)

    def get_audit_events(self, ticket_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(TicketAuditEventORM)
            .where(TicketAuditEventORM.ticket_id == int(ticket_id))
            .order_by(asc(TicketAuditEventORM.id))
        )
        return [model_to_dict(e) for e in self.session.scalars(stmt).all()]
