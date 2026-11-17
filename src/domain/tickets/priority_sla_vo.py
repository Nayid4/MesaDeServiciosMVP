"""Matriz 3x3 OR-03 (Impacto x Urgencia) y Value Objects PriorityMatrix / SLADeadline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from src.domain.common.exceptions import ValidationDomainError
from src.domain.tickets.sla_calendar_rules import (
    add_business_hours,
    calculate_sla_status,
    now_bogota,
)

SLA_BY_PRIORITY: Dict[str, Dict[str, float]] = {
    "P1 Crítica": {"sla_response_hours": 0.5, "sla_resolution_hours": 4.0},
    "P2 Alta": {"sla_response_hours": 1.0, "sla_resolution_hours": 8.0},
    "P3 Media": {"sla_response_hours": 4.0, "sla_resolution_hours": 24.0},
    "P4 Baja": {"sla_response_hours": 8.0, "sla_resolution_hours": 40.0},
}

OR03_PRIORITY_MATRIX: Dict[Tuple[str, str], str] = {
    ("Alto", "Alta"): "P1 Crítica",
    ("Alto", "Media"): "P2 Alta",
    ("Alto", "Baja"): "P3 Media",
    ("Medio", "Alta"): "P2 Alta",
    ("Medio", "Media"): "P3 Media",
    ("Medio", "Baja"): "P4 Baja",
    ("Bajo", "Alta"): "P3 Media",
    ("Bajo", "Media"): "P4 Baja",
    ("Bajo", "Baja"): "P4 Baja",
}


def calculate_priority_or03(
    impact: str,
    urgency: str,
    custom_sla_table: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Calcula prioridad y objetivos SLA aplicando la matriz 3x3 de la regla OR-03."""
    impact_norm = impact.strip().capitalize()
    urgency_norm = urgency.strip().capitalize()
    if (impact_norm, urgency_norm) not in OR03_PRIORITY_MATRIX:
        raise ValueError(
            f"Combinación inválida para matriz OR-03: Impacto='{impact}', Urgencia='{urgency}'."
        )
    priority = OR03_PRIORITY_MATRIX[(impact_norm, urgency_norm)]
    sla_source = custom_sla_table or SLA_BY_PRIORITY
    sla_values = sla_source[priority]
    return {
        "impact": impact_norm,
        "urgency": urgency_norm,
        "priority": priority,
        "sla_response_hours": float(sla_values["sla_response_hours"]),
        "sla_resolution_hours": float(sla_values["sla_resolution_hours"]),
    }


@dataclass(frozen=True)
class PriorityMatrix:
    """Resultado inmutable de la matriz de priorización 3x3 OR-03 (Impacto x Urgencia)."""

    impact: str
    urgency: str
    priority: str
    sla_response_hours: float
    sla_resolution_hours: float

    @classmethod
    def evaluate(
        cls,
        impact: str,
        urgency: str,
        custom_sla_table: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> "PriorityMatrix":
        try:
            result = calculate_priority_or03(
                impact=impact,
                urgency=urgency,
                custom_sla_table=custom_sla_table,
            )
        except ValueError as exc:
            raise ValidationDomainError(str(exc)) from exc
        return cls(
            impact=result["impact"],
            urgency=result["urgency"],
            priority=result["priority"],
            sla_response_hours=result["sla_response_hours"],
            sla_resolution_hours=result["sla_resolution_hours"],
        )


@dataclass(frozen=True)
class SLADeadline:
    """Cálculo de fechas objetivo de respuesta y resolución en horas hábiles UPC (OR-04)."""

    created_at: datetime
    response_deadline: datetime
    resolution_deadline: datetime
    sla_response_hours: float
    sla_resolution_hours: float

    @classmethod
    def compute(
        cls,
        priority_matrix: PriorityMatrix,
        created_at: Optional[datetime] = None,
    ) -> "SLADeadline":
        start = created_at or now_bogota()
        return cls(
            created_at=start,
            response_deadline=add_business_hours(start, priority_matrix.sla_response_hours),
            resolution_deadline=add_business_hours(start, priority_matrix.sla_resolution_hours),
            sla_response_hours=priority_matrix.sla_response_hours,
            sla_resolution_hours=priority_matrix.sla_resolution_hours,
        )

    @staticmethod
    def evaluate_semaphore(ticket: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        return calculate_sla_status(ticket, now=now)
