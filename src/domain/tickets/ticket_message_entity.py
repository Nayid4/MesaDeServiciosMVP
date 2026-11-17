"""Entidad de mensaje multimedia en tiempo real, respuestas, edición (<= 5 min) y borrado lógico."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

EDIT_WINDOW_SECONDS = 300


@dataclass
class TicketMessage:
    """Mensaje del canal de comunicación en tiempo real de un ticket."""

    id: Optional[int]
    ticket_id: int
    sender_id: int
    sender_email: str
    sender_role: str
    message: str
    reply_to_message_id: Optional[int] = None
    client_message_id: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_path: Optional[str] = None
    edited_at: Optional[str] = None
    is_deleted: bool = False
    is_read: bool = False
    created_at: Optional[str] = None
