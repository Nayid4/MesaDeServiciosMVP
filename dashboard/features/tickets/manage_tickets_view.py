"""Bandeja operativa 2 columnas, reasignación, KB, usuarios, catálogo SLA y auditoría (SRP)."""

from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from dashboard.features.tickets.ticket_detail_panel import render_ticket_detail_two_columns
from dashboard.shared.components import render_breadcrumbs, render_section_header
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_auth_service,
    get_ticket_service,
)
from src.domain.rules import (
    ALL_TICKET_STATUSES,
    UPC_SEDES,
    UPC_TECHNICAL_AREAS,
    VALID_ROLES,
)


def render() -> None:
    auth = StoreManager.auth()
    user = auth.user
    assert user is not None
    role = user["role"]

    ticket_svc = get_ticket_service()
    auth_svc = get_auth_service()

    render_breadcrumbs(["Workspace", "Bandeja de Operación y Administración"])
    render_section_header(
        "Bandeja de Operación, Gestión y Configuración",
        "Atención técnica ITIL v4 a 2 columnas, balanceo de carga, Base de Conocimiento y bitácora inmutable.",
        icon_name="sliders",
    )

    tab_names = ["Bandeja de Tickets (Vista 2 Columnas)"]
    if role in ("coordinador", "admin"):
        tab_names.append("Reasignar, Prioridad y Cargas")
    tab_names.append("Base de Conocimiento")
    if role == "admin":
        tab_names.extend(["Usuarios y Roles", "Catálogo SLA y Auditoría"])

    tabs = st.tabs(tab_names)
    tab_idx = 0

    # --- TAB 1: Bandeja de Tickets y Gestión Detallada a 2 Columnas ---
    with tabs[tab_idx]:
        col_f1, col_f2, col_f3, col_mon = st.columns([1.5, 1.5, 2.0, 1.5])
        with col_f1:
            f_status = st.selectbox("Filtrar Estado", ["Todos"] + list(ALL_TICKET_STATUSES), key="mg_st")
        with col_f2:
            f_prio = st.selectbox("Filtrar Prioridad", ["Todas", "P1 Crítica", "P2 Alta", "P3 Media", "P4 Baja"], key="mg_pr")
        with col_f3:
            f_search = st.text_input("Buscar radicado/asunto", key="mg_search")
        with col_mon:
            st.write("")
            if st.button("Verificar SLA", use_container_width=True, key="mg_sla_mon"):
                res = ticket_svc.run_sla_monitor(actor_email=user["email"])
                LifecycleManager.invalidate_caches(clear_data=False)
                st.toast(
                    f"SLA verificado: {res['alerts_75']} alertas 75%, {res['breaches']} vencimientos, {res['auto_closed']} autocierres."
                )

        tickets = ticket_svc.list_visible_tickets(
            user=user,
            status=None if f_status == "Todos" else f_status,
            priority=None if f_prio == "Todas" else f_prio,
            search=f_search or None,
        )

        if not tickets:
            st.info("No hay tickets pendientes con los filtros actuales.")
        else:
            options = [f"{t['ticket_number']} · [{t['priority']}] {t['title']} ({t['status']})" for t in tickets]
            chosen_idx = st.selectbox(
                "Seleccione un ticket para gestionar",
                range(len(options)),
                format_func=lambda i: options[i],
                key="mg_select_ticket",
            )
            chosen_ticket = tickets[chosen_idx]
            st.divider()
            render_ticket_detail_two_columns(
                ticket_number=chosen_ticket["ticket_number"],
                user=user,
                ticket_svc=ticket_svc,
                auth_svc=auth_svc,
                key_prefix="mg",
            )

    # --- TAB 2: Reasignación, Prioridad y Balanceo de Carga (Coordinador / Admin) ---
    if role in ("coordinador", "admin"):
        tab_idx += 1
        with tabs[tab_idx]:
            st.subheader("Reasignación de Tickets, Prioridad y Carga por Técnico")

            workload = ticket_svc.get_technician_workload()
            if workload:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Técnico": w["full_name"],
                                "Correo": w["email"],
                                "Área": w["area"],
                                "Sede": w["sede"],
                                "Tickets Abiertos": w["open_tickets"],
                                "Resueltos/Cerrados": w["resolved_tickets"],
                            }
                            for w in workload
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            open_list = [
                tk
                for tk in ticket_svc.list_visible_tickets(user=user)
                if tk["status"] not in ("Cerrado", "Anulado")
            ]
            if not open_list:
                st.info("No hay tickets abiertos disponibles para reasignación.")
            else:
                sel_i = st.selectbox(
                    "Ticket a intervenir",
                    range(len(open_list)),
                    format_func=lambda i: f"{open_list[i]['ticket_number']} | {open_list[i]['area']} | Tech: {open_list[i].get('assigned_tech_email') or 'Cola'}",
                    key="reas_tk_sel",
                )
                tk = open_list[sel_i]
                techs = auth_svc.list_active_technicians()

                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    with st.form("reassign_form"):
                        st.markdown("**Reasignar Responsable / Área (RF-11)**")
                        new_area = st.selectbox(
                            "Área técnica",
                            UPC_TECHNICAL_AREAS,
                            index=UPC_TECHNICAL_AREAS.index(tk["area"]) if tk["area"] in UPC_TECHNICAL_AREAS else 0,
                        )
                        tech_opts = {f"{x['full_name']} ({x['area']})": x["id"] for x in techs}
                        chosen_tech_label = st.selectbox("Nuevo técnico asignado", ["(Dejar en cola del área)"] + list(tech_opts.keys()))
                        reason = st.text_input("Motivo de reasignación *")
                        if st.form_submit_button("Confirmar Reasignación", type="primary"):
                            try:
                                new_tid = None if chosen_tech_label.startswith("(") else tech_opts[chosen_tech_label]
                                ticket_svc.reassign_ticket(tk["id"], user, new_tech_id=new_tid, new_area=new_area, reason=reason)
                                LifecycleManager.invalidate_caches(clear_data=False)
                                st.success("Ticket reasignado conservando su SLA original.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

                with c_r2:
                    with st.form("adj_prio_form"):
                        st.markdown("**Ajustar Prioridad OR-03 (HU-05)**")
                        new_imp = st.selectbox("Impacto", ["Alto", "Medio", "Bajo"], index=["Alto", "Medio", "Bajo"].index(tk["impact"]))
                        new_urg = st.selectbox("Urgencia", ["Alta", "Media", "Baja"], index=["Alta", "Media", "Baja"].index(tk["urgency"]))
                        just = st.text_input("Justificación obligatoria *")
                        if st.form_submit_button("Actualizar Prioridad"):
                            try:
                                ticket_svc.adjust_priority(tk["id"], user, new_imp, new_urg, just)
                                LifecycleManager.invalidate_caches(clear_data=False)
                                st.success("Prioridad ajustada y registrada en historial y auditoría.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

    # --- TAB 3: Base de Conocimiento (CU-16 / RF-21) ---
    tab_idx += 1
    with tabs[tab_idx]:
        st.subheader("Gestión de Base de Conocimiento Institucional")
        articles = ticket_svc.list_kb_articles()
        for art in articles:
            with st.expander(f"[{art['code']}] {art['title']} · {art['status']} ({art['visibility']}) v{art['version']}"):
                st.markdown(f"**Servicio:** {art['service_name']} | **Autor:** {art['author_email']}")
                st.markdown(f"**Síntomas:** {art['symptoms']}")
                st.markdown(f"**Pasos:**\n{art['solution_steps']}")
                if role in ("coordinador", "admin"):
                    c_pub, c_ret = st.columns(2)
                    if art["status"] != "Publicado":
                        if c_pub.button("Aprobar y Publicar", key=f"kb_pub_{art['id']}", type="primary"):
                            ticket_svc.upsert_kb_article(
                                user,
                                {**art, "status": "Publicado", "reviewer_email": user["email"]},
                            )
                            st.rerun()
                    if art["status"] != "Retirado":
                        if c_ret.button("Retirar artículo", key=f"kb_ret_{art['id']}"):
                            ticket_svc.upsert_kb_article(
                                user,
                                {**art, "status": "Retirado", "reviewer_email": user["email"]},
                            )
                            st.rerun()

        st.divider()
        with st.form("new_kb_form"):
            st.markdown("**Proponer o Publicar Nuevo Artículo KB**")
            kb_title = st.text_input("Título del artículo *")
            kb_svc = st.selectbox("Servicio relacionado *", [s["service_name"] for s in ticket_svc.get_active_services()])
            kb_vis = st.selectbox("Visibilidad", ["Pública", "Interna"])
            kb_symp = st.text_area("Síntomas / Problema *")
            kb_steps = st.text_area("Solución paso a paso *")
            kb_kw = st.text_input("Palabras clave (separadas por espacio)")
            if st.form_submit_button("Guardar Artículo", type="primary"):
                if not kb_title.strip() or not kb_symp.strip() or not kb_steps.strip():
                    st.error("Complete título, síntomas y solución.")
                else:
                    status_init = "Publicado" if role in ("coordinador", "admin") else "En revisión"
                    ticket_svc.upsert_kb_article(
                        user,
                        {
                            "title": kb_title.strip(),
                            "service_name": kb_svc,
                            "symptoms": kb_symp.strip(),
                            "solution_steps": kb_steps.strip(),
                            "keywords": kb_kw.strip(),
                            "visibility": kb_vis,
                            "status": status_init,
                            "author_email": user["email"],
                            "reviewer_email": user["email"] if status_init == "Publicado" else None,
                        },
                    )
                    st.success(f"Artículo guardado en estado `{status_init}`.")
                    st.rerun()

    # --- TAB 4 & 5: Solo Admin ---
    if role == "admin":
        tab_idx += 1
        with tabs[tab_idx]:
            st.subheader("Gestión de Usuarios, Roles y Áreas (CU-14 / RF-02)")
            all_users = auth_svc.list_users()
            df_u = pd.DataFrame(
                [
                    {
                        "ID": u["id"],
                        "Nombre": u["full_name"],
                        "Correo": u["email"],
                        "Rol": u["role"],
                        "Área": u.get("area") or "-",
                        "Sede": u.get("sede"),
                        "Estado": "Activo" if u["is_active"] else "Inactivo",
                    }
                    for u in all_users
                ]
            )
            st.dataframe(df_u, use_container_width=True, hide_index=True)

            target_idx = st.selectbox(
                "Editar usuario",
                range(len(all_users)),
                format_func=lambda i: f"{all_users[i]['full_name']} ({all_users[i]['email']}) - {all_users[i]['role']}",
                key="adm_user_sel",
            )
            tu = all_users[target_idx]
            with st.form("edit_user_form"):
                u_role = st.selectbox("Rol", list(VALID_ROLES), index=list(VALID_ROLES).index(tu["role"]))
                area_opts = ["(Ninguna)"] + UPC_TECHNICAL_AREAS + ["Oficina de Informática y Sistemas", "Dirección TIC"]
                u_area_idx = area_opts.index(tu["area"]) if tu.get("area") in area_opts else 0
                u_area = st.selectbox("Área técnica", area_opts, index=u_area_idx)
                u_sede = st.selectbox("Sede", UPC_SEDES, index=UPC_SEDES.index(tu["sede"]) if tu.get("sede") in UPC_SEDES else 0)
                u_active = st.checkbox("Cuenta activa", value=bool(tu["is_active"]))
                if st.form_submit_button("Guardar Cambios de Usuario", type="primary"):
                    try:
                        auth_svc.update_user_admin(
                            actor_email=user["email"],
                            target_user_id=tu["id"],
                            role=u_role,
                            area=None if u_area == "(Ninguna)" else u_area,
                            is_active=u_active,
                            sede=u_sede,
                        )
                        st.success("Usuario actualizado y registrado en auditoría.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        tab_idx += 1
        with tabs[tab_idx]:
            st.subheader("Configuración de SLA (RF-24) y Bitácora Inmutable (RF-25)")
            sla_tbl = ticket_svc.get_sla_table()
            c_sla, c_aud = st.columns([1, 1.8])
            with c_sla:
                st.markdown("**Tiempos Objetivo SLA**")
                sel_prio = st.selectbox("Prioridad", list(sla_tbl.keys()), key="adm_sla_prio")
                cur_vals = sla_tbl[sel_prio]
                resp_h = st.number_input("Respuesta (horas hábiles)", min_value=0.25, max_value=48.0, value=float(cur_vals["sla_response_hours"]), step=0.25)
                res_h = st.number_input("Resolución (horas hábiles)", min_value=0.5, max_value=120.0, value=float(cur_vals["sla_resolution_hours"]), step=0.5)
                if st.button("Actualizar SLA", type="primary"):
                    try:
                        ticket_svc.update_sla_config(user, sel_prio, resp_h, res_h)
                        st.success("SLA actualizado para nuevos tickets.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

            with c_aud:
                st.markdown("**Bitácora de Auditoría Inmutable (Append-Only)**")
                f_act = st.text_input("Filtrar por acción", placeholder="LOGIN, TICKET, ML...")
                logs = ticket_svc.list_audit_logs(user, action=f_act or None, limit=200)
                df_logs = pd.DataFrame(logs)
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
                if not df_logs.empty:
                    buf = io.BytesIO()
                    df_logs.to_excel(buf, index=False, engine="openpyxl")
                    st.download_button(
                        "Exportar Auditoría XLSX",
                        data=buf.getvalue(),
                        file_name="auditoria_casagbi_upc.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
