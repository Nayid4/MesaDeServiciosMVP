"""Router REST v1 de Tickets ITIL v4: bandeja paginada, creación y transiciones."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, Field

from src.application.tickets import (
    AdjustPriorityCommand,
    CreateTicketCommand,
    GetTicketDetailQuery,
    ListTicketsPaginatedQuery,
    ListTicketsQuery,
    RateTicketCommand,
    ReassignTicketCommand,
    TransitionTicketCommand,
    compute_technician_workloads,
)
from src.infrastructure.composition import create_uow, get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_current_user,
    get_ticket_actor,
    require_roles,
)

router = APIRouter(prefix="/api/v1/tickets", tags=["Gestión de Tickets ITIL v4"])


class CreateTicketRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    ticket_type: Optional[str] = None
    service_name: str
    sede: str
    location: str
    urgency: str = "Media"
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_human_validated: bool = False
    initial_transcript: Optional[str] = None


class TransitionTicketRequest(BaseModel):
    new_status: str
    comment: Optional[str] = None
    diagnosis: Optional[str] = None
    solution: Optional[str] = None
    closing_category: Optional[str] = None
    version: Optional[int] = Field(default=None, ge=1)


class ReassignTicketRequest(BaseModel):
    new_tech_id: int
    reason: str = Field(..., min_length=1)
    version: Optional[int] = Field(default=None, ge=1)


class AdjustPriorityRequest(BaseModel):
    impact: str
    urgency: str
    justification: str = Field(..., min_length=1)
    version: Optional[int] = Field(default=None, ge=1)


class RateTicketRequest(BaseModel):
    csat_score: int = Field(..., ge=1, le=5)
    csat_comment: Optional[str] = None
    confirm_close: bool = True
    version: Optional[int] = Field(default=None, ge=1)


@router.get("")
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    sede: Optional[str] = None,
    service_name: Optional[str] = None,
    q: Optional[str] = None,
    unassigned_only: bool = False,
    sla_risk_only: bool = False,
    sort_by: str = "priority_asc_deadline_asc",
    page: Optional[int] = Query(default=None, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    bus = get_cqrs_bus()
    tech_loads: List[Dict[str, Any]] = []
    if current_user.get("role") in ("coordinador", "admin", "director"):
        with create_uow() as uow:
            tech_loads = compute_technician_workloads(uow)

    if page is not None and not sla_risk_only:
        paged = bus.query(
            ListTicketsPaginatedQuery(
                actor=current_user,
                page=page,
                page_size=page_size or 10,
                status=status or None,
                priority=priority or None,
                sede=sede or None,
                service_name=service_name or None,
                search=q or None,
                unassigned_only=unassigned_only,
                sort_by=sort_by,
            )
        )
        return {
            **paged,
            "tickets": paged["items"],
            "total_pages": paged["pages"],
            "technician_loads": tech_loads,
        }

    items = bus.query(
        ListTicketsQuery(
            actor=current_user,
            status=status or None,
            priority=priority or None,
            sede=sede or None,
            service_name=service_name or None,
            search=q or None,
            unassigned_only=unassigned_only,
            sla_risk_only=sla_risk_only,
            sort_by=sort_by,
        )
    )
    total = len(items)
    if page is not None and page_size is not None:
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        paged_slice = items[start : start + page_size]
        return {
            "tickets": paged_slice,
            "items": paged_slice,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": total_pages,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "technician_loads": tech_loads,
        }
    return {"tickets": items, "total": total, "technician_loads": tech_loads}


@router.post("", status_code=201)
def create_ticket(
    payload: CreateTicketRequest,
    request: Request,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    result = get_cqrs_bus().execute(
        CreateTicketCommand(
            actor=current_user,
            title=payload.title,
            description=payload.description,
            ticket_type=payload.ticket_type or "Incidencia",
            service_name=payload.service_name,
            sede=payload.sede,
            location=payload.location,
            urgency=payload.urgency,
            ai_suggested_service=payload.ai_suggested_service,
            ai_confidence=payload.ai_confidence,
            ai_human_validated=payload.ai_human_validated,
            initial_transcript=payload.initial_transcript,
            idempotency_key=idempotency_key,
            ip_address=get_client_ip(request),
        )
    )
    if result.get("deduplicated"):
        response.status_code = 200
    return result


@router.get("/{ticket_id}")
def get_ticket_detail(
    ticket_id: int,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetTicketDetailQuery(actor=current_actor, ticket_id=ticket_id))


@router.post("/{ticket_id}/transition")
def transition_ticket(
    ticket_id: int,
    payload: TransitionTicketRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        TransitionTicketCommand(
            actor=current_user,
            ticket_id=ticket_id,
            new_status=payload.new_status,
            comment=payload.comment,
            diagnosis=payload.diagnosis,
            solution=payload.solution,
            closing_category=payload.closing_category,
            expected_version=payload.version,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/{ticket_id}/reassign")
def reassign_ticket(
    ticket_id: int,
    payload: ReassignTicketRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        ReassignTicketCommand(
            actor=current_user,
            ticket_id=ticket_id,
            new_tech_id=payload.new_tech_id,
            reason=payload.reason,
            expected_version=payload.version,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/{ticket_id}/priority")
def adjust_ticket_priority(
    ticket_id: int,
    payload: AdjustPriorityRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        AdjustPriorityCommand(
            actor=current_user,
            ticket_id=ticket_id,
            impact=payload.impact,
            urgency=payload.urgency,
            justification=payload.justification,
            expected_version=payload.version,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/{ticket_id}/rate")
def rate_ticket(
    ticket_id: int,
    payload: RateTicketRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        RateTicketCommand(
            actor=current_user,
            ticket_id=ticket_id,
            csat_score=payload.csat_score,
            csat_comment=payload.csat_comment,
            confirm_close=payload.confirm_close,
            expected_version=payload.version,
            ip_address=get_client_ip(request),
        )
    )
