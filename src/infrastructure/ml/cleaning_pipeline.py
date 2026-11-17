"""Pipeline CRISP-DM de auditoría, limpieza de datos y feature engineering."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from src.domain.rules import SLA_BY_PRIORITY, UPC_SERVICE_CATALOG

DEFAULT_RAW_PATH = Path("data/raw/upc_tickets_raw.csv")
DEFAULT_CLEAN_PATH = Path("data/processed/upc_tickets_clean.csv")
DEFAULT_EXCLUDED_PATH = Path("data/processed/upc_tickets_excluded.csv")


def clean_tickets_dataset(
    raw_path: Path | str = DEFAULT_RAW_PATH,
    clean_path: Path | str = DEFAULT_CLEAN_PATH,
    excluded_path: Path | str = DEFAULT_EXCLUDED_PATH,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Audita el dataset crudo de tickets UPC, separa anomalías e imputa nulos."""
    raw_file = Path(raw_path)
    clean_file = Path(clean_path)
    excluded_file = Path(excluded_path)
    clean_file.parent.mkdir(parents=True, exist_ok=True)
    excluded_file.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(raw_file, encoding="utf-8")
    total_raw = len(df)

    excluded_chunks = []
    valid_mask = pd.Series(True, index=df.index)

    missing_target = df["servicio_real"].isna() | (~df["servicio_real"].isin(UPC_SERVICE_CATALOG.keys()))
    if missing_target.any():
        chunk = df[missing_target].copy()
        chunk["exclusion_reason"] = "servicio_real faltante o fuera del catálogo UPC"
        excluded_chunks.append(chunk)
        valid_mask &= ~missing_target

    dup_mask = valid_mask & df.duplicated(keep="first")
    if dup_mask.any():
        chunk = df[dup_mask].copy()
        chunk["exclusion_reason"] = "registro_duplicado_exacto"
        excluded_chunks.append(chunk)
        valid_mask &= ~dup_mask

    neg_time_mask = valid_mask & (
        (pd.to_numeric(df["tiempo_respuesta_min"], errors="coerce") < 0)
        | (pd.to_numeric(df["tiempo_resolucion_horas"], errors="coerce") < 0)
        | df["tiempo_respuesta_min"].isna()
        | df["tiempo_resolucion_horas"].isna()
    )
    if neg_time_mask.any():
        chunk = df[neg_time_mask].copy()
        chunk["exclusion_reason"] = "tiempo_operativo_negativo_o_nulo"
        excluded_chunks.append(chunk)
        valid_mask &= ~neg_time_mask

    asunto_str = df["asunto"].fillna("").astype(str).str.strip()
    desc_str = df["descripcion"].fillna("").astype(str).str.strip()
    short_text_mask = valid_mask & ((desc_str.str.len() < 5) | (asunto_str.str.len() < 5))
    if short_text_mask.any():
        chunk = df[short_text_mask].copy()
        chunk["exclusion_reason"] = "texto_insuficiente_menor_5_chars"
        excluded_chunks.append(chunk)
        valid_mask &= ~short_text_mask

    df_clean = df[valid_mask].copy()
    df_excluded = (
        pd.concat(excluded_chunks, ignore_index=True)
        if excluded_chunks
        else pd.DataFrame(columns=list(df.columns) + ["exclusion_reason"])
    )

    null_ubicacion_count = int(df_clean["ubicacion"].isna().sum())
    df_clean["ubicacion_imputada"] = df_clean["ubicacion"].isna()
    if null_ubicacion_count > 0:
        group_modes = (
            df_clean.dropna(subset=["ubicacion"])
            .groupby(["sede", "servicio_real"])["ubicacion"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "Bloque A")
        )

        def _impute_loc(row: pd.Series) -> str:
            if pd.notna(row["ubicacion"]) and str(row["ubicacion"]).strip():
                return str(row["ubicacion"])
            return str(group_modes.get((row["sede"], row["servicio_real"]), "Bloque A"))

        df_clean["ubicacion"] = df_clean.apply(_impute_loc, axis=1)

    df_clean["fecha_creacion_dt"] = pd.to_datetime(df_clean["fecha_creacion"], errors="coerce")
    df_clean["hora_creacion"] = df_clean["fecha_creacion_dt"].dt.hour.fillna(8).astype(int)
    df_clean["dia_semana"] = df_clean["fecha_creacion_dt"].dt.day_name().fillna("Monday")
    df_clean["area_tecnica"] = df_clean["servicio_real"].map(
        lambda s: UPC_SERVICE_CATALOG[s]["area"]
    )
    df_clean["texto_completo"] = (
        df_clean["asunto"].astype(str).str.strip()
        + " | "
        + df_clean["descripcion"].astype(str).str.strip()
    )
    df_clean["longitud_texto"] = df_clean["texto_completo"].str.len()
    df_clean["num_palabras"] = df_clean["texto_completo"].str.split().str.len()
    df_clean["sla_objetivo_horas"] = df_clean["prioridad"].map(
        lambda p: SLA_BY_PRIORITY.get(p, {"sla_resolution_hours": 24.0})["sla_resolution_hours"]
    )
    df_clean["ratio_sla"] = np.round(
        df_clean["tiempo_resolucion_horas"] / df_clean["sla_objetivo_horas"], 3
    )

    df_clean.drop(columns=["fecha_creacion_dt"], inplace=True)

    df_clean.to_csv(clean_file, index=False, encoding="utf-8")
    df_excluded.to_csv(excluded_file, index=False, encoding="utf-8")

    summary = {
        "total_raw": total_raw,
        "total_clean": len(df_clean),
        "total_excluded": len(df_excluded),
        "retention_pct": round((len(df_clean) / max(1, total_raw)) * 100.0, 2),
        "imputed_locations": null_ubicacion_count,
        "exclusion_breakdown": (
            df_excluded["exclusion_reason"].value_counts().to_dict()
            if not df_excluded.empty
            else {}
        ),
    }
    return df_clean, df_excluded, summary
