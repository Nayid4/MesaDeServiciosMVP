"""Catálogo oficial UPC, nomenclatura por categoría y reglas de asignación por carga."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

SERVICE_CATEGORY_PREFIXES: Dict[str, str] = {
    "Conectividad y Redes Wi-Fi": "RED",
    "Plataformas Académicas (Aula Web / Vortal)": "SIS",
    "Correo Institucional y Cuentas": "ACC",
    "Aulas Inteligentes y Videoproyectores": "AUL",
    "Equipos de Cómputo e Impresoras": "SOP",
    "Software y Licenciamiento": "SWL",
}
VALID_CATEGORY_PREFIXES = ("RED", "SIS", "ACC", "AUL", "SOP", "SWL", "GEN")

CATEGORY_TICKET_NUMBER_PATTERN = re.compile(
    r"^MS-(RED|SIS|ACC|AUL|SOP|SWL|GEN)-(\d{4})-(\d{6})$"
)
LEGACY_TICKET_NUMBER_PATTERN = re.compile(r"^MS-(\d{4})-(\d{6})$")
TICKET_NUMBER_PATTERN = re.compile(
    r"^MS-(?:(?:RED|SIS|ACC|AUL|SOP|SWL|GEN)-)?\d{4}-\d{6}$"
)

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


def get_service_prefix(service_name: str) -> str:
    """Retorna el prefijo de categoría de 3 letras del catálogo UPC ('GEN' si es personalizado)."""
    return SERVICE_CATEGORY_PREFIXES.get((service_name or "").strip(), "GEN")


def get_service_metadata(service_name: str) -> Dict[str, str]:
    """Retorna área responsable e impacto base de un servicio del catálogo UPC."""
    if service_name not in UPC_SERVICE_CATALOG:
        raise ValueError(f"Servicio no registrado en catálogo UPC: '{service_name}'.")
    return UPC_SERVICE_CATALOG[service_name]


def normalize_subject_for_dedup(title: str) -> str:
    """Normaliza el asunto en minúsculas, sin tildes y sin espacios sobrantes."""
    nfkd = unicodedata.normalize("NFKD", str(title or ""))
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents).strip().lower()


def compute_content_dedup_hash(user_id: int, service_name: str, title: str) -> str:
    """Calcula hash SHA-256 exacto sobre (usuario, servicio, asunto normalizado)."""
    norm_title = normalize_subject_for_dedup(title)
    norm_service = (service_name or "").strip().lower()
    raw = f"{int(user_id)}|{norm_service}|{norm_title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def format_ticket_number(seq: int, year: int = 2026, prefix: Optional[str] = None) -> str:
    """Genera consecutivo MS-<CAT>-AAAA-NNNNNN (o MS-AAAA-NNNNNN si prefix es None)."""
    if seq < 1:
        raise ValueError("El consecutivo del ticket debe ser mayor o igual a 1.")
    if prefix is not None:
        clean_prefix = prefix.strip().upper()
        if clean_prefix not in VALID_CATEGORY_PREFIXES:
            raise ValueError(f"Prefijo de categoría inválido: '{prefix}'.")
        return f"MS-{clean_prefix}-{int(year):04d}-{int(seq):06d}"
    return f"MS-{int(year):04d}-{int(seq):06d}"


def select_technician_least_load(technicians: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Selecciona el técnico activo con menor carga de tickets abiertos (RF-06)."""
    active = [t for t in technicians if bool(t.get("is_active", True))]
    if not active:
        return None

    def _sort_key(tech: Dict[str, Any]) -> Tuple[int, str, int]:
        load = int(tech.get("open_tickets_count", 0))
        last_assigned = tech.get("last_assigned_at") or "0000-01-01T00:00:00"
        return (load, str(last_assigned), int(tech.get("id", 0)))

    return min(active, key=_sort_key)
