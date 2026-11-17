"""Fachada retrocompatible de excepciones de dominio."""

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
    ValidationError,
)

__all__ = [
    "AIServiceUnavailableError",
    "ConflictError",
    "DomainError",
    "EditWindowExpiredError",
    "ForbiddenError",
    "InvalidAttachmentSignatureError",
    "InvalidTransitionError",
    "NotFoundError",
    "TooManyRequestsError",
    "UnauthorizedError",
    "ValidationDomainError",
    "ValidationError",
]
