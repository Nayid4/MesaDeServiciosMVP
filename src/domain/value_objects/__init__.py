"""Fachada retrocompatible de Value Objects inmutables del dominio CASAGBI."""

from src.domain.common.pagination import PagedResult, PageRequest
from src.domain.tickets.priority_sla_vo import PriorityMatrix, SLADeadline
from src.domain.tickets.ticket_code_vo import TicketCode

__all__ = [
    "PageRequest",
    "PagedResult",
    "PriorityMatrix",
    "SLADeadline",
    "TicketCode",
]
