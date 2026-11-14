"""Formulario de creación de ticket con validación en tiempo real (Nielsen) y predicción IA."""

from __future__ import annotations

import streamlit as st

from dashboard.shared.components import render_breadcrumbs, render_section_header
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_lazy_ai_service,
    get_ticket_service,
)
from dashboard.shared.styles import UPC_GREEN, UPC_SLATE_DARK
from src.application.ai_use_cases import AIServiceUnavailableError
from src.domain.rules import (
    UPC_LOCATIONS,
    UPC_SEDES,
    UPC_SERVICE_CATALOG,
    calculate_priority_or03,
)


def _validation_chip(label: str, valid: bool, detail: str) -> str:
    cls = "badge-green" if valid else "badge-yellow"
    ico = svg_icon("check-circle" if valid else "alert-triangle", size=12, color="#166534" if valid else "#92400E")
    return f"<span class='badge-pill {cls}'>{ico}<span>{label}: {detail}</span></span>"


def render() -> None:
    auth = StoreManager.auth()
    nav = StoreManager.nav()
    t_store = StoreManager.tickets()
    ai_store = StoreManager.ai()
    user = auth.user
    assert user is not None

    ticket_svc = get_ticket_service()
    ai_svc = get_lazy_ai_service()

    render_breadcrumbs(["Workspace", "Crear Ticket TIC"])
    render_section_header(
        "Registrar Nuevo Ticket TIC",
        "Complete los campos obligatorios. El motor IA sugiere la categoría y urgencia, conservando usted la decisión final (Human-in-the-Loop).",
        icon_name="ticket",
    )

    prefill = nav.prefill_ticket_data or {}
    services_list = [s["service_name"] for s in ticket_svc.get_active_services()]

    col_left, col_right = st.columns([2.2, 1.3])

    with col_left:
        title_val = st.text_input(
            "Asunto *",
            value=prefill.get("title", ""),
            placeholder="Ej: Sin conexión a red Wi-Fi Eduroam en Bloque B",
            key="ct_title_input",
        )
        title_len = len(title_val.strip())
        title_ok = title_len >= 5

        desc_val = st.text_area(
            "Descripción detallada del caso * (mínimo 15 caracteres)",
            value=prefill.get("description", ""),
            height=130,
            placeholder="Describa qué ocurre, desde cuándo y si afecta una clase o trámite...",
            key="ct_desc_input",
        )
        desc_len = len(desc_val.strip())
        desc_ok = desc_len >= 15

        # Validación preventiva en tiempo real (Heurística Nielsen #5)
        st.markdown(
            "<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem;'>"
            + _validation_chip("Asunto", title_ok, f"{title_len}/5 mín.")
            + _validation_chip("Descripción", desc_ok, f"{desc_len}/15 mín.")
            + "</div>",
            unsafe_allow_html=True,
        )

        # Análisis IA bajo demanda
        col_ai_btn, col_sim = st.columns([2, 1.5])
        with col_ai_btn:
            analyze_clicked = st.button(
                "Analizar texto y sugerir categoría con IA",
                use_container_width=True,
                key="ct_analyze_ai_btn",
            )
        with col_sim:
            sim_fail = st.checkbox(
                "Simular caída IA (RNF-06)",
                value=ai_store.simulate_ai_failure,
                key="ct_sim_ai_fail",
            )
            ai_store.simulate_ai_failure = sim_fail

        if analyze_clicked:
            if len((title_val + desc_val).strip()) < 5:
                st.warning("Escriba al menos un asunto o descripción breve para que la IA pueda analizar el caso.")
            else:
                try:
                    pred = ai_svc.classify_ticket_text(
                        title_val,
                        desc_val,
                        simulate_failure=ai_store.simulate_ai_failure,
                    )
                    t_store.ai_draft_prediction = pred
                except AIServiceUnavailableError as err:
                    t_store.ai_draft_prediction = None
                    st.warning(str(err))
                except Exception as exc:
                    t_store.ai_draft_prediction = None
                    st.warning(f"No fue posible obtener sugerencia automática: {exc}")

        draft_pred = t_store.ai_draft_prediction
        default_svc = (
            draft_pred["predicted_service"]
            if draft_pred and draft_pred["predicted_service"] in services_list
            else prefill.get("service_name", services_list[0])
        )
        if default_svc not in services_list:
            default_svc = services_list[0]

        urgency_options = ["Alta", "Media", "Baja"]
        default_urg = (
            draft_pred["predicted_urgency"]
            if draft_pred and draft_pred.get("predicted_urgency") in urgency_options
            else prefill.get("urgency", "Media")
        )
        if default_urg not in urgency_options:
            default_urg = "Media"

        if draft_pred:
            st.success(
                f"**Sugerencia del modelo `{draft_pred['model_name']}`:** "
                f"Servicio **{draft_pred['predicted_service']}** "
                f"(Confianza: **{draft_pred['confidence_pct']}%**) · "
                f"Urgencia estimada: **{draft_pred['predicted_urgency']}**. "
                "Confirme o ajuste los selectores antes de radicar."
            )

        default_sede = prefill.get("sede") or user.get("sede")
        sede_idx = UPC_SEDES.index(default_sede) if default_sede in UPC_SEDES else 0
        default_loc = prefill.get("location")
        loc_idx = UPC_LOCATIONS.index(default_loc) if default_loc in UPC_LOCATIONS else 0

        c1, c2 = st.columns(2)
        with c1:
            ticket_type = st.selectbox("Tipo de caso *", ["Incidencia", "Solicitud"], key="ct_type")
            service_name = st.selectbox(
                "Servicio TIC del catálogo *",
                services_list,
                index=services_list.index(default_svc),
                key="ct_service",
            )
            sede = st.selectbox(
                "Sede *",
                UPC_SEDES,
                index=sede_idx,
                key="ct_sede",
            )
        with c2:
            location = st.selectbox("Ubicación / Bloque *", UPC_LOCATIONS, index=loc_idx, key="ct_location")
            urgency_help = (
                "Alta: impide trabajar sin alternativa | Media: hay alternativa temporal | Baja: no bloquea"
            )
            urgency = st.selectbox(
                "¿Qué tan urgente es el caso? *",
                urgency_options,
                index=urgency_options.index(default_urg),
                help=urgency_help,
                key="ct_urgency",
            )
            uploaded_files = st.file_uploader(
                "Adjuntar evidencias (máx. 5 archivos, 10 MB c/u)",
                type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx"],
                accept_multiple_files=True,
                key="ct_attachments",
            )

        # Vista previa en vivo de matriz OR-03
        svc_meta = UPC_SERVICE_CATALOG.get(service_name, {"base_impact": "Medio", "area": "Mesa TIC"})
        preview_prio = calculate_priority_or03(
            svc_meta["base_impact"],
            urgency,
            custom_sla_table=ticket_svc.get_sla_table() or None,
        )
        st.markdown(
            f"""<div class="upc-card-accent">
<div style="font-size:0.84rem;font-weight:700;color:{UPC_GREEN};display:flex;align-items:center;gap:0.4rem;">
{svg_icon('sliders', size=16, color=UPC_GREEN)}<span>Cálculo Automático Matriz OR-03</span>
</div>
<div style="font-size:0.94rem;color:{UPC_SLATE_DARK};margin-top:0.35rem;">
Impacto <code>{preview_prio['impact']}</code> &times; Urgencia <code>{preview_prio['urgency']}</code>
&rarr; Prioridad <strong>{preview_prio['priority']}</strong>
(SLA Respuesta: {preview_prio['sla_response_hours']}h | Resolución: {preview_prio['sla_resolution_hours']}h)
· Área destino: <strong>{svc_meta['area']}</strong>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        form_ready = title_ok and desc_ok and bool(sede) and bool(service_name)
        col_sub, col_cancel = st.columns([2, 1])
        with col_sub:
            submit_ticket = st.button(
                "Enviar y Radicar Ticket",
                type="primary",
                disabled=not form_ready,
                use_container_width=True,
                key="ct_submit_btn",
            )
        with col_cancel:
            if st.button("Cancelar", use_container_width=True, key="ct_cancel_btn"):
                LifecycleManager.on_route_change("landing")
                st.rerun()

        if not form_ready:
            st.caption("Complete un asunto (>= 5 caracteres) y una descripción (>= 15 caracteres) para habilitar el envío.")

        if submit_ticket:
            try:
                att_payload = [(f.name, f.getvalue()) for f in (uploaded_files or [])]
                ai_sugg = (
                    draft_pred["predicted_service"]
                    if draft_pred
                    else prefill.get("service_name")
                )
                ai_conf = (
                    draft_pred["confidence_pct"]
                    if draft_pred
                    else prefill.get("ai_confidence")
                )
                created = ticket_svc.create_ticket(
                    requester=user,
                    title=title_val,
                    description=desc_val,
                    ticket_type=ticket_type,
                    service_name=service_name,
                    sede=sede,
                    location=location,
                    urgency=urgency,
                    ai_suggested_service=ai_sugg,
                    ai_confidence=ai_conf,
                    ai_human_validated=bool(ai_sugg),
                    attachments=att_payload,
                    initial_transcript=prefill.get("transcript"),
                )
                LifecycleManager.invalidate_caches(clear_data=False)
                nav.prefill_ticket_data = None
                t_store.ai_draft_prediction = None
                st.success(
                    f"**Ticket radicado exitosamente: `{created['ticket_number']}`**\n\n"
                    f"- **Prioridad:** {created['priority']} (SLA Resolución: {created['sla_resolution_hours']}h)\n"
                    f"- **Estado:** {created['status']}\n"
                    f"- **Técnico asignado:** {created.get('assigned_tech_email') or 'Cola de coordinación'}"
                )
                nav.selected_ticket_number = created["ticket_number"]
            except Exception as exc:
                st.error(f"Error al registrar el ticket: {exc}")

        if nav.selected_ticket_number:
            if st.button(f"Ver detalle y chat de {nav.selected_ticket_number}", key="ct_go_detail"):
                LifecycleManager.on_route_change("track_ticket", selected_ticket=nav.selected_ticket_number)
                st.rerun()

    with col_right:
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.45rem;margin-top:0;'>"
            f"{svg_icon('book-open', size=19, color=UPC_GREEN)}<span>Guías de Autoservicio Sugeridas</span></h3>",
            unsafe_allow_html=True,
        )
        st.caption("Revise si alguna solución oficial resuelve su caso antes de crear el ticket (CU-02).")
        query_for_kb = f"{title_val} {desc_val}".strip() or service_name
        kb_hits = ai_svc.search_knowledge_base(
            query_for_kb,
            top_k=3,
            min_similarity=0.05,
            service_filter=service_name if not (title_val or desc_val).strip() else None,
        )
        if not kb_hits:
            kb_hits = ai_svc.search_knowledge_base(service_name, top_k=2, min_similarity=0.01)

        for art in kb_hits:
            with st.expander(f"[{art['code']}] {art['title']}", expanded=False):
                st.markdown(f"**Síntomas:** {art['symptoms']}")
                st.markdown(f"**Pasos:**\n{art['solution_steps']}")

        if st.button("Mi problema se resolvió con una guía", use_container_width=True, key="ct_self_solved_btn"):
            st.success("Caso resuelto mediante autoservicio institucional sin necesidad de generar ticket.")
