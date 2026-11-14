"""Landing page pública institucional UPC + consulta rápida con timeline y preview Agente IA."""

from __future__ import annotations

import streamlit as st

from dashboard.shared.components import (
    render_priority_badge,
    render_sla_badge,
    render_status_badge,
)
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_lazy_ai_service,
    get_ticket_service,
)
from dashboard.shared.styles import UPC_EMERALD, UPC_GREEN, UPC_SLATE_DARK
from src.domain.rules import SLA_BY_PRIORITY, UPC_SERVICE_CATALOG

SERVICE_ICONS = {
    "Conectividad y Redes Wi-Fi": "wifi",
    "Plataformas Académicas (Aula Web / Vortal)": "layers",
    "Correo Institucional y Cuentas": "mail",
    "Aulas Inteligentes y Videoproyectores": "monitor",
    "Equipos de Cómputo e Impresoras": "settings",
    "Software y Licenciamiento": "book-open",
}


def render() -> None:
    auth = StoreManager.auth()
    ticket_svc = get_ticket_service()
    ai_svc = get_lazy_ai_service()

    # 1. Barra de navegación superior institucional
    logo_svg = svg_icon("building", size=24, color=UPC_GREEN)
    st.markdown(
        f"""<div class="upc-public-nav">
<div style="display:flex;align-items:center;gap:0.6rem;">
{logo_svg}
<div>
<div style="font-size:1.18rem;font-weight:800;color:{UPC_GREEN};line-height:1.1;">CASAGBI</div>
<div style="font-size:0.75rem;color:#64748B;font-weight:600;">Universidad Popular del Cesar · Mesa TIC ITIL v4</div>
</div>
</div>
<div class="upc-nav-links">
<a href="#servicios-tic">Servicios TIC</a>
<a href="#como-funciona">¿Cómo funciona?</a>
<a href="#consulta-radicado">Consultar Ticket</a>
<a href="#agente-ia-rapido">Asistente IA</a>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    nav_sp, nav_btn1, nav_btn2 = st.columns([2.6, 1.4, 1.8])
    with nav_btn1:
        if st.button("Consultar Radicado", use_container_width=True, key="nav_consult_btn"):
            LifecycleManager.on_route_change("track_ticket")
            st.rerun()
    with nav_btn2:
        if auth.is_authenticated and auth.user:
            role = auth.user["role"]
            ws_route = "create_ticket" if role == "usuario" else ("manage_tickets" if role == "tecnico" else "kpi_dashboard")
            if st.button("Ir a mi Workspace", type="primary", use_container_width=True, key="nav_ws_btn"):
                LifecycleManager.on_route_change(ws_route)
                st.rerun()
        else:
            if st.button("Ingresar con Cuenta Institucional", type="primary", use_container_width=True, key="nav_login_btn"):
                LifecycleManager.on_route_change("auth")
                st.rerun()

    # 2. Hero Section en grid asimétrico (2 columnas) + Métricas en vivo desde SQLite
    impact = ticket_svc.get_public_impact_metrics()
    hero_left, hero_right = st.columns([1.45, 1.0])

    with hero_left:
        shield_svg = svg_icon("shield-check", size=14, color="#A7F3D0")
        st.markdown(
            f"""<div class="casagbi-hero">
<div class="upc-hero-tag">{shield_svg}<span>SPOC Institucional · ITIL v4 + IA Propia</span></div>
<h1>Soporte Técnico Trazable para toda la Comunidad UPC</h1>
<p>
Centraliza incidentes y requerimientos de <strong>Sede Sabanas</strong>, <strong>Sede Hurtado</strong> y
<strong>Seccional Aguachica</strong> en un Punto Único de Contacto con priorización automática OR-03,
balanceo equitativo entre técnicos y asistente IA Nivel Cero con revisión humana.
</p>
</div>""",
            unsafe_allow_html=True,
        )
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if auth.is_authenticated:
                if st.button("Registrar Nuevo Ticket TIC", type="primary", use_container_width=True, key="hero_create"):
                    LifecycleManager.on_route_change("create_ticket")
                    st.rerun()
            else:
                if st.button("Iniciar Sesión @unicesar.edu.co", type="primary", use_container_width=True, key="hero_login"):
                    LifecycleManager.on_route_change("auth")
                    st.rerun()
        with c_act2:
            if auth.is_authenticated:
                if st.button("Abrir CASAGBI Agent (IA)", use_container_width=True, key="hero_ai"):
                    LifecycleManager.on_route_change("ai_assistant")
                    st.rerun()
            else:
                if st.button("Ver Seguimiento Público", use_container_width=True, key="hero_track"):
                    LifecycleManager.on_route_change("track_ticket")
                    st.rerun()

    with hero_right:
        ic_check = svg_icon("check-circle", size=18, color=UPC_GREEN)
        ic_clock = svg_icon("clock", size=18, color=UPC_EMERALD)
        ic_award = svg_icon("award", size=18, color=UPC_GREEN)
        ic_layers = svg_icon("layers", size=18, color=UPC_EMERALD)
        st.markdown(
            f"""<div class="upc-card-accent" style="height:100%;">
<div style="font-size:0.82rem;font-weight:700;color:{UPC_GREEN};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.85rem;">
Métricas Operativas en Vivo (SQLite)
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.85rem;">
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:0.85rem;">
<div style="font-size:0.76rem;color:#64748B;font-weight:700;">{ic_check} RESUELTOS</div>
<div style="font-size:1.6rem;font-weight:800;color:{UPC_SLATE_DARK};">{impact['resolved_tickets']}</div>
<div style="font-size:0.74rem;color:#475569;">de {impact['total_tickets']} radicados</div>
</div>
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:0.85rem;">
<div style="font-size:0.76rem;color:#64748B;font-weight:700;">{ic_clock} ATENCIÓN PROM.</div>
<div style="font-size:1.6rem;font-weight:800;color:{UPC_SLATE_DARK};">{impact['avg_resolution_hours']} h</div>
<div style="font-size:0.74rem;color:#475569;">Tiempo medio resolución</div>
</div>
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:0.85rem;">
<div style="font-size:0.76rem;color:#64748B;font-weight:700;">{ic_award} CUMPLIMIENTO SLA</div>
<div style="font-size:1.6rem;font-weight:800;color:{UPC_GREEN};">{impact['sla_compliance_pct']}%</div>
<div style="font-size:0.74rem;color:#475569;">Acuerdos OR-04 activos</div>
</div>
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:0.85rem;">
<div style="font-size:0.76rem;color:#64748B;font-weight:700;">{ic_layers} DISPONIBILIDAD</div>
<div style="font-size:1.6rem;font-weight:800;color:{UPC_EMERALD};">{impact['availability_pct']}%</div>
<div style="font-size:0.74rem;color:#475569;">{impact['active_services_count']} servicios TIC</div>
</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

    # 3. Cómo funciona (Pilares ITIL + XP + IA)
    st.markdown("<div id='como-funciona'></div>", unsafe_allow_html=True)
    st.subheader("¿Cómo funciona el soporte inteligente CASAGBI?")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            f"""<div class="upc-card">
<h4 style="margin-top:0;display:flex;align-items:center;gap:0.45rem;color:{UPC_SLATE_DARK};">
{svg_icon('file-text', size=19, color=UPC_GREEN)}<span>1. Trazabilidad y Memoria Técnica</span>
</h4>
<p style="font-size:0.93rem;color:#475569;margin-bottom:0;">
Cada caso recibe un consecutivo oficial <code>MS-2026-NNNNNN</code> con bitácora inmutable,
chat bidireccional y documentación obligatoria de solución.
</p>
</div>""",
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            f"""<div class="upc-card">
<h4 style="margin-top:0;display:flex;align-items:center;gap:0.45rem;color:{UPC_SLATE_DARK};">
{svg_icon('clock', size=19, color=UPC_GREEN)}<span>2. Prioridad OR-03 y Menor Carga</span>
</h4>
<p style="font-size:0.93rem;color:#475569;margin-bottom:0;">
Calcula la prioridad (P1 a P4) cruzando Impacto por Urgencia y asigna al técnico activo
del área con menor número de tickets abiertos.
</p>
</div>""",
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            f"""<div class="upc-card">
<h4 style="margin-top:0;display:flex;align-items:center;gap:0.45rem;color:{UPC_SLATE_DARK};">
{svg_icon('bot', size=19, color=UPC_GREEN)}<span>3. IA Propia con Human-in-the-Loop</span>
</h4>
<p style="font-size:0.93rem;color:#475569;margin-bottom:0;">
Clasifica automáticamente la categoría con NLP evaluado con CV y resuelve preguntas frecuentes
desde la Base de Conocimiento con confirmación humana.
</p>
</div>""",
            unsafe_allow_html=True,
        )

    # 4. Catálogo Visual de Servicios TIC UPC (#servicios-tic)
    st.markdown("<div id='servicios-tic'></div>", unsafe_allow_html=True)
    st.subheader("Catálogo Institucional de Servicios TIC y Matriz SLA (OR-04)")
    svc_cols = st.columns(2)
    for idx, (svc_name, meta) in enumerate(UPC_SERVICE_CATALOG.items()):
        ico = svg_icon(SERVICE_ICONS.get(svc_name, "layers"), size=19, color=UPC_GREEN)
        with svc_cols[idx % 2]:
            st.markdown(
                f"""<div class="upc-card">
<div style="display:flex;align-items:center;gap:0.5rem;font-weight:700;font-size:1.02rem;color:{UPC_SLATE_DARK};">
{ico}<span>{svc_name}</span>
</div>
<div style="margin-top:0.35rem;display:flex;gap:0.4rem;flex-wrap:wrap;">
<span class="badge-pill badge-emerald">{meta['area']}</span>
<span class="badge-pill badge-slate">Impacto {meta['base_impact']}</span>
<span class="badge-pill badge-blue">{meta['default_type']}</span>
</div>
<p style="margin-top:0.55rem;margin-bottom:0;font-size:0.92rem;color:#475569;">{meta['description']}</p>
</div>""",
                unsafe_allow_html=True,
            )

    with st.expander("Ver Tiempos Objetivo SLA según Matriz 3x3 OR-03", expanded=False):
        sla_cols = st.columns(4)
        for col, (prio, times) in zip(sla_cols, SLA_BY_PRIORITY.items()):
            with col:
                st.markdown(
                    f"""<div class="upc-kpi-card">
<div class="upc-kpi-label">{svg_icon('clock', size=14, color=UPC_GREEN)}<span>{prio}</span></div>
<div style="font-size:0.98rem;font-weight:700;color:{UPC_SLATE_DARK};margin-top:0.35rem;">
Respuesta: {times['sla_response_hours']} h hábiles<br>
Resolución: {times['sla_resolution_hours']} h hábiles
</div>
</div>""",
                    unsafe_allow_html=True,
                )

    # 5. Widget de Consulta Pública Rápida (#consulta-radicado) + Mini Agente IA (#agente-ia-rapido)
    st.divider()
    col_lookup, col_ai_pub = st.columns([1.2, 1.0])

    with col_lookup:
        st.markdown("<div id='consulta-radicado'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.45rem;margin-bottom:0.2rem;'>"
            f"{svg_icon('search', size=20, color=UPC_GREEN)}<span>Consulta Pública Rápida de Ticket</span></h3>",
            unsafe_allow_html=True,
        )
        st.caption("Digite un radicado (ej. MS-2026-000001) para consultar su estado y línea de tiempo sin iniciar sesión.")
        q_in, q_bt = st.columns([3, 1.2])
        with q_in:
            quick_num = st.text_input(
                "Número de radicado",
                placeholder="MS-2026-000001",
                key="landing_quick_radicado",
                label_visibility="collapsed",
            )
        with q_bt:
            search_clicked = st.button("Consultar", type="primary", use_container_width=True, key="landing_quick_btn")

        if search_clicked:
            clean_num = quick_num.strip().upper()
            if not clean_num:
                st.warning("Ingrese un número de radicado con formato MS-AAAA-NNNNNN.")
            else:
                pub = ticket_svc.get_public_ticket_tracking(clean_num)
                if not pub:
                    st.warning(f"No se encontró ningún ticket con el radicado `{clean_num}`.")
                else:
                    st.markdown(
                        f"""<div class="upc-card-accent">
<div style="font-weight:800;font-size:1.05rem;color:{UPC_SLATE_DARK};margin-bottom:0.5rem;">
{pub['ticket_number']} — {pub['title']}
</div>
<div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.65rem;">
{render_status_badge(pub['status'])}
{render_priority_badge(pub['priority'])}
{render_sla_badge(pub['sla_source_ticket'])}
</div>
<div style="font-size:0.86rem;color:#475569;">
<strong>Servicio:</strong> {pub['service_name']} ({pub['area']}) ·
<strong>Sede:</strong> {pub['sede']} ({pub['location']})
</div>
</div>""",
                        unsafe_allow_html=True,
                    )
                    if pub["timeline"]:
                        st.markdown("**Línea de tiempo pública (datos personales protegidos):**")
                        for ev in pub["timeline"]:
                            ts = str(ev.get("created_at") or "")[:16].replace("T", " ")
                            cmt = f"<div style='font-size:0.83rem;color:#64748B;'>{ev['comment']}</div>" if ev.get("comment") else ""
                            st.markdown(
                                f"""<div class="upc-timeline-item">
<div style="font-size:0.85rem;font-weight:700;color:{UPC_SLATE_DARK};">{ev['action']} <span style="font-weight:500;color:#64748B;">({ts})</span></div>
<div style="font-size:0.82rem;color:#006837;">{ev['actor_label']} · {ev.get('old_status') or 'Inicio'} &rarr; {ev.get('new_status') or ''}</div>
{cmt}
</div>""",
                                unsafe_allow_html=True,
                            )

    with col_ai_pub:
        st.markdown("<div id='agente-ia-rapido'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.45rem;margin-bottom:0.2rem;'>"
            f"{svg_icon('bot', size=20, color=UPC_GREEN)}<span>Pregunta Rápida al Agente IA</span></h3>",
            unsafe_allow_html=True,
        )
        st.caption("Resuelve dudas frecuentes (Wi-Fi Eduroam, Vortal, horarios, sedes) antes de radicar un ticket.")
        pub_q = st.text_input(
            "Consulta rápida al agente",
            placeholder="Ej: Cómo conectarme a Wi-Fi Eduroam o qué horarios atienden?",
            key="landing_ai_faq_input",
            label_visibility="collapsed",
        )
        col_ask, col_full = st.columns(2)
        with col_ask:
            ask_clicked = st.button("Preguntar al Agente", use_container_width=True, key="landing_ai_faq_btn")
        with col_full:
            if st.button(
                "Abrir Chat Completo" if auth.is_authenticated else "Ingresar para Radicar",
                type="primary",
                use_container_width=True,
                key="landing_ai_open_btn",
            ):
                LifecycleManager.on_route_change("ai_assistant" if auth.is_authenticated else "auth")
                st.rerun()

        if ask_clicked and pub_q.strip():
            guest_user = {
                "id": -1,
                "email": "visitante@unicesar.edu.co",
                "full_name": "Visitante UPC",
                "role": "public",
                "sede": "Sede Sabanas (Valledupar)",
            }
            res = ai_svc.process_assistant_message(user=guest_user, message_text=pub_q.strip())
            st.markdown(
                f"""<div class="chat-bubble-tech">
<span class="upc-tool-chip">{svg_icon('sparkles', size=12, color=UPC_GREEN)}<span>{res.get('tool_invoked', 'agent')}</span></span>
</div>""",
                unsafe_allow_html=True,
            )
            st.markdown(res["reply"])
