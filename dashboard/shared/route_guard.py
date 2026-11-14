"""Middleware de seguridad de rutas: validación JWT, rotación Refresh Token y RBAC."""

from __future__ import annotations

from typing import Dict, List, Set

import streamlit as st

from dashboard.shared.store import LifecycleManager, StoreManager
from src.application.auth_use_cases import AuthService

# Matriz declarativa de acceso por ruta (Screaming Architecture + RBAC)
ROUTE_ALLOWED_ROLES: Dict[str, Set[str]] = {
    "landing": {"public", "usuario", "tecnico", "coordinador", "director", "admin"},
    "auth": {"public", "usuario", "tecnico", "coordinador", "director", "admin"},
    "create_ticket": {"usuario", "tecnico", "coordinador", "admin"},
    "track_ticket": {"public", "usuario", "tecnico", "coordinador", "director", "admin"},
    "ai_assistant": {"usuario", "tecnico", "coordinador", "director", "admin"},
    "manage_tickets": {"tecnico", "coordinador", "admin"},
    "kpi_dashboard": {"tecnico", "coordinador", "director", "admin"},
    "ml_laboratory": {"coordinador", "director", "admin"},
}

ROUTE_LABELS: Dict[str, str] = {
    "landing": "Inicio / Portal",
    "auth": "Acceso Institucional",
    "create_ticket": "Crear Ticket",
    "track_ticket": "Mis Tickets / Consulta",
    "ai_assistant": "Agente IA Soporte",
    "manage_tickets": "Bandeja y Operación",
    "kpi_dashboard": "Dashboard Ejecutivo KPI",
    "ml_laboratory": "Laboratorio MLOps (IA)",
}

_ROLE_ROUTE_LABELS: Dict[str, Dict[str, str]] = {
    "usuario": {
        "landing": "Inicio / Portal",
        "create_ticket": "Crear Ticket",
        "track_ticket": "Mis Tickets",
        "ai_assistant": "Agente IA Soporte",
    },
    "tecnico": {
        "manage_tickets": "Mi Bandeja Asignada y KB",
        "track_ticket": "Gestión y Resolución",
        "kpi_dashboard": "Mis Métricas",
        "ai_assistant": "Agente IA Soporte",
    },
    "coordinador": {
        "kpi_dashboard": "Dashboard Ejecutivo KPI",
        "manage_tickets": "Gestión Global y Reasignación",
        "ml_laboratory": "Laboratorio MLOps (IA)",
        "track_ticket": "Seguimiento Detallado",
        "create_ticket": "Registrar Ticket",
        "ai_assistant": "Agente IA Soporte",
        "landing": "Portal Público",
    },
    "director": {
        "kpi_dashboard": "Dashboard Ejecutivo KPI",
        "ml_laboratory": "Laboratorio MLOps (IA)",
        "track_ticket": "Consulta Global de Casos",
        "ai_assistant": "Agente IA Soporte",
        "landing": "Portal Público",
    },
    "admin": {
        "kpi_dashboard": "Dashboard Ejecutivo KPI",
        "manage_tickets": "Gestión Global, KB y Auditoría",
        "ml_laboratory": "Laboratorio MLOps (IA)",
        "track_ticket": "Seguimiento y Chat",
        "create_ticket": "Registrar Ticket",
        "ai_assistant": "Agente IA Soporte",
        "landing": "Portal Público",
    },
}


def get_route_label(route: str, role: str | None = None) -> str:
    """Retorna la etiqueta de menú adaptada al rol autenticado (sin emojis)."""
    if role and role in _ROLE_ROUTE_LABELS and route in _ROLE_ROUTE_LABELS[role]:
        return _ROLE_ROUTE_LABELS[role][route]
    return ROUTE_LABELS.get(route, route)


def get_accessible_routes(role: str | None) -> List[str]:
    """Retorna la lista ordenada de rutas visibles en menú lateral según rol (RBAC estricto)."""
    effective_role = role or "public"
    if effective_role == "public":
        return ["landing", "track_ticket", "auth"]
    if effective_role == "usuario":
        return ["landing", "create_ticket", "track_ticket", "ai_assistant"]
    if effective_role == "tecnico":
        return ["manage_tickets", "track_ticket", "kpi_dashboard", "ai_assistant"]
    if effective_role == "director":
        return ["kpi_dashboard", "ml_laboratory", "track_ticket", "ai_assistant", "landing"]
    # coordinador / admin
    ordered = [
        "kpi_dashboard",
        "manage_tickets",
        "ml_laboratory",
        "track_ticket",
        "create_ticket",
        "ai_assistant",
        "landing",
    ]
    return [r for r in ordered if effective_role in ROUTE_ALLOWED_ROLES[r]]


def enforce_route_guard(route: str, auth_service: AuthService) -> bool:
    """
    Interceptor ejecutado antes de cargar perezosamente una vista:
    - Valida JWT y rota silenciosamente Refresh Token si expiró.
    - Comprueba autorización RBAC por rol.
    - Registra intentos no autorizados en la bitácora de auditoría (HU-03 / RF-03).
    """
    LifecycleManager.on_request_start(auth_service)
    auth = StoreManager.auth()
    allowed_roles = ROUTE_ALLOWED_ROLES.get(route, set())

    if "public" in allowed_roles:
        return True

    if not auth.is_authenticated or not auth.user:
        st.warning("Debe iniciar sesión con su cuenta institucional `@unicesar.edu.co` para acceder a esta sección.")
        if st.button("Ir al Inicio de Sesión", type="primary", key=f"guard_login_{route}"):
            LifecycleManager.on_route_change("auth")
            st.rerun()
        return False

    user_role = auth.user.get("role", "usuario")
    if user_role not in allowed_roles:
        auth_service.log_unauthorized_attempt(
            user_email=auth.user.get("email", "desconocido"),
            route=route,
            role=user_role,
        )
        st.error(
            f"**Acceso no autorizado (RBAC):** Su rol `{user_role}` no tiene permisos para acceder a "
            f"`{get_route_label(route, user_role)}`. Este intento ha quedado registrado en la bitácora de auditoría."
        )
        return False

    return True
