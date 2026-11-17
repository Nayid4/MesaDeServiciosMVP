"""Primitivas base CQRS (Commands, Queries, DTOs y sanitización)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, TypeVar

TResult = TypeVar("TResult")


@dataclass(frozen=True)
class Command:
    """Marcador base para comandos CQRS que mutan estado dentro de un Unit of Work."""


@dataclass(frozen=True)
class Query:
    """Marcador base para consultas CQRS de lectura."""


@dataclass
class Result(Generic[TResult]):
    """Contenedor uniforme de resultado de ejecución en capa de aplicación."""

    ok: bool
    data: Optional[TResult] = None
    error: Optional[str] = None


def sanitize_user_dict(user: Dict[str, Any]) -> Dict[str, Any]:
    """Elimina password_hash antes de exponer cualquier perfil fuera de infraestructura."""
    clean = dict(user)
    clean.pop("password_hash", None)
    return clean
