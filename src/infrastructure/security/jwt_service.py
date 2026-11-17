"""Servicio JWT, firmas de descarga y tokens temporales de restablecimiento (15 min)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from src.infrastructure.security.jwt_provider import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GUEST_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SIGNED_URL_EXPIRE_SECONDS,
    build_signed_attachment_url,
    create_access_token,
    create_attachment_signature,
    create_ticket_guest_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_attachment_signature,
)

PASSWORD_RESET_EXPIRE_MINUTES = 15


def hash_password_reset_token(raw_token: str) -> str:
    """Calcula SHA-256 para almacenamiento seguro de token de restablecimiento."""
    return hash_refresh_token(raw_token)


def generate_password_reset_token(
    minutes_valid: int = PASSWORD_RESET_EXPIRE_MINUTES,
) -> Tuple[str, str, str]:
    """Genera (token_plano, token_hash, expires_at_iso) válido por 15 minutos."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password_reset_token(raw_token)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=int(minutes_valid))).isoformat()
    return raw_token, token_hash, expires_at


__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "GUEST_TOKEN_EXPIRE_MINUTES",
    "JWT_ALGORITHM",
    "PASSWORD_RESET_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "SIGNED_URL_EXPIRE_SECONDS",
    "build_signed_attachment_url",
    "create_access_token",
    "create_attachment_signature",
    "create_ticket_guest_token",
    "decode_access_token",
    "generate_password_reset_token",
    "generate_refresh_token",
    "hash_password_reset_token",
    "hash_refresh_token",
    "verify_attachment_signature",
]
