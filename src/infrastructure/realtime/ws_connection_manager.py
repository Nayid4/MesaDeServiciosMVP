"""Gestor de salas WebSocket en tiempo real por ticket_id y presencia de participantes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

from fastapi import WebSocket

from src.domain.rules import mask_email


@dataclass
class _ConnectedClient:
    websocket: WebSocket
    user_email: str
    full_name: str
    role: str


class TicketWebSocketManager:
    """Administra conexiones WebSocket por ticket y transmite mensajes en vivo."""

    def __init__(self) -> None:
        self._rooms: Dict[int, List[_ConnectedClient]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        ticket_id: int,
        websocket: WebSocket,
        user: Dict[str, Any],
        *,
        already_accepted: bool = False,
    ) -> List[Dict[str, str]]:
        if not already_accepted:
            await websocket.accept()
        display_email = (
            user.get("masked_email") or mask_email(user["email"])
            if user.get("role") == "invitado"
            else user["email"]
        )
        client = _ConnectedClient(
            websocket=websocket,
            user_email=display_email,
            full_name=user.get("full_name") or user.get("name") or display_email,
            role=user["role"],
        )
        async with self._lock:
            room = self._rooms.setdefault(int(ticket_id), [])
            room.append(client)
            participants = self._presence_snapshot(int(ticket_id))

        await self.broadcast_to_ticket(
            ticket_id,
            {
                "type": "presence",
                "ticket_id": int(ticket_id),
                "participants": participants,
            },
        )
        return participants

    async def disconnect(self, ticket_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(int(ticket_id), [])
            self._rooms[int(ticket_id)] = [c for c in room if c.websocket is not websocket]
            if not self._rooms[int(ticket_id)]:
                self._rooms.pop(int(ticket_id), None)
                participants: List[Dict[str, str]] = []
            else:
                participants = self._presence_snapshot(int(ticket_id))

        if participants:
            await self.broadcast_to_ticket(
                ticket_id,
                {
                    "type": "presence",
                    "ticket_id": int(ticket_id),
                    "participants": participants,
                },
            )

    def _presence_snapshot(self, ticket_id: int) -> List[Dict[str, str]]:
        seen: Dict[str, Dict[str, str]] = {}
        for client in self._rooms.get(int(ticket_id), []):
            seen[client.user_email] = {
                "email": client.user_email,
                "full_name": client.full_name,
                "role": client.role,
            }
        return list(seen.values())

    def _sanitize_payload_for_client(
        self, client: _ConnectedClient, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if client.role != "invitado":
            return payload
        sanitized = dict(payload)
        if isinstance(payload.get("message"), dict):
            m = dict(payload["message"])
            m["sender_email"] = mask_email(m.get("sender_email", ""))
            sanitized["message"] = m
        if isinstance(payload.get("participants"), list):
            sanitized["participants"] = [
                {
                    **p,
                    "email": mask_email(p.get("email", "")) if "@" in str(p.get("email", "")) else p.get("email", ""),
                }
                for p in payload["participants"]
            ]
        return sanitized

    async def broadcast_to_ticket(self, ticket_id: int, payload: Dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._rooms.get(int(ticket_id), []))

        dead_sockets: List[WebSocket] = []
        for client in targets:
            try:
                out_payload = self._sanitize_payload_for_client(client, payload)
                await client.websocket.send_json(out_payload)
            except Exception:
                dead_sockets.append(client.websocket)

        if dead_sockets:
            async with self._lock:
                room = self._rooms.get(int(ticket_id), [])
                self._rooms[int(ticket_id)] = [
                    c for c in room if c.websocket not in dead_sockets
                ]
                if not self._rooms[int(ticket_id)]:
                    self._rooms.pop(int(ticket_id), None)


ws_connection_manager = TicketWebSocketManager()
