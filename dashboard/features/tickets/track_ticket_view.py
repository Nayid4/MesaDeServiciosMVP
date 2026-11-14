"""Vista de consulta de tickets, línea de tiempo cronológica, chat bidireccional y CSAT."""

from __future__ import annotations

import streamlit as st

from dashboard.features.tickets.ticket_detail_panel import render_ticket_detail_two_columns
from dashboard.shared.components import (
    render_breadcrumbs,
    render_priority_badge,
    render_section_header,
    render_sla_badge,
    render_status_badge,
)
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_auth_service,
    get_ticket_service,
)
from dashboard.shared.styles import UPC_SLATE_DARK
from src.domain.rules import ALL_TICKET_STATUSES, UPC_SEDES


def render() -> None:
    auth = StoreManager.auth()
    nav = StoreManager.nav()
    t_store = StoreManager.tickets()
    ticket_svc = get_ticket_service()
    auth_svc = get_auth_service()

    render_breadcrumbs(["CASAGBI", "Consulta y Seguimiento de Tickets"])
    render_section_header(
        "Consultar Estado e Historial de Tickets",
        "Seguimiento en tiempo real del ciclo de vida ITIL v4, semáforo SLA y conversación técnica.",
        icon_name="search",
    )

    if not auth.is_authenticated or not auth.user:
        c_back, _ = st.columns([1.4, 4.6])
        with c_back:
            if st.button("Volver al Portal Público", use_container_width=True, key="tk_pub_back"):
                LifecycleManager.on_route_change("landing")
                st.rerun()

        st.info("Consulte el estado resumido y la línea de tiempo pública de un radicado, o inicie sesión para ver sus tickets y chat.")
        rad = st.text_input("Número de radicado", value=nav.selected_ticket_number or "", placeholder="MS-2026-000001")
        if st.button("Buscar radicado", type="primary", key="tk_pub_search") and rad.strip():
            pub = ticket_svc.get_public_ticket_tracking(rad.strip().upper())
            if not pub:
                st.warning("No se encontró el radicado consultado.")
            else:
                st.markdown(
                    f"""<div class="upc-card-accent">
<div style="font-size:1.08rem;font-weight:800;color:{UPC_SLATE_DARK};margin-bottom:0.45rem;">{pub['ticket_number']} — {pub['title']}</div>
<div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.65rem;">
{render_status_badge(pub['status'])}
{render_priority_badge(pub['priority'])}
{render_sla_badge(pub['sla_source_ticket'])}
</div>
<div style="font-size:0.88rem;color:#475569;">
Área: <strong>{pub['area']}</strong> · Sede: <strong>{pub['sede']}</strong> · Ubicación: <strong>{pub['location']}</strong>
</div>
</div>""",
                    unsafe_allow_html=True,
                )
                if pub["timeline"]:
                    st.markdown("**Línea de tiempo pública (sin datos personales sensibles):**")
                    for ev in pub["timeline"]:
                        ts = str(ev.get("created_at") or "")[:16].replace("T", " ")
                        st.markdown(
                            f"""<div class="upc-timeline-item">
<div style="font-size:0.85rem;font-weight:700;color:{UPC_SLATE_DARK};">{ev['action']} ({ts})</div>
<div style="font-size:0.82rem;color:#006837;">{ev['actor_label']} · {ev.get('old_status') or 'Inicio'} &rarr; {ev.get('new_status') or ''}</div>
</div>""",
                            unsafe_allow_html=True,
                        )
        return

    user = auth.user

    with st.expander("Filtros de búsqueda", expanded=True):
        f1, f2, f3, f4 = st.columns([2, 1.3, 1.3, 1.5])
        with f1:
            t_store.search_query = st.text_input(
                "Buscar por número o palabra clave",
                value=t_store.search_query,
                placeholder="MS-2026-... o asunto",
                key="tk_search_input",
            )
        with f2:
            status_opts = ["Todos"] + list(ALL_TICKET_STATUSES)
            t_store.status_filter = st.selectbox("Estado", status_opts, key="tk_status_filter")
        with f3:
            prio_opts = ["Todas", "P1 Crítica", "P2 Alta", "P3 Media", "P4 Baja"]
            t_store.priority_filter = st.selectbox("Prioridad", prio_opts, key="tk_prio_filter")
        with f4:
            sede_opts = ["Todas"] + UPC_SEDES
            t_store.sede_filter = st.selectbox("Sede", sede_opts, key="tk_sede_filter")

    tickets = ticket_svc.list_visible_tickets(
        user=user,
        status=None if t_store.status_filter == "Todos" else t_store.status_filter,
        priority=None if t_store.priority_filter == "Todas" else t_store.priority_filter,
        sede=None if t_store.sede_filter == "Todas" else t_store.sede_filter,
        search=t_store.search_query or None,
    )

    if not tickets:
        st.info("Aún no hay tickets que coincidan con los criterios seleccionados.")
        if user["role"] in ("usuario", "tecnico", "coordinador", "admin"):
            if st.button("Crear Nuevo Ticket", type="primary", key="tk_empty_create"):
                LifecycleManager.on_route_change("create_ticket")
                st.rerun()
        return

    total_items = len(tickets)
    total_pages = max(1, (total_items + t_store.page_size - 1) // t_store.page_size)
    t_store.page = min(max(1, t_store.page), total_pages)
    start_idx = (t_store.page - 1) * t_store.page_size
    page_items = tickets[start_idx : start_idx + t_store.page_size]

    p_col1, _, p_col3 = st.columns([2, 3, 2])
    with p_col1:
        st.caption(f"Mostrando {start_idx + 1}–{min(start_idx + t_store.page_size, total_items)} de {total_items} tickets")
    with p_col3:
        if total_pages > 1:
            t_store.page = st.number_input("Página", min_value=1, max_value=total_pages, value=t_store.page, key="tk_page_num")

    ticket_numbers = [t["ticket_number"] for t in page_items]
    default_sel = (
        nav.selected_ticket_number
        if nav.selected_ticket_number in ticket_numbers
        else ticket_numbers[0]
    )

    for t in page_items:
        cols = st.columns([1.4, 3.0, 1.3, 1.3, 1.8, 1.0])
        cols[0].markdown(f"**{t['ticket_number']}**")
        cols[1].markdown(
            f"{t['title']}<br><span style='font-size:0.8rem;color:#64748B;'>{t['service_name']} · {t['sede']}</span>",
            unsafe_allow_html=True,
        )
        cols[2].markdown(render_status_badge(t["status"]), unsafe_allow_html=True)
        cols[3].markdown(render_priority_badge(t["priority"]), unsafe_allow_html=True)
        cols[4].markdown(render_sla_badge(t), unsafe_allow_html=True)
        if cols[5].button("Abrir", key=f"open_tk_{t['ticket_number']}", use_container_width=True):
            nav.selected_ticket_number = t["ticket_number"]
            st.rerun()

    st.divider()
    selected_num = nav.selected_ticket_number or default_sel
    render_ticket_detail_two_columns(
        ticket_number=selected_num,
        user=user,
        ticket_svc=ticket_svc,
        auth_svc=auth_svc,
        key_prefix="tk",
    )
