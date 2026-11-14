"""Dashboard ejecutivo de KPIs ITIL v4 con filtros globales reactivos, embudo, cargas y CSAT."""

from __future__ import annotations

import io
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.shared.components import (
    render_breadcrumbs,
    render_kpi_card,
    render_section_header,
)
from dashboard.shared.store import StoreManager, get_ticket_service, load_clean_dataset_cached
from dashboard.shared.styles import UPC_EMERALD, UPC_GREEN, UPC_SLATE_DARK
from src.domain.rules import ALL_TICKET_STATUSES, UPC_SEDES, calculate_sla_status
from src.metrics import compute_itil_kpis


def render() -> None:
    auth = StoreManager.auth()
    t_store = StoreManager.tickets()
    user = auth.user
    assert user is not None

    ticket_svc = get_ticket_service()

    render_breadcrumbs(["Workspace", "Dashboard Ejecutivo KPIs ITIL v4"])
    render_section_header(
        "Tablero Ejecutivo de Indicadores ITIL v4",
        f"Métricas operativas en tiempo real segmentadas por permisos RBAC ({user['role']} · {user['email']}).",
        icon_name="chart-bar",
    )

    # Filtros globales reactivos (Sede, Servicio, Prioridad, Estado)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        f_sede = st.selectbox("Sede", ["Todas"] + UPC_SEDES, key="kpi_sede")
    with f2:
        f_svc = st.selectbox("Servicio TIC", ["Todos"] + [s["service_name"] for s in ticket_svc.get_active_services()], key="kpi_svc")
    with f3:
        f_prio = st.selectbox("Prioridad", ["Todas", "P1 Crítica", "P2 Alta", "P3 Media", "P4 Baja"], key="kpi_prio")
    with f4:
        f_status = st.selectbox("Estado ITIL", ["Todos"] + list(ALL_TICKET_STATUSES), key="kpi_status")

    tickets = ticket_svc.list_visible_tickets(
        user=user,
        status=None if f_status == "Todos" else f_status,
        priority=None if f_prio == "Todas" else f_prio,
        sede=None if f_sede == "Todas" else f_sede,
    )
    if f_svc != "Todos":
        tickets = [t for t in tickets if t["service_name"] == f_svc]

    kpis = compute_itil_kpis(tickets)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi_card(
            "Total Tickets",
            str(kpis["total_tickets"]),
            f"{kpis['open_tickets']} activos en atención",
            delta=f"{kpis['resolved_or_closed']} resueltos/cerrados",
            icon_name="ticket",
        )
    with k2:
        sla_ok = kpis["sla_compliance_pct"] >= 85.0
        render_kpi_card(
            "Cumplimiento SLA",
            f"{kpis['sla_compliance_pct']}%",
            f"{kpis['breached_open_count']} vencidos · {kpis['at_risk_open_count']} en riesgo",
            delta="Meta >= 85%" if sla_ok else "Por debajo de meta",
            delta_positive=sla_ok,
            icon_name="shield-check",
        )
    with k3:
        render_kpi_card(
            "Resolución Promedio",
            f"{kpis['avg_resolution_hours']} h",
            "Horas netas descontando espera",
            delta=f"1ra resp: {kpis['avg_first_response_min']} min",
            icon_name="clock",
        )
    with k4:
        reopen_ok = kpis["reopen_rate_pct"] <= 10.0
        render_kpi_card(
            "Tasa Reapertura",
            f"{kpis['reopen_rate_pct']}%",
            "Calidad técnica de cierre",
            delta="Óptimo <= 10%" if reopen_ok else "Requiere revisión",
            delta_positive=reopen_ok,
            icon_name="refresh-cw",
        )
    with k5:
        csat_ok = kpis["avg_csat"] == 0.0 or kpis["avg_csat"] >= 4.0
        render_kpi_card(
            "Satisfacción CSAT",
            f"{kpis['avg_csat']} / 5",
            "Encuesta post-cierre usuario",
            delta="Objetivo >= 4.0" if csat_ok else "Alerta calidad",
            delta_positive=csat_ok,
            icon_name="award",
        )

    tab_ops, tab_hist = st.tabs(["Operación en Vivo (SQLite)", "Dataset Histórico CRISP-DM (18k registros)"])

    with tab_ops:
        if not tickets:
            st.info("Sin datos en SQLite para los filtros seleccionados.")
        else:
            df_ops = pd.DataFrame(tickets)
            sla_evals = [calculate_sla_status(t) for t in tickets]
            df_ops["semaforo_sla"] = [s["semaphore"] for s in sla_evals]
            df_ops["cumple_sla_vivo"] = [not s["is_breached"] for s in sla_evals]

            c_row1_a, c_row1_b = st.columns(2)

            with c_row1_a:
                # 1. Embudo de Conversión de Estados ITIL
                stage_order = ["Registrado", "Asignado", "En atención", "En espera", "Resuelto", "Cerrado", "Reabierto", "Anulado"]
                counts_map = df_ops["status"].value_counts().to_dict()
                funnel_rows = [
                    {"Estado": st_name, "Tickets": int(counts_map.get(st_name, 0))}
                    for st_name in stage_order
                    if counts_map.get(st_name, 0) > 0
                ]
                df_funnel = pd.DataFrame(funnel_rows)
                fig_funnel = px.funnel(
                    df_funnel,
                    x="Tickets",
                    y="Estado",
                    title="Embudo de Estados ITIL v4",
                    color_discrete_sequence=[UPC_GREEN],
                )
                st.plotly_chart(fig_funnel, use_container_width=True)

            with c_row1_b:
                # 2. Distribución de Carga de Trabajo por Técnico Activo
                workload = ticket_svc.get_technician_workload()
                if workload:
                    df_wl = pd.DataFrame(workload)
                    fig_wl = px.bar(
                        df_wl,
                        x="full_name",
                        y=["open_tickets", "resolved_tickets"],
                        barmode="group",
                        title="Balanceo de Carga Automática por Técnico (RF-06)",
                        labels={"value": "Cantidad de tickets", "full_name": "Técnico", "variable": "Métrica"},
                        color_discrete_sequence=[UPC_SLATE_DARK, UPC_EMERALD],
                    )
                    st.plotly_chart(fig_wl, use_container_width=True)
                else:
                    st.info("Sin técnicos activos registrados para mostrar balanceo de carga.")

            c_row2_a, c_row2_b = st.columns(2)
            with c_row2_a:
                # 3. Tasa de Cumplimiento SLA por Servicio
                sla_svc = (
                    df_ops.groupby("service_name")["cumple_sla_vivo"]
                    .mean()
                    .mul(100)
                    .round(1)
                    .reset_index()
                )
                sla_svc.columns = ["Servicio TIC", "% Cumplimiento SLA"]
                fig_sla_svc = px.bar(
                    sla_svc.sort_values("% Cumplimiento SLA", ascending=True),
                    x="% Cumplimiento SLA",
                    y="Servicio TIC",
                    orientation="h",
                    range_x=[0, 105],
                    title="Tasa de Cumplimiento SLA (%) por Servicio",
                    color_discrete_sequence=[UPC_GREEN],
                )
                st.plotly_chart(fig_sla_svc, use_container_width=True)

            with c_row2_b:
                # 4. Análisis de Satisfacción CSAT
                csat_df = df_ops.dropna(subset=["csat_score"]).copy() if "csat_score" in df_ops.columns else pd.DataFrame()
                if not csat_df.empty:
                    csat_counts = csat_df["csat_score"].astype(int).value_counts().sort_index().reset_index()
                    csat_counts.columns = ["Calificación (1-5)", "Respuestas"]
                    fig_csat = px.bar(
                        csat_counts,
                        x="Calificación (1-5)",
                        y="Respuestas",
                        title="Distribución de Encuestas de Satisfacción CSAT (1–5)",
                        color_discrete_sequence=[UPC_EMERALD],
                    )
                    st.plotly_chart(fig_csat, use_container_width=True)
                else:
                    prio_counts = df_ops["priority"].value_counts().reset_index()
                    prio_counts.columns = ["Prioridad", "Cantidad"]
                    fig_prio = px.pie(
                        prio_counts,
                        names="Prioridad",
                        values="Cantidad",
                        title="Distribución por Prioridad (Matriz OR-03)",
                        color_discrete_sequence=["#DC2626", "#D97706", "#2563EB", "#16A34A"],
                    )
                    st.plotly_chart(fig_prio, use_container_width=True)

            with st.expander("Tabla equivalente accesible de tickets filtrados", expanded=False):
                display_cols = [c for c in ("ticket_number", "title", "service_name", "sede", "priority", "status", "semaforo_sla", "assigned_tech_email", "csat_score") if c in df_ops.columns]
                st.dataframe(df_ops[display_cols], use_container_width=True, hide_index=True)

            if user["role"] in ("coordinador", "director", "admin"):
                st.divider()
                st.subheader("Exportar Reporte de Gestión (RF-23)")
                export_cols = [
                    "ticket_number", "title", "service_name", "area", "sede", "location",
                    "priority", "status", "semaforo_sla", "requester_email",
                    "assigned_tech_email", "created_at", "resolved_at", "csat_score",
                ]
                df_exp = df_ops[[c for c in export_cols if c in df_ops.columns]]
                exp1, exp2, exp3 = st.columns(3)
                with exp1:
                    xlsx_buf = io.BytesIO()
                    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                        meta_df = pd.DataFrame(
                            {
                                "Campo": ["Sistema", "Generado por", "Fecha", "Filtros"],
                                "Valor": [
                                    "CASAGBI - Mesa de Servicios TIC UPC",
                                    user["email"],
                                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    f"Sede={f_sede}, Servicio={f_svc}, Prioridad={f_prio}, Estado={f_status}",
                                ],
                            }
                        )
                        meta_df.to_excel(writer, sheet_name="Encabezado", index=False)
                        df_exp.to_excel(writer, sheet_name="Tickets", index=False)
                    st.download_button(
                        "Descargar XLSX (Excel)",
                        data=xlsx_buf.getvalue(),
                        file_name="reporte_casagbi_upc.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with exp2:
                    st.download_button(
                        "Descargar CSV",
                        data=df_exp.to_csv(index=False).encode("utf-8"),
                        file_name="reporte_casagbi_upc.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with exp3:
                    html_rep = (
                        f"<html><head><meta charset='utf-8'><title>Reporte CASAGBI UPC</title></head>"
                        f"<body style='font-family:Arial,sans-serif;padding:24px;'>"
                        f"<h2 style='color:#006837;'>Reporte Ejecutivo CASAGBI · UPC</h2>"
                        f"<p><strong>Generado por:</strong> {user['email']} | "
                        f"<strong>Total:</strong> {kpis['total_tickets']} | "
                        f"<strong>SLA:</strong> {kpis['sla_compliance_pct']}%</p>"
                        f"{df_exp.to_html(index=False)}</body></html>"
                    )
                    st.download_button(
                        "Descargar Reporte HTML/Imprimible",
                        data=html_rep.encode("utf-8"),
                        file_name="reporte_casagbi_upc.html",
                        mime="text/html",
                        use_container_width=True,
                    )

    with tab_hist:
        df_clean = load_clean_dataset_cached(t_store.cache_version)
        if df_clean.empty:
            st.warning("No se encontró `data/processed/upc_tickets_clean.csv`. Ejecuta el pipeline en el Laboratorio MLOps.")
        else:
            st.caption(f"Dataset analítico procesado con {len(df_clean):,} tickets limpios (lazy-loaded).")
            c_h1, c_h2 = st.columns(2)
            with c_h1:
                sla_sede = (
                    df_clean.groupby("sede")["cumple_sla"]
                    .mean()
                    .mul(100)
                    .round(2)
                    .reset_index()
                )
                sla_sede.columns = ["Sede", "% Cumplimiento SLA"]
                fig_h1 = px.bar(
                    sla_sede,
                    x="Sede",
                    y="% Cumplimiento SLA",
                    title="Cumplimiento SLA (%) por Sede UPC (Histórico 18k)",
                    color_discrete_sequence=[UPC_EMERALD],
                )
                st.plotly_chart(fig_h1, use_container_width=True)
            with c_h2:
                fig_h2 = px.box(
                    df_clean.sample(min(3000, len(df_clean)), random_state=42),
                    x="prioridad",
                    y="tiempo_resolucion_horas",
                    color="prioridad",
                    title="Distribución de Tiempo de Resolución (h) por Prioridad",
                )
                st.plotly_chart(fig_h2, use_container_width=True)
