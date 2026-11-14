"""Contratos abstractos (Interfaces ABC segregadas - ISP/LSP) para la capa de dominio."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def update(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_users(
        self,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def list_active_technicians_with_load(self, area: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def count_active_admins(self) -> int: ...


class IRefreshTokenRepository(ABC):
    @abstractmethod
    def create(self, user_id: int, token_hash: str, expires_at: str) -> None: ...

    @abstractmethod
    def get_valid(self, token_hash: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def revoke(self, token_hash: str) -> None: ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int) -> None: ...


class ITicketRepository(ABC):
    @abstractmethod
    def next_ticket_number(self, year: int = 2026) -> str: ...

    @abstractmethod
    def create(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def update(self, ticket_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_tickets(
        self,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_history(self, entry: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_history(self, ticket_id: int) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_messages(self, ticket_id: int) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def mark_messages_read(self, ticket_id: int, reader_email: str) -> None: ...


class IKnowledgeRepository(ABC):
    @abstractmethod
    def list_articles(
        self,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_id(self, article_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def upsert(self, article_data: Dict[str, Any]) -> Dict[str, Any]: ...


class IAuditRepository(ABC):
    @abstractmethod
    def append(self, log_data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def list_logs(
        self,
        user_email: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]: ...


class INotificationRepository(ABC):
    @abstractmethod
    def create(self, notification_data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def list_for_user(self, user_email: str, unread_only: bool = False) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def mark_all_read(self, user_email: str) -> None: ...


class ICatalogRepository(ABC):
    @abstractmethod
    def list_services(self, active_only: bool = False) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def upsert_service(self, data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_sla_table(self) -> Dict[str, Dict[str, float]]: ...

    @abstractmethod
    def update_sla(self, priority: str, response_hours: float, resolution_hours: float) -> None: ...


# Alias retrocompatibles para consumidores existentes
UserRepository = IUserRepository
RefreshTokenRepository = IRefreshTokenRepository
TicketRepository = ITicketRepository
KnowledgeBaseRepository = IKnowledgeRepository
AuditLogRepository = IAuditRepository
NotificationRepository = INotificationRepository
CatalogRepository = ICatalogRepository
