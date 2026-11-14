"""Laboratorio MLOps: 18,000 registros, 5-Fold CV, explicabilidad Top-15 y simulador 4 modelos."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.shared.components import (
    render_breadcrumbs,
    render_kpi_card,
    render_section_header,
)
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import (
    LifecycleManager,
    StoreManager,
    get_lazy_ai_service,
    load_clean_dataset_cached,
    load_excluded_dataset_cached,
)
from dashboard.shared.styles import UPC_EMERALD, UPC_GREEN, UPC_SLATE_DARK


def render() -> None:
    auth = StoreManager.auth()
    t_store = StoreManager.tickets()
    user = auth.user
    assert user is not None

    ai_svc = get_lazy_ai_service()

    render_breadcrumbs(["Workspace", "Laboratorio MLOps (IA)"])
    render_section_header(
        "Laboratorio MLOps: Pertinencia, Validación 5-Fold y Despliegue de IA",
        "Evaluación estadística de 4 arquitecturas sobre 18,000 tickets (separación explícita entre métricas de software y métricas predictivas IA).",
        icon_name="flask",
    )

    col_retrain, col_info = st.columns([1.45, 2.55])
    with col_retrain:
        can_manage_ml = user["role"] in ("admin", "coordinador")
        if st.button(
            "Ejecutar Pipeline CRISP-DM + Entrenar 4 Modelos (18k)",
            type="primary",
            disabled=not can_manage_ml,
            use_container_width=True,
            key="ml_retrain_btn",
        ):
            with st.spinner("Generando 18,000 tickets, limpiando anomalías y evaluando 4 arquitecturas con 5-Fold CV..."):
                res = ai_svc.run_full_retraining_pipeline(actor_email=user["email"], n_rows=18000)
                LifecycleManager.invalidate_caches(clear_data=True, clear_ai_model=True)
                st.success(
                    f"Pipeline completado: {res['clean_stats']['total_clean']:,} limpios | "
                    f"{res['clean_stats']['total_excluded']:,} excluidos | "
                    f"Activo: `{res['registry']['active_model_id']}`"
                )
                st.rerun()

    registry = ai_svc.get_registry()
    if not registry:
        st.warning("No hay modelos registrados en `models/model_registry.json`. Ejecuta el entrenamiento.")
        return

    df_clean = load_clean_dataset_cached(t_store.cache_version)
    df_excl = load_excluded_dataset_cached(t_store.cache_version)

    with col_info:
        st.markdown(
            f"""<div class="upc-card-accent">
