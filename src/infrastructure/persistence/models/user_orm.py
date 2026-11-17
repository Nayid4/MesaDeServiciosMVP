"""Modelos ORM de usuarios, tokens de refresco, restablecimiento y preferencias."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.models.base import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    area: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    sede: Mapped[str] = mapped_column(
        String(120), nullable=False, default="Sede Sabanas (Valledupar)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    privacy_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_assigned_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    refresh_tokens: Mapped[list["RefreshTokenORM"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshTokenORM(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["UserORM"] = relationship(back_populates="refresh_tokens")


class PasswordResetTokenORM(Base):
    """Tokens efímeros (15 min) y de un solo uso para restablecer contraseña."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("idx_pwd_reset_user", "user_id", "consumed"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[str] = mapped_column(String(64), nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)


class UserNotificationPreferenceORM(Base):
    """Preferencias individuales de notificaciones en plataforma para usuarios UPC."""

    __tablename__ = "user_notification_preferences"

    user_email: Mapped[str] = mapped_column(String(255), primary_key=True)
    notify_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_email_sim: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_ticket_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_chat_messages: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_sla_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
