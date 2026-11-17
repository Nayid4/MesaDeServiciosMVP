"""Reglas de horario hábil UPC (OR-04), cálculo de semáforo SLA y ventana de reapertura."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

BOGOTA_TZ = timezone(timedelta(hours=-5), name="America/Bogota")

COLOMBIA_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-12", "2026-03-23", "2026-04-02", "2026-04-03",
    "2026-05-01", "2026-05-18", "2026-06-08", "2026-06-15", "2026-06-29",
    "2026-07-20", "2026-08-07", "2026-08-17", "2026-10-12", "2026-11-02",
    "2026-11-16", "2026-12-08", "2026-12-25",
}


def now_bogota() -> datetime:
    """Retorna la fecha y hora actual en zona horaria America/Bogota (UTC-5)."""
    return datetime.now(BOGOTA_TZ)


def _is_business_day(dt: datetime, holidays: Optional[set] = None) -> bool:
    active_holidays = holidays if holidays is not None else COLOMBIA_HOLIDAYS_2026
    if dt.weekday() == 6:
        return False
    return dt.strftime("%Y-%m-%d") not in active_holidays


def _business_window_for_day(dt: datetime) -> Tuple[int, int]:
    return (8, 12) if dt.weekday() == 5 else (7, 19)


def add_business_hours(
    start_dt: datetime,
    hours_to_add: float,
    holidays: Optional[set] = None,
) -> datetime:
    """Suma horas hábiles siguiendo la regla OR-04 (L-V 7:00-19:00, Sáb 8:00-12:00)."""
    current = start_dt.replace(tzinfo=BOGOTA_TZ) if start_dt.tzinfo is None else start_dt.astimezone(BOGOTA_TZ)
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
    return dt.replace(tzinfo=BOGOTA_TZ) if dt.tzinfo is None else dt.astimezone(BOGOTA_TZ)


def calculate_sla_status(ticket: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Calcula el porcentaje consumido del SLA de resolución y el semáforo operativo."""
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
            "semaphore": "Gris", "color_hex": "#64748B", "pct_consumed": 0.0,
            "remaining_hours": 0.0, "label": "Anulado", "is_breached": False, "is_alert_75": False,
        }

    end_ref = current_time
    if status in ("Resuelto", "Cerrado"):
        resolved_dt = parse_iso_datetime(ticket.get("resolved_at")) or parse_iso_datetime(ticket.get("closed_at"))
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
                "semaphore": "Verde", "color_hex": "#16A34A", "pct_consumed": pct_consumed,
                "remaining_hours": max(0.0, remaining_hours), "label": f"Cumplido ({pct_consumed:.0f}%)",
                "is_breached": False, "is_alert_75": False,
            }
        return {
            "semaphore": "Rojo", "color_hex": "#DC2626", "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours, "label": f"Cerrado fuera de SLA ({pct_consumed:.0f}%)",
            "is_breached": True, "is_alert_75": True,
        }

    if status == "En espera":
        return {
            "semaphore": "Azul", "color_hex": "#2563EB", "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours, "label": f"Pausado en espera ({pct_consumed:.0f}%)",
            "is_breached": False, "is_alert_75": pct_consumed >= 75.0,
        }

    if pct_consumed > 100.0:
        return {
            "semaphore": "Rojo", "color_hex": "#DC2626", "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours, "label": f"Vencido ({abs(remaining_hours):.1f}h de retraso)",
            "is_breached": True, "is_alert_75": True,
        }

    if pct_consumed >= 75.0:
        return {
            "semaphore": "Amarillo", "color_hex": "#D97706", "pct_consumed": pct_consumed,
            "remaining_hours": remaining_hours, "label": f"En riesgo ({remaining_hours:.1f}h restantes)",
            "is_breached": False, "is_alert_75": True,
        }

    return {
        "semaphore": "Verde", "color_hex": "#16A34A", "pct_consumed": pct_consumed,
        "remaining_hours": remaining_hours, "label": f"A tiempo ({remaining_hours:.1f}h restantes)",
        "is_breached": False, "is_alert_75": False,
    }


def validate_reopen_window(
    resolved_at_iso: Optional[str],
    now: Optional[datetime] = None,
    max_business_days: int = 3,
) -> None:
    """Valida que la reapertura de un ticket Resuelto ocurra dentro de los 3 días hábiles (OR-04)."""
    if not resolved_at_iso:
        return
    resolved_dt = parse_iso_datetime(resolved_at_iso)
    if resolved_dt is None:
        return
    current_time = now or now_bogota()
    current_time = current_time.replace(tzinfo=BOGOTA_TZ) if current_time.tzinfo is None else current_time.astimezone(BOGOTA_TZ)
    deadline_dt = add_business_hours(resolved_dt, float(max_business_days * 12))
    if current_time > deadline_dt:
        raise ValueError(
            "El plazo máximo de 3 días hábiles desde la resolución para reabrir el ticket ha vencido."
        )
