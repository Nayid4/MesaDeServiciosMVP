"""Modelos ORM principales del ciclo de tickets, catálogo SLA y contadores."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.persistence.models.ticket_comms_orm import TicketMessageORM


class ServiceCatalogORM(Base):
    __tablename__ = "service_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    category_prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="GEN")
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    base_impact: Mapped[str] = mapped_column(String(32), nullable=False)
    default_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SLAConfigORM(Base):
    __tablename__ = "sla_config"

    priority: Mapped[str] = mapped_column(String(50), primary_key=True)
    sla_response_hours: Mapped[float] = mapped_column(Float, nullable=False)
    sla_resolution_hours: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketCounterORM(Base):
    """Tabla de contadores atómicos por (prefijo de categoría, año)."""

    __tablename__ = "ticket_counters"

    prefix: Mapped[str] = mapped_column(String(16), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class IdempotencyKeyORM(Base):
    """Registro de claves Idempotency-Key por usuario para evitar dobles envíos."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_idempotency_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketORM(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_requester", "requester_id"),
        Index("idx_tickets_tech", "assigned_tech_id"),
        Index("idx_tickets_number", "ticket_number"),
        Index("idx_tickets_dedup", "requester_id", "content_dedup_hash", "created_at"),
        UniqueConstraint(
            "category_prefix",
            "ticket_year",
            "sequence_number",
            name="uq_tickets_prefix_year_seq",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    category_prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="GEN")
    ticket_year: Mapped[int] = mapped_column(Integer, nullable=False, default=2026)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    legacy_ticket_number: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, unique=True
    )
    content_dedup_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    sede: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    impact: Mapped[str] = mapped_column(String(32), nullable=False)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_role: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_tech_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    assigned_tech_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sla_response_hours: Mapped[float] = mapped_column(Float, nullable=False)
    sla_resolution_hours: Mapped[float] = mapped_column(Float, nullable=False)
    response_deadline: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolution_deadline: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_response_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paused_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paused_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    closed_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closing_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    csat_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    csat_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_suggested_service: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_human_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sla_alert_75_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    audit_events: Mapped[list["TicketAuditEventORM"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    messages: Mapped[list["TicketMessageORM"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketAuditEventORM(Base):
    __tablename__ = "ticket_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    ticket: Mapped["TicketORM"] = relationship(back_populates="audit_events")
