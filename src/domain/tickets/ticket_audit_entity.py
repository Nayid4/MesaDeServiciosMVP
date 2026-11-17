"""Entidades inmutables de trazabilidad de tickets, auditoría global y notificaciones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TicketAuditEvent:
    """Evento cronológico inmutable de trazabilidad y ciclo de vida del ticket."""

    id: Optional[int]
    ticket_id: int
    actor_email: str
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    comment: Optional[str] = None
    created_at: Optional[str] = None


TicketHistory = TicketAuditEvent


@dataclass
class AuditLog:
    """Registro inmutable (append-only) de auditoría para control interno."""

    id: Optional[int]
    timestamp: str
    user_email: str
    ip_address: str
    action: str
    entity: str
    entity_id: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class Notification:
    """Notificación en plataforma para usuarios y equipo técnico."""

    id: Optional[int]
    user_email: str
    ticket_number: Optional[str]
    title: str
    message: str
    is_read: bool = False
    created_at: Optional[str] = None