<div style="font-size:0.86rem;font-weight:700;color:{UPC_GREEN};display:flex;align-items:center;gap:0.4rem;">
{svg_icon('sparkles', size=16, color=UPC_GREEN)}<span>Estado Actual de Producción</span>
</div>
<div style="font-size:0.92rem;color:{UPC_SLATE_DARK};margin-top:0.3rem;">
<strong>Modelo Activo:</strong> <code>{registry['active_model_id']}</code> ·
<strong>Dataset limpio:</strong> {len(df_clean):,} filas ·
<strong>Excluidos CRISP-DM:</strong> {len(df_excl):,} filas ·
<strong>Ganancia F1 vs Baseline:</strong> +{registry.get('f1_gain_vs_baseline_pct', 0):.2f} pts
</div>
</div>""",
            unsafe_allow_html=True,
        )

    models = registry["models"]
    active_meta = next((m for m in models if m["model_id"] == registry["active_model_id"]), models[0])

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card(
            "Accuracy (Activo)",
            f"{active_meta['accuracy'] * 100:.2f}%",
            active_meta["display_name"],
            delta=f"Test: {registry['test_rows']:,} casos",
            icon_name="award",
        )
    with k2:
        cv_mean_pct = active_meta.get("cv_f1_mean", active_meta["f1_macro"]) * 100
        cv_std_pct = active_meta.get("cv_f1_std", 0.0) * 100
        render_kpi_card(
            "F1-Score Macro",
            f"{active_meta['f1_macro'] * 100:.2f}%",
            f"5-Fold CV: {cv_mean_pct:.2f}% (±{cv_std_pct:.2f})",
            delta=f"+{registry.get('f1_gain_vs_baseline_pct', 0):.2f} pts vs Reglas",
            icon_name="chart-bar",
        )
    with k3:
        render_kpi_card(
            "Latencia Inferencia",
            f"{active_meta['latency_ms']:.4f} ms",
            "Tiempo promedio por ticket",
            delta=f"Train: {active_meta['train_seconds']}s",
            icon_name="clock",
        )
    with k4:
        render_kpi_card(
            "Urgencia Auxiliar F1",
            f"{registry.get('urgency_f1_macro', 0) * 100:.2f}%",
            "Detección Alta / Media / Baja",
            delta="Matriz OR-03 asistida",
            icon_name="sliders",
        )

    st.subheader("Comparativa de las 4 Arquitecturas (Validación Cruzada 5-Fold + Hold-out Test)")
    df_comp = pd.DataFrame(
        [
            {
                "Estado": "ACTIVO" if m["model_id"] == registry["active_model_id"] else "Disponible",
                "Tipo": "Baseline Reglas" if m.get("is_baseline") else "IA Supervisada",
                "Modelo": m["display_name"],
                "5-Fold CV F1 (%)": round(m.get("cv_f1_mean", m["f1_macro"]) * 100, 2),
                "CV Desv. (±%)": round(m.get("cv_f1_std", 0.0) * 100, 2),
                "Accuracy (%)": round(m["accuracy"] * 100, 2),
                "Precision Macro (%)": round(m["precision_macro"] * 100, 2),
                "Recall Macro (%)": round(m["recall_macro"] * 100, 2),
                "F1-Score Macro (%)": round(m["f1_macro"] * 100, 2),
                "Entrenamiento (s)": m["train_seconds"],
                "Latencia (ms/ticket)": m["latency_ms"],
            }
            for m in models
        ]
    )
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    c_chart, c_cm = st.columns(2)
    with c_chart:
        fig_bar = px.bar(
            df_comp,
            x="Modelo",
            y=["5-Fold CV F1 (%)", "F1-Score Macro (%)", "Accuracy (%)"],
            barmode="group",
            title="Comparativa 5-Fold CV vs Test Hold-Out (%)",
            color_discrete_sequence=["#0F172A", UPC_GREEN, UPC_EMERALD],
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_cm:
        sel_cm_id = st.selectbox(
            "Matriz de Confusión del modelo:",
            [m["model_id"] for m in models],
            index=[m["model_id"] for m in models].index(registry["active_model_id"]),
            format_func=lambda mid: next(m["display_name"] for m in models if m["model_id"] == mid),
            key="ml_cm_select",
        )
        sel_meta = next(m for m in models if m["model_id"] == sel_cm_id)
        labels = sel_meta["labels"]
        short_labels = [lbl.split("(")[0].strip()[:22] for lbl in labels]
        fig_cm = px.imshow(
            sel_meta["confusion_matrix"],
            x=short_labels,
            y=short_labels,
            text_auto=True,
            color_continuous_scale="Greens",
            title=f"Matriz de Confusión · {sel_meta['display_name']}",
        )
        fig_cm.update_xaxes(title="Predicho")
        fig_cm.update_yaxes(title="Real")
        st.plotly_chart(fig_cm, use_container_width=True)

    st.success(
        f"**Justificación de Pertinencia IA vs Alternativa Sencilla:** {active_meta['rationale']} "
        f"En el conjunto de prueba estratificado ({registry['test_rows']:,} tickets) y validación cruzada "
        f"{registry.get('cv_folds', 5)}-Fold, el modelo activo obtiene **F1-Score = {active_meta['f1_macro']*100:.2f}%** "
        f"superando al baseline de reglas simples por **+{registry.get('f1_gain_vs_baseline_pct', 0):.2f} puntos porcentuales**."
    )

    # Top 15 Palabras Clave más Predictivas por Categoría
    top_kw_map = registry.get("top_keywords_per_service", {})
    if top_kw_map:
        st.divider()
        st.subheader("Explicabilidad NLP: Top 15 Palabras Clave Más Predictivas por Servicio")
        sel_svc_kw = st.selectbox(
            "Seleccione un servicio del catálogo para inspeccionar pesos TF-IDF:",
            list(top_kw_map.keys()),
            key="ml_kw_svc_select",
        )
        kw_rows = top_kw_map[sel_svc_kw]
        df_kw = pd.DataFrame(kw_rows)
        c_kw_chart, c_kw_tbl = st.columns([1.6, 1.0])
        with c_kw_chart:
            fig_kw = px.bar(
                df_kw.sort_values("weight", ascending=True),
                x="weight",
                y="term",
                orientation="h",
                title=f"Top 15 términos predictores para '{sel_svc_kw}'",
                color_discrete_sequence=[UPC_GREEN],
            )
            fig_kw.update_xaxes(title="Peso coeficiente Logistic Regression")
            fig_kw.update_yaxes(title="Unigrama / Bigrama TF-IDF")
            st.plotly_chart(fig_kw, use_container_width=True)
        with c_kw_tbl:
            st.dataframe(
                df_kw.rename(columns={"term": "Término / Bigrama", "weight": "Peso Predictivo"}),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    col_test, col_act = st.columns([1.85, 1.15])

    with col_test:
        st.subheader("Simulador de Inferencia en Vivo Lado a Lado (4 Modelos)")
        sample_txt = st.text_input(
            "Ingrese un caso de soporte para comparar los 4 modelos simultáneamente",
            value="El Wi-Fi funciona bien en el PC pero el Vortal arroja error 500 al subir calificaciones en Bloque C",
            key="ml_live_test_txt",
        )
        if st.button("Evaluar los 4 Modelos Lado a Lado", type="primary", key="ml_live_test_btn"):
            try:
                side_results = ai_svc.predict_side_by_side(sample_txt)
                df_side = pd.DataFrame(
                    [
                        {
                            "Modelo": ("[ACTIVO] " if r["is_active"] else "") + r["display_name"],
                            "Tipo": "Baseline Reglas" if r["is_baseline"] else "IA Supervisada",
                            "Servicio Predicho": r["predicted_service"],
                            "Confianza (%)": r["confidence_pct"],
                            "Latencia (ms)": r["latency_ms"],
                        }
                        for r in side_results
                    ]
                )
                st.dataframe(df_side, use_container_width=True, hide_index=True)

                card_cols = st.columns(2)
                for i, r in enumerate(side_results):
                    with card_cols[i % 2]:
                        top3_html = "".join(
                            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;color:#475569;'>"
                            f"<span>{item['service'][:30]}</span><strong>{item['probability_pct']}%</strong></div>"
                            for item in r["top_3_probabilities"]
                        )
                        active_tag = "<span class='badge-pill badge-green'>ACTIVO</span>" if r["is_active"] else ""
                        st.markdown(
                            f"""<div class="upc-card">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.35rem;">
