"""Helpers compartidos de autorización RBAC, enmascaramiento invitado y OTP."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.exceptions import ForbiddenError
from src.domain.rules import mask_email

PRIVATE_ATTACHMENTS_ROOT = Path("data/private_attachments")
MESSAGE_EDIT_WINDOW_SECONDS = 300
LOOKUP_MAX_ATTEMPTS = 5
LOOKUP_LOCKOUT_SECONDS = 900  # 15 minutos
_EMAIL_IN_TEXT_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Buffer en memoria para verificación de outbox OTP en modo demostración/pruebas
GUEST_OTP_OUTBOX: Dict[tuple[str, str], str] = {}


def is_guest_otp_enabled() -> bool:
    return os.environ.get("GUEST_OTP_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


_is_guest_otp_enabled = is_guest_otp_enabled


def mask_emails_in_text(value: Optional[str]) -> str:
    return _EMAIL_IN_TEXT_RE.sub(lambda m: mask_email(m.group(0)), value or "")


def sanitize_for_guest(
    ticket: Dict[str, Any],
    events: List[Dict[str, Any]],
    messages: List[Dict[str, Any]],
) -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    clean_ticket = dict(ticket)
    clean_ticket["requester_email"] = mask_email(clean_ticket.get("requester_email", ""))
    if clean_ticket.get("assigned_tech_email"):
        clean_ticket["assigned_tech_email"] = mask_email(clean_ticket["assigned_tech_email"])
    clean_events = [
        {
            "id": e["id"],
            "action": e["action"],
            "old_status": e.get("old_status"),
            "new_status": e.get("new_status"),
            "actor_email": mask_email(e.get("actor_email", "")),
            "comment": mask_emails_in_text(e.get("comment")),
            "created_at": e["created_at"],
        }
        for e in events
    ]
    clean_messages = []
    for m in messages:
        cm = dict(m)
        cm["sender_email"] = mask_email(cm.get("sender_email", ""))
        clean_messages.append(cm)
    return clean_ticket, clean_events, clean_messages


def authorize_ticket_access(actor: Dict[str, Any], ticket: Dict[str, Any]) -> None:
    role = actor.get("role")
    if role == "invitado":
        if (
            int(actor.get("ticket_id", -1)) == int(ticket["id"])
            and int(actor.get("id", -1)) == int(ticket["requester_id"])
        ):
            return
        raise ForbiddenError(
            "El acceso de invitado externo está restringido únicamente a su propio ticket."
        )
    if role in ("admin", "coordinador", "director"):
        return
    if role == "tecnico":
        if (
            ticket.get("assigned_tech_id") == actor.get("id")
            or ticket.get("requester_id") == actor.get("id")
            or ticket.get("area") == actor.get("area")
        ):
            return
        raise ForbiddenError("No tiene permisos para acceder a tickets fuera de su área o bandeja.")
    if int(ticket["requester_id"]) != int(actor["id"]):
        raise ForbiddenError(
            "Por control RBAC solo puede consultar o interactuar con sus propios tickets."
        )


_authorize_ticket_access = authorize_ticket_access
