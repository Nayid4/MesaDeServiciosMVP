"""Entidad Ticket, grafo de ciclo de vida ITIL v4 y validaciones CSAT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.domain.common.exceptions import ValidationDomainError
from src.domain.tickets.catalog_rules import ALL_TICKET_STATUSES

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "Registrado": ["Asignado", "Anulado"],
    "Asignado": ["En atención", "Anulado"],
    "En atención": ["En espera", "Resuelto"],
    "En espera": ["En atención"],
    "Resuelto": ["Cerrado", "Reabierto"],
    "Reabierto": ["En atención"],
    "Cerrado": [],
    "Anulado": [],
}


def validate_state_transition(
    current_status: str,
    new_status: str,
    comment: Optional[str] = None,
    diagnosis: Optional[str] = None,
    solution: Optional[str] = None,
    closing_category: Optional[str] = None,
) -> None:
    """Valida reglas ITIL v4 y requisitos documentales para cambios de estado."""
    if current_status not in VALID_TRANSITIONS:
        raise ValueError(f"Estado actual desconocido: '{current_status}'.")
    if new_status not in ALL_TICKET_STATUSES:
        raise ValueError(f"Estado destino desconocido: '{new_status}'.")
    if new_status not in VALID_TRANSITIONS[current_status]:
        allowed = ", ".join(VALID_TRANSITIONS[current_status]) or "ninguno (estado terminal)"
        raise ValueError(
            f"Transición ITIL no permitida de '{current_status}' a '{new_status}'. "
            f"Transiciones permitidas: {allowed}."
        )

    if new_status in ("En espera", "Anulado", "Reabierto"):
        if not comment or not comment.strip():
            raise ValueError(
                f"El cambio a estado '{new_status}' exige un comentario justificativo obligatorio."
            )

    if new_status == "Resuelto":
        if not diagnosis or not diagnosis.strip():
            raise ValueError(
                "Para marcar un ticket como 'Resuelto' es obligatorio registrar el diagnóstico."
            )
        if not solution or len(solution.strip()) < 20:
            raise ValueError(
                "Para marcar un ticket como 'Resuelto' la solución debe tener al menos 20 caracteres."
            )
        if closing_category is not None and not str(closing_category).strip():
            raise ValueError("La categoría de cierre no puede estar vacía.")


def validate_csat_rating(csat_score: int, csat_comment: Optional[str]) -> None:
    """Valida rango 1-5 y exige comentario justificativo cuando la calificación es 1 o 2 (RF-17)."""
    score = int(csat_score)
    if score < 1 or score > 5:
        raise ValidationDomainError("La calificación CSAT debe estar entre 1 y 5 estrellas.")
    if score in (1, 2) and len((csat_comment or "").strip()) < 5:
        raise ValidationDomainError(
            "Para calificaciones de 1 o 2 estrellas es obligatorio registrar un comentario explicando el motivo (mínimo 5 caracteres)."
        )


@dataclass
class Ticket:
    """Ticket institucional de incidencia o solicitud de servicio TIC."""

    id: Optional[int]
    ticket_number: str
    title: str
    description: str
    ticket_type: str
    service_name: str
    area: str
    sede: str
    location: str
    impact: str
    urgency: str
    priority: str
    status: str
    requester_id: int
    requester_email: str
    requester_role: str
    assigned_tech_id: Optional[int] = None
    assigned_tech_email: Optional[str] = None
    sla_response_hours: float = 4.0
    sla_resolution_hours: float = 24.0
    response_deadline: Optional[str] = None
    resolution_deadline: Optional[str] = None
    first_response_at: Optional[str] = None
    paused_at: Optional[str] = None
    paused_seconds: int = 0
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    diagnosis: Optional[str] = None
    solution: Optional[str] = None
    closing_category: Optional[str] = None
    csat_score: Optional[int] = None
    csat_comment: Optional[str] = None
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_human_validated: bool = False
    priority_justification: Optional[str] = None
    sla_breached: bool = False
    sla_alert_75_sent: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
