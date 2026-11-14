"""CASAGBI Agent: Agente Conversacional IA con 4 Herramientas y Flujo Human-in-the-Loop."""

from __future__ import annotations

import streamlit as st

from dashboard.shared.components import (
    render_breadcrumbs,
    render_priority_badge,
    render_section_header,
)
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_lazy_ai_service,
    get_ticket_service,
)
from dashboard.shared.styles import UPC_EMERALD, UPC_GREEN, UPC_SLATE_DARK
from src.domain.rules import UPC_LOCATIONS, UPC_SEDES, UPC_SERVICE_CATALOG


def _run_agent_turn(prompt_text: str, user: dict, ai_svc, ai_store) -> None:
    ai_store.messages.append({"role": "user", "content": prompt_text})
    res = ai_svc.process_assistant_message(
        user=user,
        message_text=prompt_text,
        failed_attempts=ai_store.failed_attempts,
        simulate_failure=ai_store.simulate_ai_failure,
    )
    ai_store.messages.append(
        {
            "role": "assistant",
            "content": res["reply"],
            "tool_invoked": res.get("tool_invoked", "agent"),
            "status": res.get("status", "ok"),
        }
    )
    if res.get("prefill"):
        ai_store.pending_prefill = res["prefill"]
    if res.get("draft_card"):
        ai_store.pending_draft_card = res["draft_card"]
    if res.get("prediction"):
        ai_store.last_prediction = res["prediction"]


