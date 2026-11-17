"""Caso de uso CQRS de subida atómica de adjuntos y notas de voz en chat."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.common import Command
from src.application.tickets.ticket_helpers import (
    PRIVATE_ATTACHMENTS_ROOT,
    authorize_ticket_access,
)
from src.domain.exceptions import (
    InvalidTransitionError,
    NotFoundError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import MAX_ATTACHMENTS_PER_MESSAGE, validate_attachment_binary


@dataclass(frozen=True)
class UploadTicketAttachmentsCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    files: List[Dict[str, Any]]
    content: str = ""
    client_message_id: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    audio_duration_seconds: Optional[float] = None
    attachments_root: Optional[Path] = None
    ip_address: str = "127.0.0.1"


class UploadTicketAttachmentsCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: UploadTicketAttachmentsCommand) -> Dict[str, Any]:
        if not cmd.files:
            raise ValidationDomainError("Debe adjuntar al menos un archivo o nota de voz.")
        if len(cmd.files) > MAX_ATTACHMENTS_PER_MESSAGE:
            raise ValidationDomainError(
                f"Se permiten máximo {MAX_ATTACHMENTS_PER_MESSAGE} archivos por mensaje."
            )

        clean_client_id = (cmd.client_message_id or "").strip() or None
        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)

            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError(
                    f"El ticket {ticket['ticket_number']} está en estado '{ticket['status']}'. No se permiten nuevos adjuntos."
                )

            if clean_client_id:
                existing = uow.tickets.get_message_by_client_id(
                    ticket["id"], int(cmd.actor["id"]), clean_client_id
                )
                if existing is not None:
                    existing["deduplicated"] = True
                    return existing

            if cmd.reply_to_message_id is not None and (
                uow.tickets.get_message_by_id(ticket["id"], int(cmd.reply_to_message_id)) is None
            ):
                raise NotFoundError(
                    f"El mensaje citado #{cmd.reply_to_message_id} no pertenece a este ticket."
                )

            validated_items: List[tuple[Dict[str, Any], bytes]] = []
            for file_entry in cmd.files:
                raw_bytes = file_entry.get("content") or b""
                filename = str(file_entry.get("filename") or "")
                meta = validate_attachment_binary(
                    filename, raw_bytes, audio_duration_seconds=cmd.audio_duration_seconds
                )
                validated_items.append((meta, raw_bytes))

            root_dir = (cmd.attachments_root or PRIVATE_ATTACHMENTS_ROOT).resolve()
            ticket_dir = root_dir / f"ticket_{int(ticket['id'])}"
            ticket_dir.mkdir(parents=True, exist_ok=True)

            has_audio = any(m["is_audio"] for m, _ in validated_items)
            msg_type = "audio" if has_audio and len(validated_items) == 1 else "attachment"
            summary_names = ", ".join(m["sanitized_name"] for m, _ in validated_items)
            display_text = (cmd.content or "").strip() or (
                f"Nota de voz ({summary_names})"
                if msg_type == "audio"
                else f"Archivos adjuntos: {summary_names}"
            )

            now_utc_iso = datetime.now(timezone.utc).isoformat()
            created_msg = uow.tickets.add_message(
                {
                    "ticket_id": ticket["id"],
                    "sender_id": int(cmd.actor["id"]),
                    "sender_email": cmd.actor["email"],
                    "sender_role": cmd.actor["role"],
                    "client_message_id": clean_client_id,
                    "reply_to_message_id": cmd.reply_to_message_id,
                    "message_type": msg_type,
                    "message": display_text,
                    "attachment_name": validated_items[0][0]["sanitized_name"],
                    "is_read": False,
                    "delivered_at": now_utc_iso,
                    "created_at": now_utc_iso,
                }
            )

            written_files: List[Path] = []
            saved_attachments: List[Dict[str, Any]] = []
            try:
                for meta, raw_bytes in validated_items:
                    stored_name = f"{uuid.uuid4().hex}.{meta['extension']}"
                    dest_path = ticket_dir / stored_name
                    dest_path.write_bytes(raw_bytes)
                    written_files.append(dest_path)
                    att = uow.tickets.add_attachment(
                        {
                            "ticket_id": ticket["id"],
                            "message_id": created_msg["id"],
                            "uploader_id": int(cmd.actor["id"]),
                            "uploader_email": cmd.actor["email"],
                            "original_name": meta["sanitized_name"],
                            "stored_name": stored_name,
                            "storage_rel_path": f"ticket_{int(ticket['id'])}/{stored_name}",
                            "mime_type": meta["mime_type"],
                            "size_bytes": meta["size_bytes"],
                            "sha256_hash": meta["sha256_hash"],
                            "is_audio": meta["is_audio"],
                            "duration_seconds": cmd.audio_duration_seconds if meta["is_audio"] else None,
                            "created_at": now_utc_iso,
                        }
                    )
                    saved_attachments.append(att)

                uow.audit_logs.append(
                    {
                        "user_email": cmd.actor["email"],
                        "ip_address": cmd.ip_address,
                        "action": "ATTACHMENT_UPLOADED",
                        "entity": "ticket_messages",
                        "entity_id": str(created_msg["id"]),
                        "new_value": summary_names,
                    }
                )
                uow.commit()
            except Exception:
                for p in written_files:
                    try:
                        p.unlink(missing_ok=True)
                    except OSError:
                        pass
                raise

        created_msg["attachments"] = saved_attachments
        created_msg["deduplicated"] = False
        return created_msg
