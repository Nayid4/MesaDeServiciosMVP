"""Reexportaciones del paquete modular de repositorios SQLAlchemy 2.0."""

from __future__ import annotations

from src.infrastructure.persistence.repositories.audit_repository import (
    SqlAlchemyAuditRepo,
    SqlAlchemyCatalogRepo,
    SqlAlchemyNotificationRepo,
)
from src.infrastructure.persistence.repositories.kb_repository import (
    SqlAlchemyKnowledgeRepo,
)
from src.infrastructure.persistence.repositories.ticket_repository import (
    SqlAlchemyTicketRepo,
)
from src.infrastructure.persistence.repositories.user_repository import (
    SqlAlchemyPasswordResetTokenRepo,
    SqlAlchemyRefreshTokenRepo,
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