def render() -> None:
    auth = StoreManager.auth()
    ai_store = StoreManager.ai()
    user = auth.user
    assert user is not None

    ai_svc = get_lazy_ai_service()
    ticket_svc = get_ticket_service()

    render_breadcrumbs(["Workspace", "CASAGBI Agent (Soporte Nivel 0)"])
    render_section_header(
        "CASAGBI Agent · Asistente Conversacional TIC",
        "Agente inteligente híbrido con herramientas reales sobre la Base de Conocimiento, Tickets SQLite y Clasificador NLP.",
        icon_name="bot",
    )

    st.markdown(
        f"""<div class="upc-card-accent">
<div style="font-weight:700;color:{UPC_GREEN};display:flex;align-items:center;gap:0.45rem;margin-bottom:0.3rem;">
{svg_icon('shield-check', size=16, color=UPC_GREEN)}<span>Transparencia IA (Regla OR-08) y 4 Herramientas Activas</span>
</div>
<div style="font-size:0.88rem;color:#475569;">
Opero mediante un enrutador híbrido conectado a:
<code>search_knowledge_base</code> · <code>check_ticket_status</code> ·
<code>classify_and_draft_ticket</code> · <code>escalate_to_human</code>.
Usted conserva siempre la validación final antes de radicar o cerrar cualquier ticket.
</div>
</div>""",
        unsafe_allow_html=True,
    )

    col_top1, col_top2, col_top3 = st.columns([2.0, 1.3, 1.2])
    with col_top1:
        ai_store.simulate_ai_failure = st.toggle(
            "Simular Indisponibilidad del Motor IA (RNF-06)",
            value=ai_store.simulate_ai_failure,
            key="ai_sim_failure_toggle",
        )
    with col_top2:
        if st.button("Transferir a un Técnico Humano", type="primary", use_container_width=True, key="ai_escalate_top"):
            try:
                esc = ai_svc.escalate_to_human(
                    user=user,
                    conversation_history=ai_store.messages,
                    draft_card=ai_store.pending_draft_card or ai_store.pending_prefill,
                    ticket_service=ticket_svc,
                )
                created = esc["ticket"]
                LifecycleManager.invalidate_caches(clear_data=False)
                ai_store.pending_prefill = None
                ai_store.pending_draft_card = None
                ai_store.failed_attempts = 0
                ai_store.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            f"**Transferencia ejecutada a técnico humano (`escalate_to_human`)**\n\n"
                            f"- **Ticket creado:** `{created['ticket_number']}`\n"
                            f"- **Prioridad OR-03:** `{created['priority']}`\n"
                            f"- **Técnico asignado:** `{created.get('assigned_tech_email') or 'Cola de coordinación'}`\n"
                            "La transcripción completa de este chat quedó adjunta en el caso."
                        ),
                        "tool_invoked": "escalate_to_human",
                        "status": "escalated",
                    }
                )
                StoreManager.nav().selected_ticket_number = created["ticket_number"]
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible transferir automáticamente: {exc}")

    with col_top3:
        if st.button("Ir al Formulario Manual", use_container_width=True, key="ai_go_manual_top"):
            transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in ai_store.messages)
            last_user_msg = next((m["content"] for m in reversed(ai_store.messages) if m["role"] == "user"), "")
            prefill = dict(ai_store.pending_prefill or {})
            prefill.setdefault("title", last_user_msg[:75] or "Solicitud desde CASAGBI Agent")
            prefill.setdefault("description", last_user_msg or "Requiero atención de soporte humano.")
            prefill["transcript"] = transcript
            LifecycleManager.on_route_change("create_ticket", preserve_prefill=True)
            StoreManager.nav().prefill_ticket_data = prefill
            st.rerun()

    if ai_store.simulate_ai_failure:
        st.warning(
            "**Modo de contingencia activo (RNF-06):** El motor de IA está simulando caída controlada. "
            "Las consultas conservan su contexto para radicar manualmente sin pérdida de información."
        )

    # Chips de prueba rápida de capacidades agénticas
    st.caption("Sugerencias rápidas para probar las capacidades del agente:")
    q_chips = [
        ("Horarios y sedes", "¿Qué horarios y sedes atiende CASAGBI?"),
        ("Guía Wi-Fi Eduroam", "¿Cómo me conecto a la red Wi-Fi Eduroam con mi cuenta?"),
        ("Estado radicado", "¿Cuál es el estado de mis tickets?"),
        ("Borrador proyector", "No enciende el videoproyector en el Bloque B de Sede Sabanas y tengo clase"),
    ]
    chip_cols = st.columns(len(q_chips))
    for col, (lbl, sample_q) in zip(chip_cols, q_chips):
        with col:
            if st.button(lbl, key=f"chip_{lbl}", use_container_width=True):
                _run_agent_turn(sample_q, user, ai_svc, ai_store)
                st.rerun()

    if not ai_store.messages:
        ai_store.messages.append(
            {
                "role": "assistant",
                "content": (
                    f"Hola, **{user['full_name']}**. Soy **CASAGBI Agent**.\n\n"
                    "Puedo responder dudas de la UPC (horarios, sedes, matriz OR-03), buscar soluciones en la "
                    "Base de Conocimiento, consultar el estado en vivo de tus radicados o pre-clasificar un "
                    "ticket en 1 clic con confirmación humana."
                ),
                "tool_invoked": "conversational_domain",
                "status": "conversational",
            }
        )

    chat_container = st.container(height=360)
    with chat_container:
        for msg in ai_store.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant" and msg.get("tool_invoked"):
                    st.markdown(
                        f"<span class='upc-tool-chip'>{svg_icon('sparkles', size=12, color=UPC_GREEN)}"
                        f"<span>Tool: {msg['tool_invoked']}</span></span>",
                        unsafe_allow_html=True,
                    )
                st.markdown(msg["content"])

    prompt = st.chat_input("Escribe tu consulta de soporte TIC o número de radicado aquí...")
    if prompt:
        _run_agent_turn(prompt, user, ai_svc, ai_store)
        st.rerun()

    # Botones de retroalimentación rápida cuando hubo coincidencia KB
    if len(ai_store.messages) >= 2 and ai_store.messages[-1]["role"] == "assistant":
        last_status = ai_store.messages[-1].get("status")
        if last_status == "kb_matched":
            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button("Sí, la guía resolvió mi consulta", use_container_width=True, key="ai_fb_yes"):
                    ai_store.failed_attempts = 0
                    ai_store.pending_prefill = None
                    ai_store.pending_draft_card = None
                    ai_store.messages.append(
                        {
                            "role": "assistant",
                            "content": "Caso resuelto mediante autoservicio en Nivel 0. Avísame si necesitas algo más.",
                            "tool_invoked": "search_knowledge_base",
                            "status": "ok",
                        }
                    )
                    st.rerun()
            with c_no:
                if st.button("No resolvió el problema (preparar ticket)", use_container_width=True, key="ai_fb_no"):
                    ai_store.failed_attempts += 1
                    ai_store.messages.append(
                        {
                            "role": "assistant",
                            "content": (
                                "Comprendido. He preparado la **tarjeta interactiva de pre-radicación** debajo con la "
                                "clasificación estimada para que confirmes el ticket en 1 clic."
                            ),
                            "tool_invoked": "classify_and_draft_ticket",
                            "status": "no_kb_match",
                        }
                    )
                    st.rerun()

    # Tarjeta interactiva Human-in-the-Loop generada por Tool 3 (classify_and_draft_ticket)
    show_card = bool(ai_store.pending_prefill) and (
        ai_store.messages[-1].get("tool_invoked") in ("classify_and_draft_ticket", "escalate_to_human", "fallback_contingency")
        or ai_store.failed_attempts >= 1
        or ai_store.simulate_ai_failure
    )
    if show_card and ai_store.pending_prefill:
        pf = ai_store.pending_prefill
        dc = ai_store.pending_draft_card or {}
        st.divider()
        st.markdown(
            f"""<div class="upc-card-accent">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
<div style="font-weight:800;font-size:1.05rem;color:{UPC_SLATE_DARK};display:flex;align-items:center;gap:0.45rem;">
{svg_icon('ticket', size=19, color=UPC_GREEN)}<span>Borrador Inteligente de Ticket (Human-in-the-Loop)</span>
</div>
<div>
{render_priority_badge(dc.get('priority', 'P3 Media'))}
<span class="badge-pill badge-emerald">Confianza IA: {pf.get('ai_confidence', 0)}%</span>
</div>
</div>
<div style="font-size:0.86rem;color:#475569;margin-top:0.35rem;">
Área técnica estimada: <strong>{dc.get('area', 'Mesa TIC')}</strong> ·
Impacto: <strong>{dc.get('impact', 'Medio')}</strong> ·
SLA Resolución: <strong>{dc.get('sla_resolution_hours', 24)}h</strong>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        svc_names = list(UPC_SERVICE_CATALOG.keys())
        default_svc = pf.get("service_name") if pf.get("service_name") in svc_names else svc_names[0]
        urg_opts = ["Alta", "Media", "Baja"]
        default_urg = pf.get("urgency") if pf.get("urgency") in urg_opts else "Media"
        default_sede = pf.get("sede") if pf.get("sede") in UPC_SEDES else UPC_SEDES[0]
        default_loc = pf.get("location") if pf.get("location") in UPC_LOCATIONS else UPC_LOCATIONS[0]

        with st.form("ai_guided_ticket_form"):
            g_title = st.text_input("Asunto del ticket *", value=pf.get("title", ""))
            g_desc = st.text_area("Descripción detallada * (mín. 15 caracteres)", value=pf.get("description", ""), height=90)
            col_g1, col_g2, col_g3, col_g4 = st.columns(4)
            g_svc = col_g1.selectbox("Servicio TIC *", svc_names, index=svc_names.index(default_svc))
            g_urg = col_g2.selectbox("Urgencia *", urg_opts, index=urg_opts.index(default_urg))
            g_sede = col_g3.selectbox("Sede *", UPC_SEDES, index=UPC_SEDES.index(default_sede))
            g_loc = col_g4.selectbox("Ubicación / Bloque *", UPC_LOCATIONS, index=UPC_LOCATIONS.index(default_loc))

            if st.form_submit_button("Confirmar y Radicar Ticket en 1 Clic", type="primary", use_container_width=True):
                try:
                    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in ai_store.messages)
                    created = ticket_svc.create_ticket(
                        requester=user,
                        title=g_title,
                        description=g_desc,
                        ticket_type=UPC_SERVICE_CATALOG[g_svc]["default_type"],
                        service_name=g_svc,
                        sede=g_sede,
                        location=g_loc,
                        urgency=g_urg,
                        ai_suggested_service=pf.get("service_name"),
                        ai_confidence=pf.get("ai_confidence"),
                        ai_human_validated=True,
                        initial_transcript=transcript,
                    )
                    LifecycleManager.invalidate_caches(clear_data=False)
                    ai_store.pending_prefill = None
                    ai_store.pending_draft_card = None
                    ai_store.failed_attempts = 0
                    ai_store.messages.append(
                        {
                            "role": "assistant",
                            "content": (
                                f"**Ticket radicado exitosamente: `{created['ticket_number']}`**\n\n"
                                f"- **Prioridad:** `{created['priority']}`\n"
                                f"- **Técnico asignado:** `{created.get('assigned_tech_email') or 'Cola de coordinación'}`\n"
                                "Puedes hacerle seguimiento desde **Mis Tickets**."
                            ),
                            "tool_invoked": "classify_and_draft_ticket",
                            "status": "ok",
                        }
                    )
                    StoreManager.nav().selected_ticket_number = created["ticket_number"]
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
