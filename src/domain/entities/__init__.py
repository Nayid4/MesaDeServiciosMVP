"""Fachada retrocompatible de entidades del dominio CASAGBI."""

from src.domain.knowledge_base.article_entity import KnowledgeArticle
from src.domain.tickets.ticket_audit_entity import (
    AuditLog,
    Notification,
    TicketAuditEvent,
    TicketHistory,
)
from src.domain.tickets.ticket_entity import Ticket
from src.domain.tickets.ticket_message_entity import TicketMessage
from src.domain.users.refresh_token_entity import PasswordResetToken, RefreshToken
from src.domain.users.user_entity import User

__all__ = [
    "AuditLog",
    "KnowledgeArticle",
    "Notification",
    "PasswordResetToken",
    "RefreshToken",
    "Ticket",
    "TicketAuditEvent",
    "TicketHistory",
    "TicketMessage",
    "User",
]
