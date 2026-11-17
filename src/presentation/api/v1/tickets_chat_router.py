"""Router REST v1 de chat en tiempo real, adjuntos privados y tickets WebSocket."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.application.tickets import (
    CreateWsTicketCommand,
    DeleteChatMessageCommand,
    EditChatMessageCommand,
    ListTicketMessagesQuery,
    MarkMessagesReadCommand,
    PRIVATE_ATTACHMENTS_ROOT,
    SendChatMessageCommand,
    UploadTicketAttachmentsCommand,
    authorize_ticket_access,
)
from src.domain.exceptions import ForbiddenError, NotFoundError
from src.domain.rules import mask_email, sanitize_filename
from src.infrastructure.composition import create_uow, get_cqrs_bus
from src.infrastructure.realtime.ws_connection_manager import ws_connection_manager
from src.infrastructure.security import verify_attachment_signature
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_optional_ticket_actor,
    get_ticket_actor,
)

router = APIRouter(prefix="/api/v1/tickets", tags=["Chat Multimedia de Tickets"])


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    client_message_id: Optional[str] = None
    reply_to_message_id: Optional[int] = None


class EditChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


def _resolve_attachments_root() -> Path:
    custom = os.environ.get("CASAGBI_ATTACHMENTS_DIR")
    return Path(custom).resolve() if custom else PRIVATE_ATTACHMENTS_ROOT.resolve()


def _mask_msg_for_actor(msg: Dict[str, Any], actor: Dict[str, Any]) -> Dict[str, Any]:
    if actor.get("role") != "invitado":
        return msg
    clean = dict(msg)
    clean["sender_email"] = mask_email(clean.get("sender_email", ""))
    return clean


@router.post("/{ticket_id}/ws-ticket")
def issue_ws_ticket(
    ticket_id: int,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(CreateWsTicketCommand(actor=current_actor, ticket_id=ticket_id))


@router.get("/{ticket_id}/messages")
def list_ticket_messages(
    ticket_id: int,
    after_id: int = Query(default=0, ge=0),
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        ListTicketMessagesQuery(actor=current_actor, ticket_id=ticket_id, after_id=after_id)
    )


@router.post("/{ticket_id}/messages", status_code=201)
async def send_ticket_message(
    ticket_id: int,
    payload: ChatMessageRequest,
    request: Request,
    response: Response,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    msg = get_cqrs_bus().execute(
        SendChatMessageCommand(
            actor=current_actor,
            ticket_id=ticket_id,
            content=payload.content,
            client_message_id=payload.client_message_id,
            reply_to_message_id=payload.reply_to_message_id,
            ip_address=get_client_ip(request),
        )
    )
    if msg.get("deduplicated"):
        response.status_code = 200
    else:
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "message", "ticket_id": ticket_id, "message": msg}
        )
    return {"message": _mask_msg_for_actor(msg, current_actor)}


@router.patch("/{ticket_id}/messages/{message_id}")
async def edit_ticket_message(
    ticket_id: int,
    message_id: int,
    payload: EditChatMessageRequest,
    request: Request,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    edited = get_cqrs_bus().execute(
        EditChatMessageCommand(
            actor=current_actor,
            ticket_id=ticket_id,
            message_id=message_id,
            new_content=payload.content,
            ip_address=get_client_ip(request),
        )
    )
    await ws_connection_manager.broadcast_to_ticket(
        ticket_id, {"type": "message_edited", "ticket_id": ticket_id, "message": edited}
    )
    return {"message": _mask_msg_for_actor(edited, current_actor)}


@router.delete("/{ticket_id}/messages/{message_id}")
async def delete_ticket_message(
    ticket_id: int,
    message_id: int,
    request: Request,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    deleted = get_cqrs_bus().execute(
        DeleteChatMessageCommand(
            actor=current_actor,
            ticket_id=ticket_id,
            message_id=message_id,
            ip_address=get_client_ip(request),
        )
    )
    await ws_connection_manager.broadcast_to_ticket(
        ticket_id, {"type": "message_deleted", "ticket_id": ticket_id, "message": deleted}
    )
    return {"message": _mask_msg_for_actor(deleted, current_actor)}


@router.post("/{ticket_id}/messages/read")
async def mark_ticket_messages_read(
    ticket_id: int,
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    res = get_cqrs_bus().execute(MarkMessagesReadCommand(actor=current_actor, ticket_id=ticket_id))
    if res["message_ids"]:
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "messages_read", **res}
        )
    return res


@router.post("/{ticket_id}/attachments", status_code=201)
async def upload_ticket_attachments(
    ticket_id: int,
    request: Request,
    response: Response,
    files: List[UploadFile] = File(...),
    content: str = Form(default=""),
    client_message_id: Optional[str] = Form(default=None),
    reply_to_message_id: Optional[int] = Form(default=None),
    audio_duration_seconds: Optional[float] = Form(default=None),
    current_actor: Dict[str, Any] = Depends(get_ticket_actor),
) -> Dict[str, Any]:
    file_entries = [
        {"filename": f.filename or "archivo.bin", "content": await f.read()} for f in files
    ]
    created_msg = get_cqrs_bus().execute(
        UploadTicketAttachmentsCommand(
            actor=current_actor,
            ticket_id=ticket_id,
            files=file_entries,
            content=content,
            client_message_id=client_message_id,
            reply_to_message_id=reply_to_message_id,
            audio_duration_seconds=audio_duration_seconds,
            attachments_root=_resolve_attachments_root(),
            ip_address=get_client_ip(request),
        )
    )
    if created_msg.get("deduplicated"):
        response.status_code = 200
    else:
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "message", "ticket_id": ticket_id, "message": created_msg}
        )
    return {"message": _mask_msg_for_actor(created_msg, current_actor)}


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
def download_ticket_attachment(
    ticket_id: int,
    attachment_id: int,
    expires: Optional[int] = Query(default=None),
    sig: Optional[str] = Query(default=None),
    actor: Optional[Dict[str, Any]] = Depends(get_optional_ticket_actor),
) -> FileResponse:
    signed_valid = False
    if expires is not None or sig is not None:
        if expires is None or not sig or not verify_attachment_signature(
            ticket_id, attachment_id, int(expires), sig
        ):
            raise ForbiddenError("El enlace firmado de descarga ha expirado o su firma es inválida.")
        signed_valid = True

    with create_uow() as uow:
        ticket = uow.tickets.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError(f"Ticket #{ticket_id} no encontrado.")
        if not signed_valid:
            if actor is None:
                raise ForbiddenError(
                    "Se requiere enlace firmado vigente de 10 minutos o autorización explícita del ticket."
                )
            authorize_ticket_access(actor, ticket)

        att = uow.tickets.get_attachment_by_id(ticket_id, attachment_id)
        if not att:
            raise NotFoundError(f"Adjunto #{attachment_id} no encontrado en el ticket.")

    root_dir = _resolve_attachments_root()
    file_path = (root_dir / str(att["storage_rel_path"])).resolve()
    if not file_path.is_relative_to(root_dir) or not file_path.is_file():
        raise NotFoundError("El archivo físico solicitado no está disponible en almacenamiento privado.")

    safe_name = sanitize_filename(att["original_name"])
    return FileResponse(
        path=file_path,
        media_type=att["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=600",
        },
    )
