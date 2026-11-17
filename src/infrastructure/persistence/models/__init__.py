"""Reexportaciones del paquete modular de modelos ORM CASAGBI."""

from __future__ import annotations

from src.infrastructure.persistence.models.audit_orm import AuditLogORM, NotificationORM
from src.infrastructure.persistence.models.base import Base
from src.infrastructure.persistence.models.kb_orm import (
    KnowledgeArticleORM,
    KnowledgeArticleVersionORM,
)
from src.infrastructure.persistence.models.ticket_comms_orm import (
    GuestOtpChallengeORM,
    MessageVersionORM,
    PublicLookupAttemptORM,
    TicketAttachmentORM,
    TicketMessageORM,
    WsConnectionTicketORM,
)
from src.infrastructure.persistence.models.ticket_orm import (
    IdempotencyKeyORM,
    SLAConfigORM,
    ServiceCatalogORM,
    TicketAuditEventORM,
    TicketCounterORM,
    TicketORM,
)
from src.infrastructure.persistence.models.user_orm import (
    PasswordResetTokenORM,
    RefreshTokenORM,
    UserNotificationPreferenceORM,
    UserORM,
)

__all__ = [
    "AuditLogORM",
    "Base",
    "GuestOtpChallengeORM",
    "IdempotencyKeyORM",
    "KnowledgeArticleORM",
    "KnowledgeArticleVersionORM",
    "MessageVersionORM",
    "NotificationORM",
    "PasswordResetTokenORM",
    "PublicLookupAttemptORM",
    "RefreshTokenORM",
    "SLAConfigORM",
    "ServiceCatalogORM",
    "TicketAttachmentORM",
    "TicketAuditEventORM",
    "TicketCounterORM",
    "TicketMessageORM",
    "TicketORM",
    "UserNotificationPreferenceORM",
    "UserORM",
    "WsConnectionTicketORM",
]
