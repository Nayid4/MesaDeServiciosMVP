"""Panel reutilizable a 2 columnas para detalle, reasignación, timeline, chat, solución y CSAT."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import streamlit as st

from dashboard.shared.components import (
    render_priority_badge,
    render_sla_badge,
    render_status_badge,
)
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import LifecycleManager
from dashboard.shared.styles import UPC_GREEN, UPC_SLATE_DARK
from src.application.auth_use_cases import AuthService
from src.application.ticket_use_cases import TicketService
from src.domain.rules import (
    CLOSING_CATEGORIES,
    UPC_TECHNICAL_AREAS,
    VALID_TRANSITIONS,
)


def render_ticket_detail_two_columns(
    ticket_number: str,
    user: Dict[str, Any],
    ticket_svc: TicketService,
    auth_svc: AuthService,
    key_prefix: str = "det",
) -> None:
    """
    Renderiza vista operativa a 2 columnas (RIU-07):
    - Izquierda: Ficha técnica, semáforo SLA en vivo, reasignación (Coord/Admin) y timeline.
    - Derecha: Chat bidireccional, diagnóstico/solución inline y cierre + CSAT o reapertura.
    """
    try:
        detail = ticket_svc.get_ticket_detail(ticket_number, user=user)
    except PermissionError as exc:
        st.error(str(exc))
        return

    if not detail:
        st.warning(f"No se encontró detalle para `{ticket_number}`.")
        return

    t = detail["ticket"]
    sla = detail["sla"]
    history = detail["history"]
    messages = detail["messages"]
    role = user["role"]

    left_zone, right_zone = st.columns([1.15, 1.0])

    # ================= COLUMNA IZQUIERDA =================
    with left_zone:
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.45rem;margin-top:0;'>"
            f"{svg_icon('file-text', size=20, color=UPC_GREEN)}<span>Ficha Técnica: {t['ticket_number']}</span></h3>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""<div class="upc-card-accent">
<div style="font-size:1.08rem;font-weight:800;color:{UPC_SLATE_DARK};margin-bottom:0.45rem;">{t['title']}</div>
<p style="font-size:0.93rem;color:#334155;margin-bottom:0.75rem;">{t['description']}</p>
<div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.8rem;">
{render_status_badge(t['status'])}
{render_priority_badge(t['priority'])}
{render_sla_badge(t)}
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.45rem;font-size:0.86rem;color:#475569;border-top:1px solid #E2E8F0;padding-top:0.65rem;">
<div><strong>Servicio:</strong> {t['service_name']}</div>
<div><strong>Área técnica:</strong> {t['area']}</div>
<div><strong>Sede:</strong> {t['sede']}</div>
<div><strong>Ubicación:</strong> {t['location']}</div>
<div><strong>Solicitante:</strong> {t['requester_email']}</div>
<div><strong>Técnico:</strong> {t.get('assigned_tech_email') or 'Cola de coordinación'}</div>
<div><strong>Tipo:</strong> {t['ticket_type']}</div>
<div><strong>Límite SLA:</strong> {str(t.get('resolution_deadline', ''))[:16].replace('T', ' ')}</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        # Barra visual de consumo SLA
        pct_val = min(100, max(0, int(round(sla["pct_consumed"]))))
        st.caption(f"Consumo SLA de Resolución: {sla['pct_consumed']:.1f}% ({sla['semaphore']})")
        st.progress(pct_val / 100.0)

        if t.get("diagnosis") or t.get("solution"):
            st.markdown(
                f"""<div class="upc-card" style="border-left:4px solid #10B981;background:#F0FDF4;">
