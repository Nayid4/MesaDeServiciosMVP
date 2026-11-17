"""Implementación concreta del Unit of Work sobre SQLAlchemy Session."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from src.domain.ports import IUnitOfWork
from src.infrastructure.persistence.database import get_session_factory
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


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Coordina repositorios sobre una misma sesión SQLAlchemy con commit/rollback atómico."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ) -> None:
        self._db_path = db_path
        self._session_factory = session_factory or get_session_factory(db_path)
        self.session: Optional[Session] = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.users = SqlAlchemyUserRepo(self.session)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepo(self.session)
        self.password_reset_tokens = SqlAlchemyPasswordResetTokenRepo(self.session)
        self.tickets = SqlAlchemyTicketRepo(self.session)
        self.kb_articles = SqlAlchemyKnowledgeRepo(self.session)
        self.audit_logs = SqlAlchemyAuditRepo(self.session)
        self.notifications = SqlAlchemyNotificationRepo(self.session)
        self.catalog = SqlAlchemyCatalogRepo(self.session)
        return self

    def begin_immediate(self) -> None:
        """Fuerza la apertura inmediata de la transacción SQLite (BEGIN IMMEDIATE)."""
        if self.session is not None:
            self.session.connection()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.session is None:
            return
        try:
            if exc_type is not None:
                self.session.rollback()
        finally:
            self.session.close()
            self.session = None

    def commit(self) -> None:
        if self.session is not None:
            self.session.commit()

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()
