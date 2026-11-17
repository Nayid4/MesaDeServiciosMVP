"""Entidades RefreshToken y PasswordResetToken para gestión segura de sesiones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RefreshToken:
    """Token opaco de refresco persistido para rotación segura de sesiones."""

    id: Optional[int]
    user_id: int
    token_hash: str
    expires_at: str
    revoked: bool = False
    created_at: Optional[str] = None


@dataclass
class PasswordResetToken:
    """Token efímero (15 min) de un solo uso para recuperación de contraseña institucional."""

    id: Optional[int]
    user_id: int
    token_hash: str
    expires_at: str
    used_at: Optional[str] = None
    created_at: Optional[str] = None
