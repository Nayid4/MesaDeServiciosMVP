"""Reglas de negocio invariantes del dominio CASAGBI (ITIL v4 - UPC)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

BOGOTA_TZ = timezone(timedelta(hours=-5), name="America/Bogota")

TICKET_NUMBER_PATTERN = re.compile(r"^MS-\d{4}-\d{6}$")

INSTITUTIONAL_DOMAIN = "@unicesar.edu.co"

OPEN_TICKET_STATUSES = ("Registrado", "Asignado", "En atención", "En espera", "Reabierto")
ASSIGNED_LOAD_STATUSES = ("Asignado", "En atención", "En espera", "Reabierto")
ALL_TICKET_STATUSES = (
    "Registrado",
    "Asignado",
    "En atención",
    "En espera",
    "Resuelto",
    "Reabierto",
    "Cerrado",
    "Anulado",
)

CLOSING_CATEGORIES = [
    "Solución definitiva en sitio",
    "Solución remota / configuración",
    "Restablecimiento de acceso / credenciales",
    "Escalado / cambio de hardware",
    "Orientación al usuario / autoservicio",
]

ALLOWED_ATTACHMENT_EXTENSIONS = {"jpg", "jpeg", "png", "pdf", "docx", "xlsx"}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_TICKET = 5

VALID_ROLES = ("usuario", "tecnico", "coordinador", "director", "admin")

ROLE_LABELS = {
    "usuario": "Usuario institucional",
    "tecnico": "Técnico de soporte",
    "coordinador": "Coordinador de mesa",
    "director": "Director de TIC",
    "admin": "Administrador del sistema",
}

ROLE_PERMISSIONS = {
    "usuario": {
        "create_ticket",
        "track_own_tickets",
        "chat_own_ticket",
        "confirm_or_reopen_own_ticket",
        "rate_service",
        "use_ai_assistant",
    },
    "tecnico": {
        "create_ticket",
        "track_assigned_tickets",
        "manage_assigned_tickets",
        "chat_assigned_ticket",
        "propose_kb_article",
        "view_own_kpis",
        "use_ai_assistant",
    },
    "coordinador": {
        "create_ticket",
        "track_all_area_tickets",
        "manage_tickets",
        "reassign_ticket",
        "adjust_priority",
        "manage_kb",
        "view_area_kpis",
        "export_reports",
        "view_ml_lab",
        "use_ai_assistant",
    },
    "director": {
        "track_all_tickets",
        "view_global_kpis",
        "export_reports",
        "view_ml_lab",
        "use_ai_assistant",
    },
    "admin": {
        "create_ticket",
        "track_all_tickets",
        "manage_tickets",
        "reassign_ticket",
        "adjust_priority",
        "manage_kb",
        "manage_users",
        "manage_catalog_sla",
        "view_audit_logs",
        "view_global_kpis",
        "export_reports",
        "manage_ml_lab",
        "use_ai_assistant",
    },
}

UPC_SEDES = [
    "Sede Sabanas (Valledupar)",
    "Sede Hurtado (Valledupar)",
    "Seccional Aguachica",
]

UPC_LOCATIONS = [
    "Bloque A",
    "Bloque B",
    "Bloque C",
    "Bloque D",
    "Laboratorios de Cómputo",
    "Biblioteca",
    "Edificio Administrativo",
]

UPC_TECHNICAL_AREAS = [
    "Redes e Infraestructura",
    "Sistemas de Información",
    "Identidad y Accesos",
    "Soporte en Campo",
    "Mesa de Software",
]

UPC_SERVICE_CATALOG: Dict[str, Dict[str, str]] = {
    "Conectividad y Redes Wi-Fi": {
        "area": "Redes e Infraestructura",
        "base_impact": "Alto",
        "default_type": "Incidencia",
        "description": "Conectividad cableada, red inalámbrica Eduroam, puntos de acceso y enlaces entre bloques.",
    },
    "Plataformas Académicas (Aula Web / Vortal)": {
        "area": "Sistemas de Información",
        "base_impact": "Alto",
        "default_type": "Incidencia",
        "description": "Acceso y errores en Aula Web, Vortal académico, matrícula en línea y registro de notas.",
    },
    "Correo Institucional y Cuentas": {
        "area": "Identidad y Accesos",
        "base_impact": "Medio",
        "default_type": "Solicitud",
        "description": "Activación de cuentas @unicesar.edu.co, desbloqueo y restablecimiento de contraseña.",
    },
    "Aulas Inteligentes y Videoproyectores": {
        "area": "Soporte en Campo",
        "base_impact": "Medio",
        "default_type": "Incidencia",
        "description": "Videoproyectores, pantallas interactivas, audio de salón y cableado audiovisual en aulas.",
    },
    "Equipos de Cómputo e Impresoras": {
        "area": "Soporte en Campo",
        "base_impact": "Bajo",
        "default_type": "Incidencia",
        "description": "Fallas de hardware en computadores, portátiles, escáneres e impresoras institucionales.",
    },
    "Software y Licenciamiento": {
        "area": "Mesa de Software",
        "base_impact": "Bajo",
        "default_type": "Solicitud",
        "description": "Instalación, actualización y licenciamiento de software académico y de oficina.",
    },
}

SLA_BY_PRIORITY: Dict[str, Dict[str, float]] = {
    "P1 Crítica": {"sla_response_hours": 0.5, "sla_resolution_hours": 4.0},
    "P2 Alta": {"sla_response_hours": 1.0, "sla_resolution_hours": 8.0},
    "P3 Media": {"sla_response_hours": 4.0, "sla_resolution_hours": 24.0},
    "P4 Baja": {"sla_response_hours": 8.0, "sla_resolution_hours": 40.0},
}

# Matriz 3x3 oficial OR-03 (Impacto x Urgencia)
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

# Grafo de transiciones válidas ITIL v4 (Figura 1 / RF-10)
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

# Festivos fijos de referencia en Colombia (OR-04)
COLOMBIA_HOLIDAYS_2026 = {
    "2026-01-01",
    "2026-01-12",
    "2026-03-23",
    "2026-04-02",
    "2026-04-03",
    "2026-05-01",
    "2026-05-18",
    "2026-06-08",
    "2026-06-15",
    "2026-06-29",
    "2026-07-20",
    "2026-08-07",
    "2026-08-17",
    "2026-10-12",
    "2026-11-02",
    "2026-11-16",
    "2026-12-08",
    "2026-12-25",
}


def now_bogota() -> datetime:
    """Retorna la fecha y hora actual en zona horaria America/Bogota (UTC-5)."""
    return datetime.now(BOGOTA_TZ)


def format_ticket_number(seq: int, year: int = 2026) -> str:
    """Genera el consecutivo institucional obligatorio MS-AAAA-NNNNNN."""
    if seq < 1:
        raise ValueError("El consecutivo del ticket debe ser mayor o igual a 1.")
    return f"MS-{int(year):04d}-{int(seq):06d}"


def is_valid_institutional_email(email: str) -> bool:
    """Valida que el correo pertenezca al dominio institucional de la UPC."""
    if not email or "@" not in email:
        return False
    normalized = email.strip().lower()
    local_part, _, domain = normalized.partition("@")
    return bool(local_part) and domain == "unicesar.edu.co"


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


def get_service_metadata(service_name: str) -> Dict[str, str]:
    """Retorna área responsable e impacto base de un servicio del catálogo UPC."""
    if service_name not in UPC_SERVICE_CATALOG:
        raise ValueError(f"Servicio no registrado en catálogo UPC: '{service_name}'.")
    return UPC_SERVICE_CATALOG[service_name]


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


def select_technician_least_load(technicians: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Selecciona el técnico activo con menor carga de tickets abiertos (RF-06).
    En caso de empate, elige al técnico cuya última asignación sea más antigua (o nunca asignado).
    """
    active = [t for t in technicians if bool(t.get("is_active", True))]
    if not active:
        return None

    def _sort_key(tech: Dict[str, Any]) -> Tuple[int, str, int]:
        load = int(tech.get("open_tickets_count", 0))
        last_assigned = tech.get("last_assigned_at") or "0000-01-01T00:00:00"
        tech_id = int(tech.get("id", 0))
        return (load, str(last_assigned), tech_id)

    return min(active, key=_sort_key)


