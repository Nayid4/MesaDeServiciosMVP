"""Emisión y verificación de JWT Access Tokens (15m) y Refresh Tokens opacos (7d)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import jwt

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
GUEST_TOKEN_EXPIRE_MINUTES = 120  # 2 horas para invitado externo
SIGNED_URL_EXPIRE_SECONDS = 600  # 10 minutos (RNF-08)


def _get_jwt_secret() -> str:
    """Obtiene la clave secreta JWT desde variable de entorno con respaldo local seguro."""
    return os.environ.get(
        "CASAGBI_JWT_SECRET",
        "casagbi-upc-itil4-mvp-secret-key-2026-valledupar-seguridad",
    )


def create_access_token(
    user: Dict[str, Any],
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Emite un JWT Access Token firmado (15 minutos por defecto)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "area": user.get("area"),
        "name": user.get("full_name", user["email"]),
        "sede": user.get("sede", "Sede Sabanas (Valledupar)"),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida firma y expiración de un JWT Access Token."""
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])


def hash_refresh_token(raw_token: str) -> str:
    """Calcula el digest SHA-256 del refresh token opaco para persistencia segura."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token(days_valid: int = REFRESH_TOKEN_EXPIRE_DAYS) -> Tuple[str, str, str]:
    """Retorna (token_plano, token_hash, expires_at_iso)."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_token)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days_valid)).isoformat()
    return raw_token, token_hash, expires_at


def create_ticket_guest_token(
    *,
    ticket_id: int,
    ticket_number: str,
    requester_id: int,
    requester_email: str,
    masked_email: str,
    expires_minutes: int = GUEST_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Emite un JWT de alcance estricto a un solo ticket para invitado externo."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": f"guest:{int(requester_id)}:{int(ticket_id)}",
        "token_type": "ticket_guest",
        "role": "invitado",
        "ticket_id": int(ticket_id),
        "ticket_number": ticket_number,
        "requester_id": int(requester_id),
        "email": requester_email.strip().lower(),
        "masked_email": masked_email,
        "name": f"Invitado ({masked_email})",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_attachment_signature(
    ticket_id: int,
    attachment_id: int,
    expires_at_unix: int,
) -> str:
    """Firma HMAC-SHA256 de enlace temporal de descarga de adjunto."""
    msg = f"{int(ticket_id)}:{int(attachment_id)}:{int(expires_at_unix)}".encode("utf-8")
    return hmac.new(_get_jwt_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def build_signed_attachment_url(
    ticket_id: int,
    attachment_id: int,
    *,
    valid_seconds: int = SIGNED_URL_EXPIRE_SECONDS,
) -> str:
    """Construye ruta relativa firmada de descarga con vigencia de 10 minutos (RNF-08)."""
    expires_at = int(datetime.now(timezone.utc).timestamp()) + int(valid_seconds)
    sig = create_attachment_signature(ticket_id, attachment_id, expires_at)
    return (
        f"/api/v1/tickets/{int(ticket_id)}/attachments/{int(attachment_id)}/download"
        f"?expires={expires_at}&sig={sig}"
    )


def verify_attachment_signature(
    ticket_id: int,
    attachment_id: int,
    expires_at_unix: int,
    signature: str,
) -> bool:
    """Verifica firma HMAC y expiración temporal del enlace firmado."""
    if not signature:
        return False
    now_unix = int(datetime.now(timezone.utc).timestamp())
    if now_unix > int(expires_at_unix):
        return False
    expected = create_attachment_signature(ticket_id, attachment_id, expires_at_unix)
    return hmac.compare_digest(expected, str(signature).strip())
