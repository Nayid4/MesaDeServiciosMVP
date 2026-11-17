"""Router REST v1 público de Tickets: catálogo, resumen SPOC, lookup invitado y preview IA."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.application.tickets import (
    GetPublicSummaryQuery,
    GetPublicTicketQuery,
    PublicTicketLookupCommand,
)
from src.domain.rules import (
    ALL_TICKET_STATUSES,
    CLOSING_CATEGORIES,
    KB_ARTICLE_STATUSES,
    KB_CATEGORIES,
    KB_VISIBILITIES,
    SLA_BY_PRIORITY,
    UPC_LOCATIONS,
    UPC_SEDES,
    UPC_SERVICE_CATALOG,
)
from src.domain.value_objects import PriorityMatrix
from src.infrastructure.composition import create_uow, get_ai_engine, get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import get_client_ip, get_current_user

router = APIRouter(prefix="/api/v1/tickets", tags=["Consulta Pública y Catálogo Tickets"])


class ClassifyPreviewRequest(BaseModel):
    title: str = ""
    description: str = ""
    simulate_failure: bool = False


class PublicTicketLookupRequest(BaseModel):
    ticket_code: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    otp_code: Optional[str] = None


@router.get("/catalog")
def get_catalog() -> Dict[str, Any]:
    with create_uow() as uow:
        services = uow.catalog.list_services(active_only=True)
        sla_table = uow.catalog.get_sla_table() or SLA_BY_PRIORITY
    return {
        "services": services
        or [{"service_name": k, **v, "is_active": True} for k, v in UPC_SERVICE_CATALOG.items()],
        "sedes": UPC_SEDES,
        "locations": UPC_LOCATIONS,
        "statuses": list(ALL_TICKET_STATUSES),
        "priorities": list(SLA_BY_PRIORITY.keys()),
        "closing_categories": CLOSING_CATEGORIES,
        "sla_levels": sla_table,
        "kb_categories": list(KB_CATEGORIES),
        "kb_statuses": list(KB_ARTICLE_STATUSES),
        "kb_visibilities": list(KB_VISIBILITIES),
    }


@router.get("/public-summary")
def get_public_summary() -> Dict[str, Any]:
    return get_cqrs_bus().query(GetPublicSummaryQuery())


@router.post("/public/lookup")
def public_ticket_lookup(payload: PublicTicketLookupRequest, request: Request) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        PublicTicketLookupCommand(
            ticket_code=payload.ticket_code,
            email=payload.email,
            otp_code=payload.otp_code,
            ip_address=get_client_ip(request),
        )
    )


@router.get("/public/{ticket_code}")
def get_public_ticket(ticket_code: str) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetPublicTicketQuery(ticket_number=ticket_code))


@router.post("/classify-preview")
def classify_ticket_preview(
    payload: ClassifyPreviewRequest,
    _user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    combined = f"{payload.title} | {payload.description}".strip(" |")
    ai_engine = get_ai_engine()
    pred = ai_engine.classify_text(combined, simulate_failure=payload.simulate_failure)
    svc = pred["predicted_service"]
    prio = PriorityMatrix.evaluate(
        impact=UPC_SERVICE_CATALOG.get(svc, {}).get("base_impact", "Medio"),
        urgency=pred["predicted_urgency"],
    )
    with create_uow() as uow:
        pub_articles = uow.kb_articles.list_articles(visibility="Pública", status="Publicado")
    return {
        **pred,
        "estimated_impact": prio.impact,
        "estimated_priority": prio.priority,
        "estimated_area": UPC_SERVICE_CATALOG.get(svc, {}).get("area"),
        "estimated_sla_hours": prio.sla_resolution_hours,
        "suggested_articles": (
            ai_engine.search_knowledge_base(combined, pub_articles, top_k=3, min_similarity=0.18)
            if combined
            else []
        ),
    }
