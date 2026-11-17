"""Entidad User, roles RBAC y validaciones institucionales de usuario."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Optional

INSTITUTIONAL_DOMAIN = "@unicesar.edu.co"
VALID_ROLES = ("usuario", "tecnico", "coordinador", "director", "admin")

ROLE_LABELS = {
    "usuario": "Usuario institucional",
    "tecnico": "Técnico de soporte",
    "coordinador": "Coordinador de mesa",
    "director": "Director de TIC",
    "admin": "Administrador del sistema",
}

ROLE_PERMISSIONS = {
    "usuario": {
        "create_ticket",
        "track_own_tickets",
        "chat_own_ticket",
        "confirm_or_reopen_own_ticket",
        "rate_service",
        "use_ai_assistant",
    },
    "tecnico": {
        "create_ticket",
        "track_assigned_tickets",
        "manage_assigned_tickets",
        "chat_assigned_ticket",
        "propose_kb_article",
        "view_own_kpis",
        "use_ai_assistant",
    },
    "coordinador": {
        "create_ticket",
        "track_all_area_tickets",
        "manage_tickets",
        "reassign_ticket",
        "adjust_priority",
        "manage_kb",
        "view_area_kpis",
        "export_reports",
        "view_ml_lab",
        "use_ai_assistant",
    },
    "director": {
        "track_all_tickets",
        "view_global_kpis",
        "export_reports",
        "view_ml_lab",
        "use_ai_assistant",
    },
    "admin": {
        "create_ticket",
        "track_all_tickets",
        "manage_tickets",
        "reassign_ticket",
        "adjust_priority",
        "manage_kb",
        "manage_users",
        "manage_catalog_sla",
        "view_audit_logs",
        "view_global_kpis",
        "export_reports",
        "manage_ml_lab",
        "use_ai_assistant",
    },
}


def is_valid_institutional_email(email: str) -> bool:
    """Valida que el correo pertenezca al dominio institucional @unicesar.edu.co."""
    if not email or "@" not in email:
        return False
    normalized = email.strip().lower()
    local_part, _, domain = normalized.partition("@")
    return bool(local_part) and domain == "unicesar.edu.co"


def mask_email(email: str) -> str:
    """Enmascara correo institucional (ej. ka***@unicesar.edu.co)."""
    raw = (email or "").strip().lower()
    if "@" not in raw:
        return "***"
    local, _, domain = raw.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def constant_time_email_matches(candidate_email: str, target_email: str) -> bool:
    """Compara dos correos sin distinción de mayúsculas en tiempo constante."""
    norm_a = (candidate_email or "").strip().lower().encode("utf-8")
    norm_b = (target_email or "").strip().lower().encode("utf-8")
    digest_a = hashlib.sha256(norm_a).digest()
    digest_b = hashlib.sha256(norm_b).digest()
    return hmac.compare_digest(digest_a, digest_b)


@dataclass
class User:
    """Representa un usuario institucional o miembro del equipo TIC de la UPC."""

    id: Optional[int]
    email: str
    full_name: str
    role: str
    area: Optional[str]
    sede: str
    is_active: bool = True
    privacy_accepted: bool = False
    last_assigned_at: Optional[str] = None
    created_at: Optional[str] = None
    password_hash: Optional[str] = field(default=None, repr=False)
