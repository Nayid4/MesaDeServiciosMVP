"""Fachada modular para el gestor de salas WebSocket de tickets."""

from __future__ import annotations

from src.infrastructure.realtime.ws_connection_manager import TicketWebSocketManager

__all__ = ["TicketWebSocketManager"]
