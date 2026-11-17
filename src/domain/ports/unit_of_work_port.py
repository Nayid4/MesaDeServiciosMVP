"""Contrato Unit of Work para atomicidad transaccional sobre repositorios."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.knowledge_base.kb_repository_port import IKnowledgeRepo
from src.domain.tickets.ticket_repository_port import (
    IAuditRepo,
    ICatalogRepo,
    INotificationRepo,
    ITicketRepo,
)
from src.domain.users.user_repository_port import (
    IPasswordResetTokenRepo,
    IRefreshTokenRepo,
    IUserRepo,
)


class IUnitOfWork(ABC):
    """Contrato Unit of Work para atomicidad transaccional sobre repositorios."""

    users: IUserRepo
    refresh_tokens: IRefreshTokenRepo
    password_reset_tokens: IPasswordResetTokenRepo
    tickets: ITicketRepo
    kb_articles: IKnowledgeRepo
    audit_logs: IAuditRepo
    notifications: INotificationRepo
    catalog: ICatalogRepo

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

    @abstractmethod
    def begin_immediate(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
