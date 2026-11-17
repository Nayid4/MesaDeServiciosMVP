"""Consultas CQRS de Base de Conocimiento (estándar, paginada SQL, detalle y versiones)."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.application.common import Query
from src.application.common.cqrs_bus import serialize_paged_result
from src.domain.common.pagination import PageRequest
from src.domain.exceptions import ForbiddenError, NotFoundError
from src.domain.ports import IUnitOfWork


@dataclass(frozen=True)
class ListKnowledgeArticlesQuery(Query):
    actor: Optional[Dict[str, Any]] = None
    service_name: Optional[str] = None
    category_topic: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    search: Optional[str] = None


@dataclass(frozen=True)
class ListKbArticlesPaginatedQuery(Query):
    actor: Optional[Dict[str, Any]] = None
    page: int = 1
    page_size: int = 10
    service_name: Optional[str] = None
    category_topic: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = None
    search: Optional[str] = None


@dataclass(frozen=True)
class GetKbArticleDetailQuery(Query):
    actor: Optional[Dict[str, Any]]
    article_id: int


@dataclass(frozen=True)
class GetKnowledgeArticleVersionsQuery(Query):
    actor: Optional[Dict[str, Any]]
    article_id: int


@dataclass(frozen=True)
class CompareKnowledgeArticleVersionsQuery(Query):
    actor: Optional[Dict[str, Any]]
    article_id: int
    from_version: int
    to_version: int


def _resolve_kb_visibility(actor: Optional[Dict[str, Any]], visibility: Optional[str], status: Optional[str]):
    role = actor.get("role") if actor else "public"
    if role in ("usuario", "public", "invitado"):
        return "Pública", "Publicado"
    return visibility or None, status or None


class ListKnowledgeArticlesQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListKnowledgeArticlesQuery) -> List[Dict[str, Any]]:
        visibility, status = _resolve_kb_visibility(query.actor, query.visibility, query.status)
        with self._uow_factory() as uow:
            articles = uow.kb_articles.list_articles(
                visibility=visibility,
                status=status,
                service_name=query.service_name,
                category_topic=query.category_topic,
            )
        if query.search and query.search.strip():
            needle = query.search.strip().lower()
            articles = [
                a
                for a in articles
                if needle in (a.get("title") or "").lower()
                or needle in (a.get("symptoms") or "").lower()
                or needle in (a.get("probable_cause") or "").lower()
                or needle in (a.get("solution_steps") or "").lower()
                or needle in (a.get("escalation_criteria") or "").lower()
                or needle in (a.get("keywords") or "").lower()
                or needle in (a.get("category_topic") or "").lower()
                or needle in (a.get("code") or "").lower()
            ]
        return articles


class ListKbArticlesPaginatedQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListKbArticlesPaginatedQuery) -> Dict[str, Any]:
        visibility, status = _resolve_kb_visibility(query.actor, query.visibility, query.status)
        page_req = PageRequest(page=query.page, page_size=query.page_size)
        with self._uow_factory() as uow:
            paged = uow.kb_articles.list_articles_paginated(
                page_req,
                visibility=visibility,
                status=status,
                service_name=query.service_name,
                category_topic=query.category_topic,
                search=query.search,
            )
        return serialize_paged_result(paged)


class GetKbArticleDetailQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetKbArticleDetailQuery) -> Dict[str, Any]:
        role = query.actor.get("role") if query.actor else "public"
        with self._uow_factory() as uow:
            art = uow.kb_articles.get_by_id(query.article_id)
            if not art:
                raise NotFoundError(f"Artículo KB #{query.article_id} no encontrado.")
            if role in ("usuario", "public", "invitado") and (
                art.get("visibility") != "Pública" or art.get("status") != "Publicado"
            ):
                raise ForbiddenError("No tiene permisos para consultar este artículo KB.")
            versions = uow.kb_articles.list_versions(query.article_id)
        return {"article": art, "versions": versions}


class GetKnowledgeArticleVersionsQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetKnowledgeArticleVersionsQuery) -> Dict[str, Any]:
        return GetKbArticleDetailQueryHandler(self._uow_factory).handle(
            GetKbArticleDetailQuery(actor=query.actor, article_id=query.article_id)
        )


class CompareKnowledgeArticleVersionsQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: CompareKnowledgeArticleVersionsQuery) -> Dict[str, Any]:
        role = query.actor.get("role") if query.actor else "public"
        if role not in ("tecnico", "coordinador", "director", "admin"):
            raise ForbiddenError("Acceso restringido para comparar versiones editoriales KB.")

        with self._uow_factory() as uow:
            art = uow.kb_articles.get_by_id(query.article_id)
            if not art:
                raise NotFoundError(f"Artículo KB #{query.article_id} no encontrado.")
            v_from = uow.kb_articles.get_version(query.article_id, query.from_version)
            v_to = uow.kb_articles.get_version(query.article_id, query.to_version)
            if not v_from or not v_to:
                raise NotFoundError("Una o ambas versiones solicitadas no existen en el historial.")

        fields = [
            ("title", "Título"),
            ("service_name", "Servicio"),
            ("category_topic", "Categoría"),
            ("symptoms", "Síntomas"),
            ("probable_cause", "Causa probable"),
            ("solution_steps", "Pasos de solución"),
            ("escalation_criteria", "Cuándo escalar"),
            ("keywords", "Etiquetas"),
            ("visibility", "Visibilidad"),
            ("status", "Estado"),
        ]
        differences: List[Dict[str, Any]] = []
        for field_key, label in fields:
            old_val = str(v_from.get(field_key) or "")
            new_val = str(v_to.get(field_key) or "")
            if old_val != new_val:
                differences.append(
                    {
                        "field": field_key,
                        "label": label,
                        "old_value": old_val,
                        "new_value": new_val,
                        "diff_lines": list(
                            difflib.unified_diff(
                                old_val.splitlines(),
                                new_val.splitlines(),
                                fromfile=f"v{query.from_version}",
                                tofile=f"v{query.to_version}",
                                lineterm="",
                            )
                        ),
                    }
                )
        return {
            "article_id": art["id"],
            "code": art["code"],
            "from_version": query.from_version,
            "to_version": query.to_version,
            "differences": differences,
        }
