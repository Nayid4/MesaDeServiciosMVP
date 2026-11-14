"""Componentes visuales reutilizables con SVG para CASAGBI (UPC) — Cero emojis."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from dashboard.shared.icons import svg_icon
from dashboard.shared.store import LifecycleManager, StoreManager
from dashboard.shared.styles import UPC_EMERALD, UPC_GREEN, UPC_SLATE_DARK
from src.domain.rules import ROLE_LABELS, calculate_sla_status


def render_breadcrumbs(items: List[str]) -> None:
    """Renderiza migas de pan para visibilidad del estado de navegación (Heurística Nielsen #1)."""
    if not items:
        return
    sep = svg_icon("chevron-right", size=14, color="#94A3B8")
    parts: List[str] = []
    for idx, label in enumerate(items):
        if idx == len(items) - 1:
            parts.append(f"<strong>{label}</strong>")
        else:
            parts.append(f"<span>{label}</span>")
    html = f"<div class='upc-breadcrumb'>{svg_icon('building', size=14, color=UPC_GREEN)} {f' {sep} '.join(parts)}</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = "", icon_name: str = "layers") -> None:
    """Renderiza un encabezado institucional con icono SVG y subtítulo accesible."""
    ico = svg_icon(icon_name, size=24, color=UPC_GREEN)
    sub = f"<p style='color:#475569;margin:0.2rem 0 0 0;font-size:0.95rem;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"<div style='margin-bottom:0.9rem;'>"
        f"<h2 style='margin:0;font-size:1.55rem;font-weight:800;color:{UPC_SLATE_DARK};display:flex;align-items:center;gap:0.55rem;'>"
        f"{ico}<span>{title}</span></h2>{sub}</div>",
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str,
    subtitle: str = "",
    delta: str = "",
    delta_positive: bool = True,
    icon_name: str = "chart-bar",
) -> None:
    """Renderiza una tarjeta KPI institucional con icono SVG, valor y delta opcional."""
    ico = svg_icon(icon_name, size=15, color=UPC_GREEN)
    sub_html = f"<div style='font-size:0.8rem;color:#64748B;margin-top:0.2rem;'>{subtitle}</div>" if subtitle else ""
    delta_cls = "upc-kpi-delta-pos" if delta_positive else "upc-kpi-delta-warn"
    delta_html = f"<div class='{delta_cls}'>{delta}</div>" if delta else ""
    st.markdown(
        f"""<div class="upc-kpi-card">
<div class="upc-kpi-label">{ico}<span>{label}</span></div>
<div class="upc-kpi-value">{value}</div>
{sub_html}
{delta_html}
</div>""",
        unsafe_allow_html=True,
    )


def render_sla_badge(ticket: Dict[str, Any]) -> str:
    """Retorna HTML accesible del semáforo SLA en tiempo real (Verde <75%, Ámbar 75%-99%, Rojo Vencido)."""
    sla = calculate_sla_status(ticket)
    sem = sla["semaphore"]
    cls_map = {
        "Verde": "badge-green",
        "Amarillo": "badge-yellow",
        "Rojo": "badge-red",
        "Azul": "badge-blue",
        "Gris": "badge-slate",
    }
    icon_map = {
        "Verde": svg_icon("check-circle", size=13, color="#166534"),
        "Amarillo": svg_icon("alert-triangle", size=13, color="#92400E"),
        "Rojo": svg_icon("x-circle", size=13, color="#991B1B"),
        "Azul": svg_icon("pause-circle", size=13, color="#1E40AF"),
        "Gris": svg_icon("dot", size=12, color="#475569"),
    }
    badge_cls = cls_map.get(sem, "badge-slate")
    ico = icon_map.get(sem, icon_map["Gris"])
    return f"<span class='badge-pill {badge_cls}'>{ico}<span>{sla['label']}</span></span>"


def render_status_badge(status: str) -> str:
    """Retorna badge HTML semántico para estado ITIL v4."""
    cls_map = {
        "Registrado": "badge-slate",
        "Asignado": "badge-blue",
        "En atención": "badge-yellow",
        "En espera": "badge-slate",
        "Resuelto": "badge-green",
        "Reabierto": "badge-red",
        "Cerrado": "badge-emerald",
        "Anulado": "badge-red",
    }
    return f"<span class='badge-pill {cls_map.get(status, 'badge-slate')}'>{status}</span>"


def render_priority_badge(priority: str) -> str:
    """Retorna badge HTML para prioridad OR-03."""
    if priority.startswith("P1"):
        cls = "badge-red"
    elif priority.startswith("P2"):
        cls = "badge-yellow"
    elif priority.startswith("P3"):
        cls = "badge-blue"
    else:
        cls = "badge-green"
    return f"<span class='badge-pill {cls}'>{priority}</span>"


def render_top_bar(
    notifications: List[Dict[str, Any]],
    on_mark_read: Optional[Callable[[str], None]] = None,
) -> None:
    """Barra superior del Workspace Privado autenticado con buscador, notificaciones y perfil."""
    auth = StoreManager.auth()
    col_brand, col_search, col_notif, col_user = st.columns([3.0, 2.7, 1.9, 2.4])

    with col_brand:
        ico = svg_icon("shield-check", size=22, color=UPC_GREEN)
        st.markdown(
            f"<div style='padding-top:0.35rem;display:flex;align-items:center;gap:0.45rem;'>"
            f"{ico}"
            f"<span style='font-size:1.18rem;font-weight:800;color:{UPC_GREEN};'>CASAGBI</span>"
            f"<span style='font-size:0.86rem;color:#64748B;font-weight:600;'>| Workspace ITIL v4 · UPC</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_search:
        q = st.text_input(
            "Buscador rápido de ticket",
            placeholder="Ir a radicado MS-2026-...",
            label_visibility="collapsed",
            key="topbar_ticket_search",
        )
        if q and q.strip().upper().startswith("MS-"):
            if st.button("Abrir radicado", key="topbar_go_ticket"):
                LifecycleManager.on_route_change("track_ticket", selected_ticket=q.strip().upper())
                st.rerun()

    with col_notif:
        if auth.is_authenticated and auth.user:
            unread = [n for n in notifications if not n.get("is_read")]
            with st.popover(f"Avisos ({len(unread)})", use_container_width=True):
                if not notifications:
                    st.caption("Sin notificaciones recientes.")
                else:
                    if unread and on_mark_read is not None:
                        if st.button("Marcar todas como leídas", key="topbar_mark_read", use_container_width=True):
                            on_mark_read(auth.user["email"])
                            st.rerun()
                    for n in notifications[:6]:
                        tag = "[NUEVO] " if not n.get("is_read") else ""
                        st.markdown(f"**{tag}{n['title']}**")
                        st.caption(n["message"])
                        st.divider()

    with col_user:
        if auth.is_authenticated and auth.user:
            role_label = ROLE_LABELS.get(auth.user["role"], auth.user["role"])
            ico_u = svg_icon("user", size=15, color=UPC_GREEN)
            st.markdown(
                f"<div style='text-align:right;font-size:0.84rem;line-height:1.3;'>"
                f"<strong>{ico_u} {auth.user['full_name']}</strong><br>"
                f"<span style='color:{UPC_EMERALD};font-weight:700;'>{role_label}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if auth.last_auth_notice:
        st.info(auth.last_auth_notice)
        auth.last_auth_notice = None
