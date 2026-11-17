"""Modelos ORM de chat multimedia, adjuntos, acceso invitado y tickets WebSocket."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.persistence.models.ticket_orm import TicketORM


class TicketMessageORM(Base):
    __tablename__ = "ticket_messages"
    __table_args__ = (Index("idx_msg_ticket_id", "ticket_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(50), nullable=False)
    client_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reply_to_message_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ticket_messages.id"), nullable=True
    )
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivered_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    read_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    edited_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    ticket: Mapped["TicketORM"] = relationship(back_populates="messages")


class MessageVersionORM(Base):
    """Historial inmutable de versiones anteriores por edición o borrado lógico."""

    __tablename__ = "message_versions"
    __table_args__ = (Index("idx_msg_versions_msg_id", "message_id", "version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ticket_messages.id", ondelete="CASCADE"), nullable=False
    )
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="edit")
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketAttachmentORM(Base):
    """Metadatos de adjuntos y notas de voz almacenados fuera del árbol estático."""

    __tablename__ = "ticket_attachments"
    __table_args__ = (Index("idx_att_ticket_msg", "ticket_id", "message_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ticket_messages.id", ondelete="CASCADE"), nullable=False
    )
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploader_email: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_rel_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class PublicLookupAttemptORM(Base):
    """Control de intentos fallidos de consulta pública por IP y radicado."""

    __tablename__ = "public_lookup_attempts"
    __table_args__ = (
        UniqueConstraint("ip_address", "ticket_code", name="uq_lookup_ip_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    ticket_code: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class GuestOtpChallengeORM(Base):
    """Retos OTP efímeros cuando GUEST_OTP_ENABLED está activo."""

    __tablename__ = "guest_otp_challenges"
    __table_args__ = (Index("idx_guest_otp_ticket_email", "ticket_id", "email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(64), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class WsConnectionTicketORM(Base):
    """Tickets de un solo uso y vida corta para autenticar handshakes WebSocket."""

    __tablename__ = "ws_connection_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    user_json: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(String(64), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
