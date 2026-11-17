"""Consultas CQRS de laboratorio ML (comparación) y bitácora de auditoría."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.application.common import Query
from src.domain.exceptions import ForbiddenError, NotFoundError
from src.domain.ports import IUnitOfWork
from src.infrastructure.ml.ai_engine import LocalNLPEngine
from src.infrastructure.ml.model_trainer import load_model_registry


@dataclass(frozen=True)
class GetModelComparisonQuery(Query):
    simulate_text: Optional[str] = None


@dataclass(frozen=True)
class ListAuditLogsQuery(Query):
    actor: Dict[str, Any]
    user_email: Optional[str] = None
    action: Optional[str] = None
    limit: int = 200


class GetModelComparisonQueryHandler:
    def __init__(self, ai_engine: LocalNLPEngine) -> None:
        self._ai_engine = ai_engine

    def handle(self, query: GetModelComparisonQuery) -> Dict[str, Any]:
        registry = load_model_registry(self._ai_engine.registry_path)
        if not registry:
            raise NotFoundError("No existe el registro de modelos ML entrenados.")
        side_by_side: List[Dict[str, Any]] = []
        if query.simulate_text and len(query.simulate_text.strip()) >= 3:
            side_by_side = self._ai_engine.predict_side_by_side(query.simulate_text.strip())
        return {"registry": registry, "side_by_side": side_by_side}


class ListAuditLogsQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ListAuditLogsQuery) -> List[Dict[str, Any]]:
        if query.actor.get("role") not in ("coordinador", "admin"):
            raise ForbiddenError("Acceso restringido a bitácora inmutable de auditoría.")
        with self._uow_factory() as uow:
            return uow.audit_logs.list_logs(
                user_email=query.user_email, action=query.action, limit=query.limit
            )
