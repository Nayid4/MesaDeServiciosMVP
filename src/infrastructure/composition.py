"""Composición de dependencias de infraestructura y proveedores para FastAPI."""

from __future__ import annotations

from functools import partial
from typing import Callable, Optional

from src.application.common.cqrs_bus import CQRSBus
from src.domain.ports import IUnitOfWork
from src.infrastructure.bus_registry import build_cqrs_bus
from src.infrastructure.ml.ai_engine import LocalNLPEngine
from src.infrastructure.ml.model_trainer import DEFAULT_REGISTRY_PATH
from src.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

_AI_ENGINE: Optional[LocalNLPEngine] = None
_CQRS_BUS: Optional[CQRSBus] = None


def uow_factory(db_path: Optional[str] = None) -> Callable[[], IUnitOfWork]:
    """Retorna una fábrica transaccional Unit of Work resuelta dinámicamente."""
    return partial(SqlAlchemyUnitOfWork, db_path=db_path)


def create_uow(db_path: Optional[str] = None) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db_path=db_path)


def get_ai_engine() -> LocalNLPEngine:
    global _AI_ENGINE
    if _AI_ENGINE is None:
        _AI_ENGINE = LocalNLPEngine(registry_path=DEFAULT_REGISTRY_PATH)
    return _AI_ENGINE


def get_cqrs_bus() -> CQRSBus:
    """Obtiene el bus CQRS singleton compartido por la capa de presentación."""
    global _CQRS_BUS
    if _CQRS_BUS is None:
        _CQRS_BUS = build_cqrs_bus(uow_factory(), get_ai_engine())
    return _CQRS_BUS


def reset_runtime_dependencies() -> None:
    """Reinicia singletons en memoria (útil tras reentrenamiento o pruebas aisladas)."""
    global _AI_ENGINE, _CQRS_BUS
    _AI_ENGINE = None
    _CQRS_BUS = None
