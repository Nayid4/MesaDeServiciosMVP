"""Puertos de repositorio para tickets, chat, auditoría, notificaciones y catálogo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.common.pagination import PageRequest, PagedResult


class ITicketRepo(ABC):
    @abstractmethod
    def next_ticket_number(self, year: int = 2026) -> str: ...

    @abstractmethod
    def allocate_next_ticket_code(self, prefix: str, year: int = 2026) -> tuple[str, int]: ...

    @abstractmethod
    def get_by_idempotency_key(self, user_id: int, key: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def save_idempotency_key(self, user_id: int, key: str, ticket_id: int) -> None: ...

    @abstractmethod
    def find_recent_duplicate(
        self, requester_id: int, content_dedup_hash: str, since_iso: str
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def create(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def update(
        self, ticket_id: int, updates: Dict[str, Any], *, expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_tickets(
        self,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def list_tickets_paginated(
        self,
        page_request: PageRequest,
        *,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        unassigned_only: bool = False,
    ) -> PagedResult[Dict[str, Any]]: ...

    @abstractmethod
    def add_audit_event(self, entry: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_audit_events(self, ticket_id: int) -> List[Dict[str, Any]]: ...

    def add_history(self, entry: Dict[str, Any]) -> None:
        self.add_audit_event(entry)

    def get_history(self, ticket_id: int) -> List[Dict[str, Any]]:
        return self.get_audit_events(ticket_id)

    @abstractmethod
    def add_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_messages(self, ticket_id: int, *, after_id: int = 0) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_message_by_id(self, ticket_id: int, message_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_message_by_client_id(
        self, ticket_id: int, sender_id: int, client_message_id: str
    ) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def update_message(self, message_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def add_message_version(self, version_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_message_versions(self, message_id: int) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def add_attachment(self, attachment_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_attachment_by_id(self, ticket_id: int, attachment_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_attachments_for_ticket(self, ticket_id: int) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def mark_messages_read(self, ticket_id: int, reader_email: str) -> List[int]: ...

    @abstractmethod
    def get_lookup_attempt(self, ip_address: str, ticket_code: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def record_lookup_failure(
        self, ip_address: str, ticket_code: str, *, max_attempts: int = 5, lockout_seconds: int = 900
    ) -> Dict[str, Any]: ...

    @abstractmethod
    def reset_lookup_attempts(self, ip_address: str, ticket_code: str) -> None: ...

    @abstractmethod
    def create_guest_otp(self, ticket_id: int, email: str, otp_hash: str, expires_at: str) -> None: ...

    @abstractmethod
    def consume_guest_otp(self, ticket_id: int, email: str, otp_hash: str, now_iso: str) -> bool: ...

    @abstractmethod
    def create_ws_ticket(self, token_hash: str, ticket_id: int, user_json: str, expires_at: str) -> None: ...

    @abstractmethod
    def consume_ws_ticket(self, token_hash: str, ticket_id: int, now_iso: str) -> Optional[Dict[str, Any]]: ...


class IAuditRepo(ABC):
    @abstractmethod
    def append(self, log_data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def list_logs(
        self, user_email: Optional[str] = None, action: Optional[str] = None, limit: int = 500
    ) -> List[Dict[str, Any]]: ...


class INotificationRepo(ABC):
    @abstractmethod
    def create(self, notification_data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def list_for_user(self, user_email: str, unread_only: bool = False) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def mark_all_read(self, user_email: str) -> None: ...

    @abstractmethod
    def mark_read(self, user_email: str, notification_id: int) -> bool: ...

    @abstractmethod
    def get_preferences(self, user_email: str) -> Dict[str, Any]: ...

    @abstractmethod
    def update_preferences(self, user_email: str, prefs: Dict[str, Any]) -> Dict[str, Any]: ...


class ICatalogRepo(ABC):
    @abstractmethod
    def list_services(self, active_only: bool = False) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def upsert_service(self, data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_sla_table(self) -> Dict[str, Dict[str, float]]: ...

    @abstractmethod
    def update_sla(self, priority: str, response_hours: float, resolution_hours: float) -> None: ...


ITicketRepository = ITicketRepo
IAuditRepository = IAuditRepo
INotificationRepository = INotificationRepo
ICatalogRepository = ICatalogRepo
