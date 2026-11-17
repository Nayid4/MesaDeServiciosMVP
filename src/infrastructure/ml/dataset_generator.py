"""Generador de dataset sintético realista de tickets TIC para la UPC (18,000 registros)."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from src.domain.rules import (
    SLA_BY_PRIORITY,
    UPC_LOCATIONS,
    UPC_SEDES,
    UPC_SERVICE_CATALOG,
    calculate_priority_or03,
    format_ticket_number,
)
from src.infrastructure.ml.dataset_templates import (
    COLOQUIAL_NOISE,
    CROSS_SERVICE_CONTEXT,
    REQUESTER_ROLES,
    REQUESTER_WEIGHTS,
    SEDE_WEIGHTS,
    SERVICE_TEMPLATES,
    TECHNICIANS_BY_AREA,
    URGENCY_CONTEXT,
)

DEFAULT_RAW_PATH = Path("data/raw/upc_tickets_raw.csv")


def generate_synthetic_dataset(
    n_rows: int = 18000,
    output_path: Path | str = DEFAULT_RAW_PATH,
    seed: int = 42,
) -> pd.DataFrame:
    """Genera dataset sintético realista UPC con anomalías controladas CRISP-DM."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    n_duplicates = max(1, int(round(n_rows * 0.008)))
    n_base = n_rows - n_duplicates
    services = list(UPC_SERVICE_CATALOG.keys())
    service_weights = [0.24, 0.22, 0.19, 0.13, 0.13, 0.09]
    start_date = datetime(2025, 1, 15, 7, 0, 0)
    records: List[Dict[str, object]] = []

    for idx in range(1, n_base + 1):
        service = rng.choices(services, weights=service_weights, k=1)[0]
        svc_meta = UPC_SERVICE_CATALOG[service]
        impact = svc_meta["base_impact"] if rng.random() < 0.84 else rng.choice(["Alto", "Medio", "Bajo"])
        urgency = rng.choices(["Alta", "Media", "Baja"], weights=[0.28, 0.44, 0.28], k=1)[0]
        prio_info = calculate_priority_or03(impact, urgency)
        priority = prio_info["priority"]
        sla_res_h = prio_info["sla_resolution_hours"]

        sede = rng.choices(UPC_SEDES, weights=SEDE_WEIGHTS, k=1)[0]
        ubicacion = rng.choice(UPC_LOCATIONS)
        rol_solicitante = rng.choices(REQUESTER_ROLES, weights=REQUESTER_WEIGHTS, k=1)[0]

        tipo_caso = svc_meta["default_type"]
        if service == "Software y Licenciamiento" and rng.random() < 0.25:
            tipo_caso = "Incidencia"
        elif service == "Correo Institucional y Cuentas" and rng.random() < 0.42:
            tipo_caso = "Incidencia"

        tpl = SERVICE_TEMPLATES[service]
        asunto = rng.choice(tpl["subjects"]).format(ubicacion=ubicacion, sede=sede)
        sintoma = rng.choice(tpl["symptoms"]).format(ubicacion=ubicacion, sede=sede)
        if rng.random() < 0.45:
            sintoma = f"{sintoma} {rng.choice(CROSS_SERVICE_CONTEXT[service])}"

        text_urgency = urgency if rng.random() >= 0.05 else rng.choice(["Alta", "Media", "Baja"])
        urg_nota = rng.choice(URGENCY_CONTEXT[text_urgency])
        colloquial = rng.choice(COLOQUIAL_NOISE) if rng.random() < 0.40 else ""

        if rng.random() < 0.22:
            asunto = rng.choice(
                [
                    f"Solicitud de soporte técnico urgente en {ubicacion}",
                    f"Problema tecnológico reportado en {sede}",
                    f"Inconveniente con servicio institucional en {ubicacion}",
                    f"Falla reportada por {rol_solicitante.lower()} en {ubicacion}",
                ]
            )

        descripcion = (
            f"{sintoma} Reportado por {rol_solicitante.lower()} en {ubicacion} ({sede}). "
            f"{urg_nota} {colloquial}".strip()
        )
        reported_service = (
            service if rng.random() >= 0.025 else rng.choice([s for s in services if s != service])
        )
        day_offset = int(np_rng.integers(0, 600))
        hour = int(rng.choices(range(7, 20), weights=[2, 4, 6, 7, 7, 5, 4, 6, 6, 5, 4, 3, 2], k=1)[0])
        minute = int(np_rng.integers(0, 60))
        fecha_creacion = (start_date + timedelta(days=day_offset, hours=hour - 7, minutes=minute)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        tech = rng.choice(TECHNICIANS_BY_AREA[UPC_SERVICE_CATALOG[reported_service]["area"]])
        sede_factor = 1.0 if "Sabanas" in sede else (1.12 if "Hurtado" in sede else 1.25)
        resp_target_min = SLA_BY_PRIORITY[priority]["sla_response_hours"] * 60.0
        tiempo_resp_min = round(
            float(np.clip(np_rng.gamma(shape=2.2, scale=resp_target_min * 0.28 * sede_factor), 2.0, resp_target_min * 1.9)),
            1,
        )
        tiempo_res_horas = round(
            float(np.clip(np_rng.gamma(shape=2.4, scale=sla_res_h * 0.36 * sede_factor), 0.25, sla_res_h * 1.65)),
            2,
        )
        cumple_sla = bool(tiempo_res_horas <= sla_res_h)
        csat = int(np.clip(round(float(np_rng.normal(loc=4.5 if cumple_sla else 2.9, scale=0.7))), 1, 5))

        records.append(
            {
                "ticket_id": format_ticket_number(idx, year=2026),
                "fecha_creacion": fecha_creacion,
                "rol_solicitante": rol_solicitante,
                "sede": sede,
                "ubicacion": ubicacion,
                "asunto": asunto,
                "descripcion": descripcion,
                "tipo_caso": tipo_caso,
                "servicio_real": reported_service,
                "impacto": impact,
                "urgencia": urgency,
                "prioridad": priority,
                "tecnico_asignado": tech,
                "tiempo_respuesta_min": tiempo_resp_min,
                "tiempo_resolucion_horas": tiempo_res_horas,
                "cumple_sla": cumple_sla,
                "satisfaccion": csat,
            }
        )

    df = pd.DataFrame(records)
    n_null_loc = int(round(n_rows * 0.011))
    n_short_txt = int(round(n_rows * 0.005))
    n_neg_outliers = int(round(n_rows * 0.006))

    all_indices = list(range(len(df)))
    rng.shuffle(all_indices)
    df.loc[all_indices[:n_null_loc], "ubicacion"] = np.nan
    for i in all_indices[n_null_loc : n_null_loc + n_short_txt]:
        df.loc[i, "asunto"] = rng.choice(["ayuda", "mal", "ok", "??"])
        df.loc[i, "descripcion"] = rng.choice(["hola", "no", "x", "malo"])
    for i in all_indices[n_null_loc + n_short_txt : n_null_loc + n_short_txt + n_neg_outliers]:
        if rng.random() < 0.5:
            df.loc[i, "tiempo_respuesta_min"] = -round(rng.uniform(5.0, 60.0), 1)
        else:
            df.loc[i, "tiempo_resolucion_horas"] = -round(rng.uniform(1.0, 15.0), 2)

    dup_start = n_null_loc + n_short_txt + n_neg_outliers
    dup_rows = df.iloc[all_indices[dup_start : dup_start + n_duplicates]].copy()
    df_final = pd.concat([df, dup_rows], ignore_index=True)
    df_final.to_csv(output_file, index=False, encoding="utf-8")
    return df_final


if __name__ == "__main__":
    generated = generate_synthetic_dataset()
    print(f"Dataset sintético generado: {len(generated)} registros en {DEFAULT_RAW_PATH}")
