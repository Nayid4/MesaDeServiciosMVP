"""Router REST v1 de Base de Conocimiento (autoservicio, paginación y versionado)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.application.knowledge_base import (
    CompareKnowledgeArticleVersionsQuery,
    GetKbArticleDetailQuery,
    GetKnowledgeArticleVersionsQuery,
    ListKbArticlesPaginatedQuery,
    ListKnowledgeArticlesQuery,
    RestoreKnowledgeArticleVersionCommand,
    TransitionKnowledgeArticleCommand,
    UpsertKnowledgeArticleCommand,
)
from src.domain.rules import sanitize_kb_html
from src.infrastructure.composition import get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_optional_user,
    require_roles,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Base de Conocimiento ITIL v4"])


class UpsertKbRequest(BaseModel):
    article_id: Optional[int] = None
    code: str = ""
    title: str = Field(..., min_length=5)
    service_name: str
    category_topic: str = "General"
    symptoms: str
    probable_cause: str = ""
    solution_steps: str
    escalation_criteria: str = ""
    keywords: str
    visibility: str = "Pública"
    status: str = "En revisión"
    change_summary: str = ""
    source_ticket_id: Optional[int] = None


class TransitionKbRequest(BaseModel):
    action: str = Field(..., min_length=3)
    review_notes: Optional[str] = None
    restore_to_status: Optional[str] = None


class PreviewSanitizeKbRequest(BaseModel):
    symptoms: str = ""
    probable_cause: str = ""
    solution_steps: str = ""
    escalation_criteria: str = ""


@router.get("/kb")
def list_kb_articles(
    service_name: Optional[str] = None,
    category_topic: Optional[str] = None,
    status: Optional[str] = None,
    visibility: Optional[str] = None,
    q: Optional[str] = None,
    page: Optional[int] = Query(default=None, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    bus = get_cqrs_bus()
    if page is not None:
        paged = bus.query(
            ListKbArticlesPaginatedQuery(
                actor=current_user,
                page=page,
                page_size=page_size,
                service_name=service_name or None,
                category_topic=category_topic or None,
                status=status or None,
                visibility=visibility or None,
                search=q or None,
            )
        )
        return {**paged, "articles": paged["items"], "total_pages": paged["pages"]}

    articles = bus.query(
        ListKnowledgeArticlesQuery(
            actor=current_user,
            service_name=service_name or None,
            category_topic=category_topic or None,
            status=status or None,
            visibility=visibility or None,
            search=q or None,
        )
    )
    return {"articles": articles, "total": len(articles)}


@router.get("/kb/{article_id}")
def get_kb_article_detail(
    article_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        GetKbArticleDetailQuery(actor=current_user, article_id=article_id)
    )


@router.post("/kb/preview-sanitize")
def preview_sanitize_kb(
    payload: PreviewSanitizeKbRequest,
    _current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "admin"])),
) -> Dict[str, Any]:
    return {
        "symptoms": sanitize_kb_html(payload.symptoms),
        "probable_cause": sanitize_kb_html(payload.probable_cause),
        "solution_steps": sanitize_kb_html(payload.solution_steps),
        "escalation_criteria": sanitize_kb_html(payload.escalation_criteria),
    }


def _execute_upsert_kb(
    article_id: Optional[int],
    payload: UpsertKbRequest,
    request: Request,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    art = get_cqrs_bus().execute(
        UpsertKnowledgeArticleCommand(
            actor=current_user,
            article_id=article_id,
            code=payload.code,
            title=payload.title,
            service_name=payload.service_name,
            category_topic=payload.category_topic,
            symptoms=payload.symptoms,
            probable_cause=payload.probable_cause,
            solution_steps=payload.solution_steps,
            escalation_criteria=payload.escalation_criteria,
            keywords=payload.keywords,
            visibility=payload.visibility,
            status=payload.status,
            change_summary=payload.change_summary,
            source_ticket_id=payload.source_ticket_id,
            ip_address=get_client_ip(request),
        )
    )
    return {"article": art}


@router.post("/kb", status_code=201)
def upsert_kb_article(
    payload: UpsertKbRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "admin"])),
) -> Dict[str, Any]:
    return _execute_upsert_kb(payload.article_id, payload, request, current_user)


@router.put("/kb/{article_id}")
def update_kb_article(
    article_id: int,
    payload: UpsertKbRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "admin"])),
) -> Dict[str, Any]:
    return _execute_upsert_kb(article_id, payload, request, current_user)


@router.post("/kb/{article_id}/transition")
def transition_kb_article(
    article_id: int,
    payload: TransitionKbRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "admin"])),
) -> Dict[str, Any]:
    art = get_cqrs_bus().execute(
        TransitionKnowledgeArticleCommand(
            actor=current_user,
            article_id=article_id,
            action=payload.action,
            review_notes=payload.review_notes,
            restore_to_status=payload.restore_to_status,
            ip_address=get_client_ip(request),
        )
    )
    return {"article": art}


@router.get("/kb/{article_id}/versions")
def list_kb_article_versions(
    article_id: int,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        GetKnowledgeArticleVersionsQuery(actor=current_user, article_id=article_id)
    )


@router.get("/kb/{article_id}/versions/compare")
def compare_kb_article_versions(
    article_id: int,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "director", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        CompareKnowledgeArticleVersionsQuery(
            actor=current_user,
            article_id=article_id,
            from_version=from_version,
            to_version=to_version,
        )
    )


@router.post("/kb/{article_id}/versions/{version_number}/restore")
def restore_kb_article_version(
    article_id: int,
    version_number: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["tecnico", "coordinador", "admin"])),
) -> Dict[str, Any]:
    art = get_cqrs_bus().execute(
        RestoreKnowledgeArticleVersionCommand(
            actor=current_user,
            article_id=article_id,
            version_number=version_number,
            ip_address=get_client_ip(request),
        )
    )
    return {"article": art}
