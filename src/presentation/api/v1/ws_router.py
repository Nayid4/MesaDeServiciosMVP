"""Router WebSocket v1 para chat en tiempo real por ticket (/api/v1/ws/tickets/{id})."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from src.application.tickets import (
    DeleteChatMessageCommand,
    EditChatMessageCommand,
    MarkMessagesReadCommand,
    SendChatMessageCommand,
    authorize_ticket_access,
)
from src.domain.exceptions import DomainError
from src.domain.rules import mask_email
from src.infrastructure.composition import create_uow, get_cqrs_bus
from src.infrastructure.realtime.ws_connection_manager import ws_connection_manager
from src.presentation.api.dependencies.auth_guards import resolve_user_from_token

router = APIRouter(tags=["WebSocket Tiempo Real"])


def _redeem_ws_ticket(raw_ticket: str, ticket_id: int) -> Optional[Dict[str, Any]]:
    token_hash = hashlib.sha256(raw_ticket.strip().encode("utf-8")).hexdigest()
    now_utc_iso = datetime.now(timezone.utc).isoformat()
    with create_uow() as uow:
        uow.begin_immediate()
        actor = uow.tickets.consume_ws_ticket(token_hash, int(ticket_id), now_utc_iso)
        uow.commit()
    return actor


async def _authenticate_ws_connection(
    websocket: WebSocket,
    ticket_id: int,
    *,
    ws_ticket: Optional[str],
    auth: Optional[str],
    token: Optional[str],
) -> tuple[Optional[Dict[str, Any]], bool]:
    if not ws_ticket and not token and auth != "first_message":
        await websocket.close(code=1008)
        return None, False

    already_accepted = False
    user: Optional[Dict[str, Any]] = None
    if ws_ticket:
        user = _redeem_ws_ticket(ws_ticket, ticket_id)
    elif token:
        user = resolve_user_from_token(token, allow_guest=True)
    elif auth == "first_message":
        await websocket.accept()
        already_accepted = True
        auth_payload = json.loads(await websocket.receive_text())
        if not isinstance(auth_payload, dict) or auth_payload.get("type") != "auth":
            await websocket.close(code=1008)
            return None, already_accepted
        if auth_payload.get("ws_ticket"):
            user = _redeem_ws_ticket(str(auth_payload["ws_ticket"]), ticket_id)
        elif auth_payload.get("token"):
            user = resolve_user_from_token(str(auth_payload["token"]), allow_guest=True)

    if not user:
        await websocket.close(code=1008)
        return None, already_accepted
    return user, already_accepted


async def _send_ws_error(websocket: WebSocket, exc: Exception, default_code: str) -> None:
    await websocket.send_json(
        {
            "type": "error",
            "code": getattr(exc, "code", default_code),
            "status": getattr(exc, "status_code", 400),
            "detail": getattr(exc, "detail", str(exc)),
        }
    )


async def _handle_ws_event(
    websocket: WebSocket, ticket_id: int, user: Dict[str, Any], data: Dict[str, Any]
) -> None:
    bus = get_cqrs_bus()
    evt_type = str(data.get("type") or "message").strip().lower()

    if evt_type == "typing":
        actor_label = (
            user.get("masked_email") or mask_email(user["email"])
            if user.get("role") == "invitado"
            else user["email"]
        )
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id,
            {
                "type": "typing",
                "ticket_id": int(ticket_id),
                "actor_email": actor_label,
                "full_name": user.get("full_name") or actor_label,
                "is_typing": bool(data.get("is_typing", True)),
            },
        )
        return

    if evt_type == "read":
        res = bus.execute(MarkMessagesReadCommand(actor=user, ticket_id=ticket_id))
        if res["message_ids"]:
            await ws_connection_manager.broadcast_to_ticket(
                ticket_id, {"type": "messages_read", **res}
            )
        return

    if evt_type == "edit_message":
        try:
            edited = bus.execute(
                EditChatMessageCommand(
                    actor=user,
                    ticket_id=ticket_id,
                    message_id=int(data["message_id"]),
                    new_content=str(data.get("content", "")),
                )
            )
        except (DomainError, KeyError, TypeError, ValueError) as exc:
            await _send_ws_error(websocket, exc, "EDIT_ERROR")
            return
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "message_edited", "ticket_id": int(ticket_id), "message": edited}
        )
        return

    if evt_type == "delete_message":
        try:
            deleted = bus.execute(
                DeleteChatMessageCommand(
                    actor=user, ticket_id=ticket_id, message_id=int(data["message_id"])
                )
            )
        except (DomainError, KeyError, TypeError, ValueError) as exc:
            await _send_ws_error(websocket, exc, "DELETE_ERROR")
            return
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "message_deleted", "ticket_id": int(ticket_id), "message": deleted}
        )
        return

    client_msg_id = data.get("client_message_id")
    reply_to_id = data.get("reply_to_message_id")
    try:
        persisted = bus.execute(
            SendChatMessageCommand(
                actor=user,
                ticket_id=ticket_id,
                content=str(data.get("content", "")),
                client_message_id=str(client_msg_id) if client_msg_id else None,
                reply_to_message_id=int(reply_to_id) if reply_to_id is not None else None,
            )
        )
    except DomainError as exc:
        await _send_ws_error(websocket, exc, "MESSAGE_ERROR")
        return

    if persisted.get("deduplicated"):
        msg_out = dict(persisted)
        if user.get("role") == "invitado":
            msg_out["sender_email"] = mask_email(msg_out.get("sender_email", ""))
        await websocket.send_json({"type": "message", "ticket_id": int(ticket_id), "message": msg_out})
    else:
        await ws_connection_manager.broadcast_to_ticket(
            ticket_id, {"type": "message", "ticket_id": int(ticket_id), "message": persisted}
        )


@router.websocket("/api/v1/ws/tickets/{ticket_id}")
async def ticket_chat_websocket(
    websocket: WebSocket,
    ticket_id: int,
    ws_ticket: Optional[str] = Query(default=None),
    auth: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
) -> None:
    try:
        user, already_accepted = await _authenticate_ws_connection(
            websocket, ticket_id, ws_ticket=ws_ticket, auth=auth, token=token
        )
        if not user:
            return
        with create_uow() as uow:
            ticket = uow.tickets.get_by_id(ticket_id)
        if not ticket:
            await websocket.close(code=1008)
            return
        authorize_ticket_access(user, ticket)
    except Exception:
        try:
            await websocket.close(code=1008)
        except Exception:
            pass
        return

    participants = await ws_connection_manager.connect(
        ticket_id, websocket, user, already_accepted=already_accepted
    )
    visible_participants = (
        [
            {
                **p,
                "email": mask_email(p.get("email", "")) if "@" in str(p.get("email", "")) else p.get("email", ""),
            }
            for p in participants
        ]
        if user.get("role") == "invitado"
        else participants
    )
    await websocket.send_json(
        {
            "type": "ready",
            "ticket_id": int(ticket_id),
            "read_only": ticket["status"] in ("Cerrado", "Anulado"),
            "status": ticket["status"],
            "participants": visible_participants,
        }
    )

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                data = {"type": "message", "content": raw_text}
            if not isinstance(data, dict):
                data = {"type": "message", "content": str(data)}

            with create_uow() as uow:
                latest_ticket = uow.tickets.get_by_id(ticket_id)
            if not latest_ticket:
                await websocket.close(code=1008)
                break
            try:
                authorize_ticket_access(user, latest_ticket)
            except DomainError:
                await websocket.close(code=1008)
                break

            await _handle_ws_event(websocket, ticket_id, user, data)
    except WebSocketDisconnect:
        await ws_connection_manager.disconnect(ticket_id, websocket)
    except Exception:
        await ws_connection_manager.disconnect(ticket_id, websocket)
