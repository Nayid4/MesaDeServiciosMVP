"""Módulo de seguridad criptográfica: hashing bcrypt, JWT Access Token y Refresh Token."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _get_jwt_secret() -> str:
    """Obtiene la clave secreta JWT desde variable de entorno con respaldo local seguro."""
    return os.environ.get(
        "CASAGBI_JWT_SECRET",
        "casagbi-upc-itil4-mvp-secret-key-2026-valledupar-seguridad",
    )


def hash_password(plain_password: str) -> str:
    """Genera hash bcrypt seguro con salt aleatorio."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


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