def _is_business_day(dt: datetime, holidays: Optional[set] = None) -> bool:
    """Indica si la fecha corresponde a un día hábil UPC (Lunes a Sábado sin festivos)."""
    active_holidays = holidays if holidays is not None else COLOMBIA_HOLIDAYS_2026
    if dt.weekday() == 6:  # Domingo
        return False
    if dt.strftime("%Y-%m-%d") in active_holidays:
        return False
    return True


def _business_window_for_day(dt: datetime) -> Tuple[int, int]:
    """Retorna hora de inicio y fin de horario hábil OR-04 (L-V 7-19, Sáb 8-12)."""
    if dt.weekday() == 5:  # Sábado
        return (8, 12)
    return (7, 19)


def add_business_hours(
    start_dt: datetime,
    hours_to_add: float,
    holidays: Optional[set] = None,
) -> datetime:
    """Suma horas hábiles siguiendo la regla OR-04 (L-V 7:00-19:00, Sáb 8:00-12:00)."""
    if start_dt.tzinfo is None:
        current = start_dt.replace(tzinfo=BOGOTA_TZ)
    else:
        current = start_dt.astimezone(BOGOTA_TZ)

    remaining_minutes = max(0, int(round(hours_to_add * 60)))
    if remaining_minutes == 0:
        return current

    safety_days = 0
    while remaining_minutes > 0 and safety_days < 365:
        if not _is_business_day(current, holidays):
            current = (current + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
            safety_days += 1
            continue

        start_h, end_h = _business_window_for_day(current)
        window_start = current.replace(hour=start_h, minute=0, second=0, microsecond=0)
        window_end = current.replace(hour=end_h, minute=0, second=0, microsecond=0)

        if current < window_start:
            current = window_start
        if current >= window_end:
            current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            safety_days += 1
            continue

        available_minutes = int((window_end - current).total_seconds() // 60)
        if remaining_minutes <= available_minutes:
            return current + timedelta(minutes=remaining_minutes)

        remaining_minutes -= available_minutes
        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        safety_days += 1

    return current


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Convierte una cadena ISO 8601 a datetime en zona horaria Bogotá."""
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BOGOTA_TZ)
    return dt.astimezone(BOGOTA_TZ)


def calculate_sla_status(ticket: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Calcula el porcentaje consumido del SLA de resolución y el semáforo operativo:
    - Verde: < 75 % consumido (o resuelto/cerrado dentro de SLA)
    - Amarillo: 75 % <= consumido <= 100 %
    - Rojo: > 100 % consumido (SLA vencido)
    Descuenta el tiempo acumulado en pausa ('En espera').
    """
    current_time = now or now_bogota()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=BOGOTA_TZ)

    status = ticket.get("status", "Registrado")
    sla_hours = float(ticket.get("sla_resolution_hours") or 24.0)
    total_sla_seconds = max(1.0, sla_hours * 3600.0)
    created_at = parse_iso_datetime(ticket.get("created_at")) or current_time
    paused_seconds = int(ticket.get("paused_seconds") or 0)

    if status == "Anulado":
        return {
            "semaphore": "Gris",
            "color_hex": "#64748B",
            "pct_consumed": 0.0,
            "remaining_hours": 0.0,
            "label": "Anulado",
            "is_breached": False,
            "is_alert_75": False,
        }

    end_ref = current_time
    if status in ("Resuelto", "Cerrado"):
        resolved_dt = parse_iso_datetime(ticket.get("resolved_at")) or parse_iso_datetime(
            ticket.get("closed_at")
        )
        if resolved_dt:
            end_ref = resolved_dt
    elif status == "En espera" and ticket.get("paused_at"):
        paused_dt = parse_iso_datetime(ticket.get("paused_at"))
        if paused_dt:
            end_ref = paused_dt

    elapsed_seconds = max(0.0, (end_ref - created_at).total_seconds() - paused_seconds)
    pct_consumed = round((elapsed_seconds / total_sla_seconds) * 100.0, 1)
    remaining_hours = round((total_sla_seconds - elapsed_seconds) / 3600.0, 2)

    if status in ("Resuelto", "Cerrado"):
        if pct_consumed <= 100.0:
            return {
                "semaphore": "Verde",
                "color_hex": "#16A34A",
                "pct_consumed": pct_consumed,
                "remaining_hours": max(0.0, remaining_hours),
                "label": f"Cumplido ({pct_consumed:.0f}%)",
                "is_breached": False,
                "is_alert_75": False,
            }
        return {
            "semaphore": "Rojo",
            "color_hex": "#DC2626",
            "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours,
            "label": f"Cerrado fuera de SLA ({pct_consumed:.0f}%)",
            "is_breached": True,
            "is_alert_75": True,
        }

    if status == "En espera":
        return {
            "semaphore": "Azul",
            "color_hex": "#2563EB",
            "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours,
            "label": f"Pausado en espera ({pct_consumed:.0f}%)",
            "is_breached": False,
            "is_alert_75": pct_consumed >= 75.0,
        }

    if pct_consumed > 100.0:
        return {
            "semaphore": "Rojo",
            "color_hex": "#DC2626",
            "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours,
            "label": f"Vencido ({abs(remaining_hours):.1f}h de retraso)",
            "is_breached": True,
            "is_alert_75": True,
        }

    if pct_consumed >= 75.0:
        return {
            "semaphore": "Amarillo",
            "color_hex": "#D97706",
            "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours,
            "label": f"En riesgo ({remaining_hours:.1f}h restantes)",
            "is_breached": False,
            "is_alert_75": True,
        }

    return {
        "semaphore": "Verde",
        "color_hex": "#16A34A",
        "pct_consumed": pct_consumed,
        "remaining_hours": remaining_hours,
        "label": f"A tiempo ({remaining_hours:.1f}h restantes)",
        "is_breached": False,
        "is_alert_75": False,
    }


def validate_attachment(filename: str, size_bytes: int) -> None:
    """Valida extensión permitida y límite de 10 MB para adjuntos (RF-04 / RF-13)."""
    if not filename or "." not in filename:
        raise ValueError("El archivo adjunto debe tener una extensión válida.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS)).upper()
        raise ValueError(f"Formato no permitido '.{ext}'. Formatos válidos: {allowed}.")
    if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValueError(f"El archivo '{filename}' supera el límite máximo permitido de 10 MB.")
