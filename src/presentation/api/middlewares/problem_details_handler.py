"""Manejador global de errores estándar RFC 7807 (application/problem+json)."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.exceptions import DomainError


def _resolve_trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None) or request.headers.get("x-trace-id") or str(uuid.uuid4())


def _problem_response(
    *,
    request: Request,
    type_uri: str,
    title: str,
    status: int,
    detail: str,
    extra: Dict[str, Any] | None = None,
) -> JSONResponse:
    trace_id = _resolve_trace_id(request)
    body: Dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "trace_id": trace_id,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers={"X-Trace-Id": trace_id},
    )


def register_problem_details_handlers(app: FastAPI) -> None:
    """Registra capturadores globales RFC 7807 sobre la instancia FastAPI."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return _problem_response(
            request=request,
            type_uri=exc.type_uri,
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            extra={"code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": ".".join(str(x) for x in err.get("loc", [])),
                "msg": err.get("msg", "Valor inválido"),
            }
            for err in exc.errors()
        ]
        summary = "; ".join(f"{e['loc']}: {e['msg']}" for e in errors) or "Error de validación en solicitud."
        return _problem_response(
            request=request,
            type_uri="https://casagbi.unicesar.edu.co/problems/request-validation-error",
            title="Error de validación en parámetros de entrada",
            status=422,
            detail=summary,
            extra={"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem_response(
            request=request,
            type_uri=f"https://casagbi.unicesar.edu.co/problems/http-{exc.status_code}",
            title=f"Error HTTP {exc.status_code}",
            status=exc.status_code,
            detail=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return _problem_response(
            request=request,
            type_uri="https://casagbi.unicesar.edu.co/problems/internal-server-error",
            title="Error interno no controlado",
            status=500,
            detail=f"Ocurrió un error inesperado procesando la solicitud ({type(exc).__name__}).",
        )
