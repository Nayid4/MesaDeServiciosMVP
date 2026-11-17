"""Casos de uso CQRS de mensajería en tiempo real del chat de tickets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.application.tickets.ticket_helpers import (
    MESSAGE_EDIT_WINDOW_SECONDS,
    authorize_ticket_access,
)
from src.domain.exceptions import (
    EditWindowExpiredError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import mask_email, now_bogota, parse_iso_datetime


@dataclass(frozen=True)
class SendChatMessageCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    content: str
    client_message_id: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class EditChatMessageCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    message_id: int
    new_content: str
    now_utc_override: Optional[datetime] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class DeleteChatMessageCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int
    message_id: int
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class MarkMessagesReadCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int


class SendChatMessageCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: SendChatMessageCommand) -> Dict[str, Any]:
        if not cmd.content or not cmd.content.strip():
            raise ValidationDomainError("El mensaje de chat no puede estar vacío.")
        clean_client_id = (cmd.client_message_id or "").strip() or None

        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)

            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError(
                    f"El ticket {ticket['ticket_number']} está en estado '{ticket['status']}'. El chat está en modo solo lectura."
                )

            if clean_client_id:
                existing = uow.tickets.get_message_by_client_id(
                    ticket["id"], int(cmd.actor["id"]), clean_client_id
                )
                if existing is not None:
                    existing["deduplicated"] = True
                    return existing

            if cmd.reply_to_message_id is not None:
                if uow.tickets.get_message_by_id(ticket["id"], int(cmd.reply_to_message_id)) is None:
                    raise NotFoundError(
                        f"El mensaje citado #{cmd.reply_to_message_id} no pertenece a este ticket."
                    )

            now_utc_iso = datetime.now(timezone.utc).isoformat()
            now_bogota_iso = now_bogota().isoformat()
            msg = uow.tickets.add_message(
                {
                    "ticket_id": ticket["id"],
                    "sender_id": int(cmd.actor["id"]),
                    "sender_email": cmd.actor["email"],
                    "sender_role": cmd.actor["role"],
                    "client_message_id": clean_client_id,
                    "reply_to_message_id": cmd.reply_to_message_id,
                    "message_type": "text",
                    "message": cmd.content.strip(),
                    "is_read": False,
                    "delivered_at": now_utc_iso,
                    "created_at": now_utc_iso,
                }
            )
            msg["deduplicated"] = False

            if cmd.actor["role"] == "tecnico" and not ticket.get("first_response_at"):
                uow.tickets.update(ticket["id"], {"first_response_at": now_bogota_iso})

            target = (
                ticket["requester_email"]
                if cmd.actor["email"] != ticket["requester_email"]
                else ticket.get("assigned_tech_email")
            )
            if target:
                uow.notifications.create(
                    {
                        "user_email": target,
                        "ticket_number": ticket["ticket_number"],
                        "title": f"Nuevo mensaje en {ticket['ticket_number']}",
                        "message": cmd.content.strip()[:120],
                        "category": "chat",
                        "created_at": now_bogota_iso,
                    }
                )
            uow.commit()
        return msg


class EditChatMessageCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: EditChatMessageCommand) -> Dict[str, Any]:
        clean_text = (cmd.new_content or "").strip()
        if not clean_text:
            raise ValidationDomainError("El nuevo contenido del mensaje no puede estar vacío.")

        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)
            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError(
                    f"El ticket {ticket['ticket_number']} está en modo solo lectura; no admite ediciones."
                )

            msg = uow.tickets.get_message_by_id(ticket["id"], int(cmd.message_id))
            if not msg:
                raise NotFoundError(f"Mensaje #{cmd.message_id} no encontrado en el ticket.")
            if msg.get("is_deleted"):
                raise ForbiddenError("No se puede editar un mensaje que ya fue eliminado.")
            if int(msg["sender_id"]) != int(cmd.actor["id"]):
                raise ForbiddenError("Solo el autor original puede editar su propio mensaje.")
            if msg.get("message_type", "text") != "text":
                raise ValidationDomainError("Solo los mensajes de texto pueden editarse.")

            now_utc = cmd.now_utc_override or datetime.now(timezone.utc)
            if now_utc.tzinfo is None:
                now_utc = now_utc.replace(tzinfo=timezone.utc)
            created_dt = parse_iso_datetime(msg["created_at"])
            if created_dt is None:
                raise ValidationDomainError("No se pudo determinar la marca temporal del mensaje.")
            elapsed_seconds = (now_utc - created_dt.astimezone(timezone.utc)).total_seconds()
            if elapsed_seconds > MESSAGE_EDIT_WINDOW_SECONDS:
                raise EditWindowExpiredError(
                    f"El plazo de edición de 5 minutos (300 s) expiró (transcurridos: {int(elapsed_seconds)} s)."
                )

            existing_versions = uow.tickets.get_message_versions(msg["id"])
            now_utc_iso = now_utc.isoformat()
            uow.tickets.add_message_version(
                {
                    "message_id": msg["id"],
                    "ticket_id": ticket["id"],
                    "version_number": len(existing_versions) + 1,
                    "previous_content": msg["message"],
                    "action": "edit",
                    "actor_email": cmd.actor["email"],
                    "created_at": now_utc_iso,
                }
            )
            updated = uow.tickets.update_message(
                msg["id"], {"message": clean_text, "edited_at": now_utc_iso}
            )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "MESSAGE_EDITED",
                    "entity": "ticket_messages",
                    "entity_id": str(msg["id"]),
                    "old_value": msg["message"],
                    "new_value": clean_text,
                }
            )
            uow.commit()

        assert updated is not None
        return updated


class DeleteChatMessageCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: DeleteChatMessageCommand) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)
            if ticket["status"] in ("Cerrado", "Anulado"):
                raise InvalidTransitionError(
                    f"El ticket {ticket['ticket_number']} está en modo solo lectura; no admite eliminaciones."
                )

            msg = uow.tickets.get_message_by_id(ticket["id"], int(cmd.message_id))
            if not msg:
                raise NotFoundError(f"Mensaje #{cmd.message_id} no encontrado en el ticket.")
            if int(msg["sender_id"]) != int(cmd.actor["id"]) and cmd.actor.get("role") != "admin":
                raise ForbiddenError("Solo el autor del mensaje o un administrador puede retirarlo.")
            if msg.get("is_deleted"):
                return msg

            now_utc_iso = datetime.now(timezone.utc).isoformat()
            existing_versions = uow.tickets.get_message_versions(msg["id"])
            uow.tickets.add_message_version(
                {
                    "message_id": msg["id"],
                    "ticket_id": ticket["id"],
                    "version_number": len(existing_versions) + 1,
                    "previous_content": msg["message"],
                    "action": "delete",
                    "actor_email": cmd.actor["email"],
                    "created_at": now_utc_iso,
                }
            )
            updated = uow.tickets.update_message(msg["id"], {"is_deleted": True})
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "MESSAGE_DELETED",
                    "entity": "ticket_messages",
                    "entity_id": str(msg["id"]),
                    "old_value": msg["message"],
                    "new_value": "[borrado lógico participante]",
                }
            )
            uow.commit()

        assert updated is not None
        return updated


class MarkMessagesReadCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: MarkMessagesReadCommand) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)
            read_ids = uow.tickets.mark_messages_read(ticket["id"], cmd.actor["email"])
            uow.commit()
        return {
            "ticket_id": ticket["id"],
            "message_ids": read_ids,
            "read_at": datetime.now(timezone.utc).isoformat(),
            "reader_email": (
                mask_email(cmd.actor["email"])
                if cmd.actor.get("role") == "invitado"
                else cmd.actor["email"]
            ),
        }
