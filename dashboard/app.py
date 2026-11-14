"""
Orquestador principal CASAGBI (Mesa de Servicios TIC · UPC Valledupar).

Implementa:
- Contenedor de Inyección de Dependencias (DIP, cero SQL/repositorios en UI)
- Estado público sin sidebar técnico para Landing/Auth vs Workspace privado RBAC
- Lazy loading por ruta mediante importlib.import_module
- Validación JWT + rotación Refresh Token
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict

import streamlit as st

# Asegurar raíz del proyecto en sys.path al ejecutar `streamlit run dashboard/app.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.shared.components import render_top_bar
from dashboard.shared.icons import svg_icon
from dashboard.shared.route_guard import (
    enforce_route_guard,
    get_accessible_routes,
    get_route_label,
)
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_auth_service,
    get_ticket_service,
)
from dashboard.shared.styles import (
    UPC_EMERALD,
    UPC_GREEN,
    UPC_SLATE_DARK,
    hide_sidebar_for_public_landing,
    inject_upc_styles,
)
from src.application.auth_use_cases import AuthService
from src.domain.rules import ROLE_LABELS

# Registro Lazy Loading: solo se importa el módulo de la vista activa
LAZY_ROUTE_MODULES: Dict[str, str] = {
    "landing": "dashboard.features.landing.landing_view",
    "auth": "dashboard.features.auth.auth_view",
    "create_ticket": "dashboard.features.tickets.create_ticket_view",
    "track_ticket": "dashboard.features.tickets.track_ticket_view",
    "ai_assistant": "dashboard.features.ai_assistant.assistant_chat_view",
    "manage_tickets": "dashboard.features.tickets.manage_tickets_view",
    "kpi_dashboard": "dashboard.features.admin_analytics.kpi_dashboard_view",
    "ml_laboratory": "dashboard.features.admin_analytics.ml_laboratory_view",
}


def _render_private_sidebar(auth_svc: AuthService) -> None:
    """Renderiza el menú lateral estricto por rol solo cuando existe sesión autenticada."""
    auth = StoreManager.auth()
    nav = StoreManager.nav()
    user = auth.user
    assert user is not None

    with st.sidebar:
        logo_svg = svg_icon("building", size=22, color=UPC_GREEN)
        st.markdown(
            f"""<div style="padding:0.4rem 0 0.9rem 0;border-bottom:2px solid {UPC_GREEN};margin-bottom:0.9rem;">
<div style="display:flex;align-items:center;gap:0.5rem;font-size:1.28rem;font-weight:800;color:{UPC_GREEN};">
{logo_svg}<span>CASAGBI</span>
</div>
<div style="font-size:0.8rem;color:#475569;font-weight:500;margin-top:0.15rem;">Mesa de Servicios TIC · ITIL v4</div>
</div>""",
            unsafe_allow_html=True,
        )

        role = user["role"]
        routes = get_accessible_routes(role)

        for r in routes:
            is_active = nav.current_route == r
            if st.button(
                get_route_label(r, role),
                key=f"side_nav_{r}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                LifecycleManager.on_route_change(r)
                st.rerun()

        st.divider()
        role_desc = ROLE_LABELS.get(role, role)
        st.markdown(
            f"""<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:0.75rem 0.85rem;margin-bottom:0.7rem;">
<div style="font-size:0.86rem;font-weight:700;color:{UPC_SLATE_DARK};display:flex;align-items:center;gap:0.4rem;">
{svg_icon('user', size=15, color=UPC_GREEN)}<span>{user['full_name']}</span>
</div>
<div style="font-size:0.78rem;color:#475569;margin-top:0.25rem;">Rol: <strong style="color:{UPC_EMERALD};">{role_desc}</strong></div>
<div style="font-size:0.76rem;color:#64748B;">{user.get('sede', 'Valledupar')}</div>
</div>""",
            unsafe_allow_html=True,
        )
        if st.button("Estado de Sesión JWT", use_container_width=True, key="side_auth_status"):
            LifecycleManager.on_route_change("auth")
            st.rerun()
        if st.button("Cerrar Sesión", use_container_width=True, key="side_logout"):
            auth_svc.logout(user["email"], auth.refresh_token)
            StoreManager.clear_auth_session(notice="Sesión cerrada de forma segura y token revocado.")
            LifecycleManager.on_route_change("landing")
            st.rerun()


def _render_floating_assistant_shortcut() -> None:
    """Acceso rápido al Agente IA visible en pantallas del Workspace Privado."""
    auth = StoreManager.auth()
    nav = StoreManager.nav()
    if auth.is_authenticated and nav.current_route not in ("ai_assistant", "landing"):
        st.divider()
        col_sp, col_btn = st.columns([3.4, 1.6])
        with col_btn:
            if st.button("Consultar con CASAGBI Agent (IA)", use_container_width=True, key="floating_ai_btn"):
                LifecycleManager.on_route_change("ai_assistant")
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="CASAGBI · Mesa de Servicios TIC UPC",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_upc_styles()

    # 1. Ciclo de Vida: Bootstrap inicial único (Dataset 18k + Modelos + SQLite)
    LifecycleManager.on_app_bootstrap()

    auth_svc = get_auth_service()
    ticket_svc = get_ticket_service()

    # 2. Ciclo de Vida: Validación JWT / Refresh Token / Timeout 30m al iniciar request
    LifecycleManager.on_request_start(auth_svc)

    auth = StoreManager.auth()

    if auth.is_authenticated and auth.user:
        notifications = ticket_svc.list_user_notifications(auth.user["email"])
        StoreManager.notifications().items = notifications
        StoreManager.notifications().unread_count = sum(1 for n in notifications if not n.get("is_read"))
        _render_private_sidebar(auth_svc)
        render_top_bar(notifications, on_mark_read=ticket_svc.mark_notifications_read)
    else:
        StoreManager.notifications().items = []
        StoreManager.notifications().unread_count = 0
        hide_sidebar_for_public_landing()

    # 3. Enrutador protegido + Lazy Loading del módulo activo
    current_route = StoreManager.nav().current_route
    if current_route not in LAZY_ROUTE_MODULES:
        current_route = "landing"
        StoreManager.nav().current_route = "landing"

    if enforce_route_guard(current_route, auth_svc):
        module_path = LAZY_ROUTE_MODULES[current_route]
        view_module = importlib.import_module(module_path)
        view_module.render()
        _render_floating_assistant_shortcut()


if __name__ == "__main__":
    main()