<strong style="font-size:0.9rem;color:{UPC_SLATE_DARK};">{r['display_name']}</strong>
{active_tag}
</div>
<div style="font-size:0.86rem;font-weight:700;color:{UPC_GREEN};margin-bottom:0.4rem;">
{r['predicted_service']} ({r['confidence_pct']}%)
</div>
{top3_html}
</div>""",
                            unsafe_allow_html=True,
                        )
            except Exception as exc:
                st.error(str(exc))

    with col_act:
        st.subheader("Activar Modelo en Producción")
        model_choice = st.selectbox(
            "Seleccionar modelo candidato",
            [m["model_id"] for m in models],
            index=[m["model_id"] for m in models].index(registry["active_model_id"]),
            format_func=lambda mid: next(m["display_name"] for m in models if m["model_id"] == mid),
            key="ml_activate_sel",
        )
        if st.button(
            "Activar Modelo en Producción",
            type="primary",
            disabled=not can_manage_ml,
            use_container_width=True,
            key="ml_activate_btn",
        ):
            ai_svc.activate_model(actor_email=user["email"], model_id=model_choice)
            LifecycleManager.invalidate_caches(clear_data=False, clear_ai_model=True)
            st.success(f"Modelo `{model_choice}` activado en producción y auditado.")
            st.rerun()

    if not df_excl.empty:
        with st.expander(f"Auditoría de Exclusiones CRISP-DM ({len(df_excl):,} registros excluidos)", expanded=False):
            st.dataframe(df_excl["exclusion_reason"].value_counts().reset_index(), use_container_width=True, hide_index=True)
            st.dataframe(df_excl.head(50), use_container_width=True, hide_index=True)
