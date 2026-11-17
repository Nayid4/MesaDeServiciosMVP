"""Fachada de compatibilidad para repositorios SQLAlchemy 2.0."""

from __future__ import annotations

from src.infrastructure.persistence.repositories import (
    SqlAlchemyAuditRepo,
    SqlAlchemyCatalogRepo,
    SqlAlchemyKnowledgeRepo,
    SqlAlchemyNotificationRepo,
    SqlAlchemyPasswordResetTokenRepo,
    SqlAlchemyRefreshTokenRepo,
    SqlAlchemyTicketRepo,
    SqlAlchemyUserRepo,
)

__all__ = [
    "SqlAlchemyAuditRepo",
    "SqlAlchemyCatalogRepo",
    "SqlAlchemyKnowledgeRepo",
    "SqlAlchemyNotificationRepo",
    "SqlAlchemyPasswordResetTokenRepo",
    "SqlAlchemyRefreshTokenRepo",
    "SqlAlchemyTicketRepo",
    "SqlAlchemyUserRepo",
]
