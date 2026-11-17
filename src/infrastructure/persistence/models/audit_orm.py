"""Modelos ORM de auditoría inmutable y notificaciones en plataforma."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import Base


class AuditLogORM(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("idx_audit_timestamp", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, default="127.0.0.1")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class NotificationORM(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("idx_notif_user", "user_email", "is_read"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    ticket_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
