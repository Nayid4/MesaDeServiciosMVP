"""Pruebas unitarias de reglas de dominio ITIL v4, matriz OR-03, SLA y carga técnica."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.domain.rules import (
    BOGOTA_TZ,
    OR03_PRIORITY_MATRIX,
    add_business_hours,
    calculate_priority_or03,
    calculate_sla_status,
    format_ticket_number,
    select_technician_least_load,
    validate_attachment,
    validate_state_transition,
)


def test_format_ticket_number_pattern():
    assert format_ticket_number(1, 2026) == "MS-2026-000001"
    assert format_ticket_number(425, 2026) == "MS-2026-000425"
    with pytest.raises(ValueError):
        format_ticket_number(0, 2026)


@pytest.mark.parametrize(
    "impact,urgency,expected_prio,expected_resp,expected_res",
    [
        ("Alto", "Alta", "P1 Crítica", 0.5, 4.0),
        ("Alto", "Media", "P2 Alta", 1.0, 8.0),
        ("Alto", "Baja", "P3 Media", 4.0, 24.0),
        ("Medio", "Alta", "P2 Alta", 1.0, 8.0),
        ("Medio", "Media", "P3 Media", 4.0, 24.0),
        ("Medio", "Baja", "P4 Baja", 8.0, 40.0),
        ("Bajo", "Alta", "P3 Media", 4.0, 24.0),
        ("Bajo", "Media", "P4 Baja", 8.0, 40.0),
        ("Bajo", "Baja", "P4 Baja", 8.0, 40.0),
    ],
)
def test_or03_matrix_all_9_combinations(impact, urgency, expected_prio, expected_resp, expected_res):
    assert len(OR03_PRIORITY_MATRIX) == 9
    res = calculate_priority_or03(impact, urgency)
    assert res["priority"] == expected_prio
    assert res["sla_response_hours"] == expected_resp
    assert res["sla_resolution_hours"] == expected_res


def test_or03_invalid_values():
    with pytest.raises(ValueError):
        calculate_priority_or03("Crítico", "Alta")


def test_itil_state_transitions_and_solution_validation():
    # Transición válida normal
    validate_state_transition("Registrado", "Asignado")
    validate_state_transition("Asignado", "En atención")
    validate_state_transition("En atención", "En espera", comment="Esperando captura de pantalla del docente")

    # Transición prohibida (Registrado -> Resuelto directo)
    with pytest.raises(ValueError):
        validate_state_transition("Registrado", "Resuelto", diagnosis="X", solution="A" * 25)

    # Falta comentario en En espera / Anulado / Reabierto
    with pytest.raises(ValueError):
        validate_state_transition("En atención", "En espera", comment="")
    with pytest.raises(ValueError):
        validate_state_transition("Resuelto", "Reabierto", comment="   ")

    # Solución menor a 20 caracteres rechazada (RF-15)
    with pytest.raises(ValueError):
        validate_state_transition(
            "En atención",
            "Resuelto",
            diagnosis="Falla en switch de piso",
            solution="Se reinició.",
        )

    # Solución >= 20 caracteres y diagnóstico válidos
    validate_state_transition(
        "En atención",
        "Resuelto",
        diagnosis="Puerto PoE deshabilitado en switch del bloque B",
        solution="Se habilitó puerto PoE y se verificó conectividad Eduroam en salón 204.",
        closing_category="Solución definitiva en sitio",
    )


def test_select_technician_least_load_and_tiebreak():
    techs = [
        {"id": 1, "email": "t1@unicesar.edu.co", "is_active": True, "open_tickets_count": 3, "last_assigned_at": "2026-10-01T09:00:00"},
        {"id": 2, "email": "t2@unicesar.edu.co", "is_active": True, "open_tickets_count": 1, "last_assigned_at": "2026-10-02T10:00:00"},
        {"id": 3, "email": "t3@unicesar.edu.co", "is_active": True, "open_tickets_count": 1, "last_assigned_at": "2026-10-01T08:00:00"},
        {"id": 4, "email": "t4@unicesar.edu.co", "is_active": False, "open_tickets_count": 0, "last_assigned_at": None},
    ]
    chosen = select_technician_least_load(techs)
    assert chosen is not None
    # Empate en carga=1 entre id 2 y id 3; id 3 tiene last_assigned_at más antiguo y id 4 está inactivo
    assert chosen["id"] == 3


def test_business_hours_and_sla_semaphore():
    # Viernes 18:00 + 2 horas hábiles -> Sábado 09:00 (viernes cierra a las 19:00, sábado abre a las 8:00)
    friday_evening = datetime(2026, 11, 13, 18, 0, tzinfo=BOGOTA_TZ)
    deadline = add_business_hours(friday_evening, 2.0)
    assert deadline.weekday() == 5
    assert deadline.hour == 9

    created = datetime(2026, 11, 14, 8, 0, tzinfo=BOGOTA_TZ)
    ticket_base = {
        "status": "En atención",
        "sla_resolution_hours": 4.0,
        "created_at": created.isoformat(),
        "paused_seconds": 0,
    }
    assert calculate_sla_status(ticket_base, now=datetime(2026, 11, 14, 10, 0, tzinfo=BOGOTA_TZ))["semaphore"] == "Verde"
    assert calculate_sla_status(ticket_base, now=datetime(2026, 11, 14, 11, 10, tzinfo=BOGOTA_TZ))["semaphore"] == "Amarillo"
    assert calculate_sla_status(ticket_base, now=datetime(2026, 11, 14, 12, 30, tzinfo=BOGOTA_TZ))["semaphore"] == "Rojo"


def test_attachment_validation():
    validate_attachment("captura_error.png", 1024 * 500)
    with pytest.raises(ValueError):
        validate_attachment("script.exe", 500)
    with pytest.raises(ValueError):
        validate_attachment("archivo_grande.pdf", 12 * 1024 * 1024)