<div style="font-weight:700;color:#166534;display:flex;align-items:center;gap:0.4rem;margin-bottom:0.35rem;">
{svg_icon('check-circle', size=16, color='#166534')}<span>Solución Documentada ({t.get('closing_category') or 'ITIL'})</span>
</div>
<div style="font-size:0.88rem;color:#1E293B;"><strong>Diagnóstico:</strong> {t.get('diagnosis') or '-'}</div>
<div style="font-size:0.88rem;color:#1E293B;margin-top:0.3rem;"><strong>Solución:</strong> {t.get('solution') or '-'}</div>
</div>""",
                unsafe_allow_html=True,
            )

        # Control de Reasignación y Prioridad para Coordinador / Admin
        if role in ("coordinador", "admin") and t["status"] not in ("Cerrado", "Anulado"):
            with st.expander("Reasignar Responsable / Ajustar Prioridad (Coordinación)", expanded=False):
                techs = auth_svc.list_active_technicians()
                c_reas1, c_reas2 = st.columns(2)
                with c_reas1:
                    with st.form(f"{key_prefix}_reas_form_{t['id']}"):
                        st.markdown("**Reasignar Técnico o Área (RF-11)**")
                        new_area = st.selectbox(
                            "Área técnica",
                            UPC_TECHNICAL_AREAS,
                            index=UPC_TECHNICAL_AREAS.index(t["area"]) if t["area"] in UPC_TECHNICAL_AREAS else 0,
                        )
                        tech_opts = {f"{x['full_name']} ({x['area']})": x["id"] for x in techs}
                        chosen_tech_label = st.selectbox(
                            "Nuevo técnico asignado",
                            ["(Dejar en cola del área)"] + list(tech_opts.keys()),
                        )
                        reason = st.text_input("Motivo obligatorio de reasignación *")
                        if st.form_submit_button("Confirmar Reasignación", type="primary", use_container_width=True):
                            try:
                                new_tid = None if chosen_tech_label.startswith("(") else tech_opts[chosen_tech_label]
                                ticket_svc.reassign_ticket(
                                    t["id"],
                                    user,
                                    new_tech_id=new_tid,
                                    new_area=new_area,
                                    reason=reason,
                                )
                                LifecycleManager.invalidate_caches(clear_data=False)
                                st.success("Ticket reasignado preservando SLA original.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

                with c_reas2:
                    with st.form(f"{key_prefix}_prio_form_{t['id']}"):
                        st.markdown("**Ajustar Prioridad OR-03 (HU-05)**")
                        new_imp = st.selectbox(
                            "Impacto",
                            ["Alto", "Medio", "Bajo"],
                            index=["Alto", "Medio", "Bajo"].index(t["impact"]),
                        )
                        new_urg = st.selectbox(
                            "Urgencia",
                            ["Alta", "Media", "Baja"],
                            index=["Alta", "Media", "Baja"].index(t["urgency"]),
                        )
                        just = st.text_input("Justificación obligatoria *")
                        if st.form_submit_button("Actualizar Prioridad", use_container_width=True):
                            try:
                                ticket_svc.adjust_priority(t["id"], user, new_imp, new_urg, just)
                                LifecycleManager.invalidate_caches(clear_data=False)
                                st.success("Prioridad ajustada y auditada.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

        # Línea de tiempo cronológica
        st.markdown(
            f"<h4 style='display:flex;align-items:center;gap:0.4rem;margin-top:0.85rem;'>"
            f"{svg_icon('clock', size=17, color=UPC_GREEN)}<span>Línea de Tiempo Cronológica</span></h4>",
            unsafe_allow_html=True,
        )
        for h in history:
            ts = str(h.get("created_at", ""))[:16].replace("T", " ")
            cmt_html = f"<div style='font-size:0.82rem;color:#475569;margin-top:0.15rem;'>{h['comment']}</div>" if h.get("comment") else ""
            st.markdown(
                f"""<div class="upc-timeline-item">
<div style="font-size:0.86rem;font-weight:700;color:{UPC_SLATE_DARK};">
{h['action']} <span style="font-weight:500;color:#64748B;">· {ts}</span>
</div>
<div style="font-size:0.8rem;color:{UPC_GREEN};">
{h['actor_email']} ({h.get('old_status') or 'Inicio'} &rarr; {h.get('new_status') or ''})
</div>
{cmt_html}
</div>""",
                unsafe_allow_html=True,
            )

    # ================= COLUMNA DERECHA =================
    with right_zone:
        st.markdown(
            f"<h3 style='display:flex;align-items:center;gap:0.45rem;margin-top:0;'>"
            f"{svg_icon('message-square', size=20, color=UPC_GREEN)}<span>Chat Bidireccional y Gestión</span></h3>",
            unsafe_allow_html=True,
        )

        chat_box = st.container(height=340)
        with chat_box:
            if not messages:
                st.caption("No hay mensajes aún en este ticket.")
            for m in messages:
                is_tech = m["sender_role"] in ("tecnico", "coordinador", "admin")
                bubble_cls = "chat-bubble-tech" if is_tech else "chat-bubble-user"
                ts = str(m.get("created_at", ""))[:16].replace("T", " ")
                read_txt = "Leído" if m.get("is_read") else "Enviado"
                st.markdown(
                    f"""<div class="{bubble_cls}">
