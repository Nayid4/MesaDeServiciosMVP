"""Utilidades compartidas de serialización y paginación SQLAlchemy 2.0."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.common.pagination import PageRequest, PagedResult


def model_to_dict(instance: Any) -> Dict[str, Any]:
    """Serializa un modelo ORM a diccionario plano de dominio."""
    return {col.name: getattr(instance, col.name) for col in instance.__table__.columns}


def execute_paginated_query(
    session: Session,
    base_stmt: Any,
    count_col: Any,
    page_request: PageRequest,
    *,
    serializer: Optional[Callable[[Any], Dict[str, Any]]] = None,
) -> PagedResult[Dict[str, Any]]:
    """Ejecuta conteo total SQL (COUNT) y consulta LIMIT/OFFSET reales en base de datos."""
    count_subq = base_stmt.order_by(None).with_only_columns(count_col).subquery()
    total = int(session.scalar(select(func.count()).select_from(count_subq)) or 0)
    paged_stmt = base_stmt.offset(page_request.offset).limit(page_request.page_size)
    rows = session.scalars(paged_stmt).all()
    serialize_fn = serializer or model_to_dict
    items = [serialize_fn(row) for row in rows]
    return PagedResult.build(items=items, total=total, page_request=page_request)
