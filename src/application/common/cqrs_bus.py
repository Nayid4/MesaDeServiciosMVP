"""Bus CQRS desacoplado que enruta Commands y Queries hacia sus Handlers registrados."""

from __future__ import annotations

from typing import Any, Callable, Dict, Type

from src.application.common import Command, Query
from src.domain.common.pagination import PagedResult


def serialize_paged_result(result: PagedResult[Any]) -> Dict[str, Any]:
    """Convierte un PagedResult del dominio a diccionario uniforme de respuesta."""
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "pages": result.pages,
        "has_next": result.page < result.pages,
        "has_prev": result.page > 1,
    }


class CQRSBus:
    """Mediador central CQRS para desacoplar routers HTTP de casos de uso concretos."""

    def __init__(self) -> None:
        self._command_handlers: Dict[Type[Command], Callable[[Any], Any]] = {}
        self._query_handlers: Dict[Type[Query], Callable[[Any], Any]] = {}

    def register_command(
        self, command_type: Type[Command], handler: Callable[[Any], Any]
    ) -> None:
        self._command_handlers[command_type] = handler

    def register_query(
        self, query_type: Type[Query], handler: Callable[[Any], Any]
    ) -> None:
        self._query_handlers[query_type] = handler

    def execute(self, command: Command) -> Any:
        handler = self._command_handlers.get(type(command))
        if handler is None:
            raise LookupError(f"No hay handler registrado para comando {type(command).__name__}.")
        if hasattr(handler, "handle"):
            return handler.handle(command)
        return handler(command)

    def query(self, query_obj: Query) -> Any:
        handler = self._query_handlers.get(type(query_obj))
        if handler is None:
            raise LookupError(f"No hay handler registrado para consulta {type(query_obj).__name__}.")
        if hasattr(handler, "handle"):
            return handler.handle(query_obj)
        return handler(query_obj)
