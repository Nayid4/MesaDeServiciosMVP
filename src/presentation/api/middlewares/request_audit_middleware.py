"""Middleware de auditoría HTTP con propagación de X-Trace-Id y medición de latencia."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("casagbi.access")


class RequestAuditMiddleware(BaseHTTPMiddleware):
    """Asigna x-trace-id único a cada solicitud y adjunta tiempos de respuesta."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        logger.info(
            "trace_id=%s method=%s path=%s status=%s latency_ms=%s",
            trace_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
