"""Paquete común de dominio: paginación y excepciones."""

from src.domain.common.exceptions import (
    AIServiceUnavailableError,
    ConflictError,
    DomainError,
    EditWindowExpiredError,
    ForbiddenError,
    InvalidAttachmentSignatureError,
    InvalidTransitionError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationDomainError,
)
from src.domain.common.pagination import PagedResult, PageRequest

__all__ = [
    "AIServiceUnavailableError",
    "ConflictError",
    "DomainError",
    "EditWindowExpiredError",
    "ForbiddenError",
    "InvalidAttachmentSignatureError",
    "InvalidTransitionError",
    "NotFoundError",
    "PageRequest",
    "PagedResult",
    "TooManyRequestsError",
    "UnauthorizedError",
    "ValidationDomainError",
]
