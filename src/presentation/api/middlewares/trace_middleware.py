"""Middleware de trazabilidad HTTP X-Trace-Id."""

from __future__ import annotations

from src.presentation.api.middlewares.request_audit_middleware import (
    RequestAuditMiddleware,
)

TraceMiddleware = RequestAuditMiddleware

__all__ = ["RequestAuditMiddleware", "TraceMiddleware"]
