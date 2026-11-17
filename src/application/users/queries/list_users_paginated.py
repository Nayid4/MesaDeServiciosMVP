"""Consulta CQRS de listado de usuarios con paginación SQL real."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Query, sanitize_user_dict
from src.application.common.cqrs_bus import serialize_paged_result
from src.domain.common.pagination import PageRequest, PagedResult
from src.domain.exceptions import ForbiddenError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS


@dataclass(frozen=True)
class ListUsersPaginatedQuery(Query):
    actor_role: str
    page: int = 1
    page_size: int = 10
    role: Optional[str] = None
    area: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None


class ListUsersPaginatedQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListUsersPaginatedQuery) -> Dict[str, Any]:
        if query.actor_role not in ("admin", "coordinador", "director"):
            raise ForbiddenError("No tiene permisos para consultar el directorio completo de usuarios.")

        page_req = PageRequest(page=query.page, page_size=query.page_size)
        with self._uow_factory() as uow:
            paged = uow.users.list_users_paginated(
                page_req,
                role=query.role,
                area=query.area,
                is_active=query.is_active,
                search=query.search,
            )

        sanitized_items = []
        for u in paged.items:
            clean = sanitize_user_dict(u)
            clean["role_label"] = ROLE_LABELS.get(clean["role"], clean["role"])
            sanitized_items.append(clean)

        return serialize_paged_result(
            PagedResult(
                items=sanitized_items,
                total=paged.total,
                page=paged.page,
                page_size=paged.page_size,
                pages=paged.pages,
            )
        )