<div style="font-size:0.78rem;color:#64748B;display:flex;justify-content:space-between;">
<span><strong>{m['sender_email']}</strong> ({m['sender_role']})</span>
<span>{ts} · {read_txt}</span>
</div>
<div style="margin-top:0.32rem;font-size:0.92rem;color:{UPC_SLATE_DARK};">{m['message']}</div>
</div>""",
                    unsafe_allow_html=True,
                )
                if m.get("attachment_path") and Path(m["attachment_path"]).exists():
                    fpath = Path(m["attachment_path"])
                    if fpath.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        st.image(str(fpath), caption=m.get("attachment_name"), width=240)
                    else:
                        st.download_button(
                            f"Descargar {m.get('attachment_name')}",
                            data=fpath.read_bytes(),
                            file_name=m.get("attachment_name") or fpath.name,
                            key=f"{key_prefix}_dl_msg_{m['id']}",
                        )

        if t["status"] in ("Cerrado", "Anulado"):
            st.info("El ticket está cerrado o anulado; el historial de chat permanece en modo de solo lectura (RF-12).")
        else:
            with st.form(f"{key_prefix}_chat_form_{t['id']}", clear_on_submit=True):
                msg_text = st.text_area("Escribir mensaje al caso", height=76, placeholder="Escriba una actualización o respuesta...")
                chat_file = st.file_uploader(
                    "Adjuntar evidencia opcional",
                    type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx"],
                )
                if st.form_submit_button("Enviar mensaje", type="primary", use_container_width=True):
                    try:
                        att_name = chat_file.name if chat_file else None
                        att_bytes = chat_file.getvalue() if chat_file else None
                        ticket_svc.add_chat_message(
                            t["id"],
                            user,
                            msg_text,
                            attachment_name=att_name,
                            attachment_bytes=att_bytes,
                        )
                        LifecycleManager.invalidate_caches(clear_data=False)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        # --- Gestión operativa inline para Técnico / Coordinador / Admin ---
        can_operate = (
            (role == "tecnico" and t.get("assigned_tech_id") == user["id"])
            or role in ("coordinador", "admin")
        )
        allowed_next = [
            s
            for s in VALID_TRANSITIONS.get(t["status"], [])
            if not (role == "tecnico" and s == "Cerrado")
        ]

        if can_operate and allowed_next:
            st.divider()
            st.markdown(
                f"<h4 style='display:flex;align-items:center;gap:0.4rem;'>"
                f"{svg_icon('sliders', size=17, color=UPC_GREEN)}<span>Transición de Estado ITIL</span></h4>",
                unsafe_allow_html=True,
            )
            target_status = st.selectbox(
                "Siguiente estado permitido",
                allowed_next,
                key=f"{key_prefix}_target_status_{t['id']}",
            )
            if target_status == "Resuelto":
                with st.form(f"{key_prefix}_resolve_form_{t['id']}"):
                    st.markdown("**Documentar Diagnóstico y Solución (RF-15)**")
                    diag = st.text_area("Diagnóstico técnico *", placeholder="Causa raíz identificada...")
                    sol = st.text_area(
                        "Solución aplicada * (mínimo 20 caracteres)",
                        placeholder="Detalle exacto del procedimiento realizado...",
                    )
                    cat_close = st.selectbox("Categoría de cierre *", CLOSING_CATEGORIES)
                    propose_kb = st.checkbox("Proponer esta solución como artículo de Base de Conocimiento (En revisión)")
                    if st.form_submit_button("Documentar Solución y Marcar Resuelto", type="primary", use_container_width=True):
                        try:
                            ticket_svc.transition_status(
                                t["id"],
                                user,
                                "Resuelto",
                                diagnosis=diag,
                                solution=sol,
                                closing_category=cat_close,
                                propose_kb=propose_kb,
                            )
                            LifecycleManager.invalidate_caches(clear_data=False)
                            st.success("Ticket marcado como Resuelto y notificado al usuario.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
            else:
                comment_req = target_status in ("En espera", "Anulado", "Reabierto")
                comment_val = st.text_input(
                    "Comentario / Justificación" + (" *" if comment_req else " (opcional)"),
                    key=f"{key_prefix}_trans_cmt_{t['id']}",
                )
                confirm_ok = True
                if target_status in ("Anulado", "Cerrado"):
                    confirm_ok = st.checkbox(
                        f"Confirmo explícitamente que deseo cambiar este ticket a estado terminal '{target_status}'",
                        key=f"{key_prefix}_confirm_term_{target_status}_{t['id']}",
                    )
                if st.button(
                    f"Aplicar cambio a '{target_status}'",
                    type="primary",
                    disabled=not confirm_ok,
                    use_container_width=True,
                    key=f"{key_prefix}_apply_trans_{t['id']}",
                ):
                    try:
                        ticket_svc.transition_status(t["id"], user, target_status, comment=comment_val)
                        LifecycleManager.invalidate_caches(clear_data=False)
                        st.success(f"Estado actualizado a `{target_status}`.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        # --- Confirmación de Solución (Cerrar + Encuesta CSAT 1-5) o Reapertura para el Solicitante ---
        if t["status"] == "Resuelto" and t["requester_id"] == user["id"]:
            st.divider()
            st.markdown(
                f"<h4 style='display:flex;align-items:center;gap:0.4rem;'>"
                f"{svg_icon('award', size=17, color=UPC_GREEN)}<span>Validar Solución del Caso</span></h4>",
                unsafe_allow_html=True,
            )
            tab_close_csat, tab_reopen = st.tabs(["Confirmar Solución (Cerrar + CSAT)", "Reabrir Caso"])

            with tab_close_csat:
                with st.form(f"{key_prefix}_confirm_close_csat_{t['id']}"):
                    score = st.slider("Calificación de atención CSAT (1 = Muy mala, 5 = Excelente)", 1, 5, 5)
                    csat_comment = st.text_input("Comentario de experiencia (obligatorio si califica 1 o 2)")
                    confirm_close_chk = st.checkbox("Confirmo que el inconveniente fue solucionado y deseo cerrar el ticket")
                    if st.form_submit_button("Confirmar Solución y Cerrar Ticket", type="primary", use_container_width=True):
                        if not confirm_close_chk:
                            st.warning("Marque la casilla de confirmación antes de cerrar definitivamente el ticket.")
                        elif score <= 2 and (not csat_comment or not csat_comment.strip()):
                            st.error("Para calificaciones de 1 o 2, registre un comentario de mejora (CU-10).")
                        else:
                            try:
                                ticket_svc.transition_status(
                                    t["id"],
                                    user,
                                    "Cerrado",
                                    comment="Solución confirmada por el solicitante.",
                                )
                                ticket_svc.submit_csat(t["id"], user, score, csat_comment)
                                LifecycleManager.invalidate_caches(clear_data=False)
                                st.success("Ticket cerrado y encuesta CSAT registrada. Gracias por su evaluación.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

            with tab_reopen:
                with st.form(f"{key_prefix}_reopen_form_{t['id']}"):
                    reopen_reason = st.text_input("Explique por qué el problema persiste *")
                    if st.form_submit_button("El problema continúa (Reabrir caso)", use_container_width=True):
                        try:
                            ticket_svc.transition_status(t["id"], user, "Reabierto", comment=reopen_reason)
                            LifecycleManager.invalidate_caches(clear_data=False)
                            st.success("Ticket reabierto y escalado al técnico asignado.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        # Si ya está cerrado sin CSAT (ej. autocierre RF-16 o cerrado por coordinador)
        if t["status"] == "Cerrado" and t["requester_id"] == user["id"]:
            if t.get("csat_score") is not None:
                st.info(f"Calificación CSAT registrada: **{t['csat_score']} / 5**.")
            else:
                with st.form(f"{key_prefix}_csat_only_{t['id']}"):
                    st.markdown("**Encuesta de Satisfacción CSAT (1 a 5)**")
                    score = st.slider("Calificación", 1, 5, 5)
                    csat_comment = st.text_input("Comentario (obligatorio si califica 1 o 2)")
                    if st.form_submit_button("Enviar calificación CSAT", type="primary"):
                        try:
                            ticket_svc.submit_csat(t["id"], user, score, csat_comment)
                            LifecycleManager.invalidate_caches(clear_data=False)
                            st.success("Gracias por evaluar el servicio TIC.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
