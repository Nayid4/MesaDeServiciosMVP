"""Métricas operativas ITIL v4 y métricas predictivas/estadísticas para evaluación IA."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from src.domain.rules import OPEN_TICKET_STATUSES, calculate_sla_status


def compute_itil_kpis(tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula KPIs operativos ITIL v4 a partir de los tickets persistidos en SQLite."""
    if not tickets:
        return {
            "total_tickets": 0,
            "open_tickets": 0,
            "resolved_or_closed": 0,
            "sla_compliance_pct": 100.0,
            "avg_resolution_hours": 0.0,
            "avg_first_response_min": 0.0,
            "reopen_rate_pct": 0.0,
            "avg_csat": 0.0,
            "breached_open_count": 0,
            "at_risk_open_count": 0,
        }

    total = len(tickets)
    open_tickets = [t for t in tickets if t.get("status") in OPEN_TICKET_STATUSES]
    resolved_closed = [t for t in tickets if t.get("status") in ("Resuelto", "Cerrado")]

    sla_statuses = [calculate_sla_status(t) for t in tickets]
    evaluated_for_sla = [
        (t, s) for t, s in zip(tickets, sla_statuses) if t.get("status") != "Anulado"
    ]
    compliant = [s for _, s in evaluated_for_sla if not s["is_breached"]]
    sla_pct = round((len(compliant) / max(1, len(evaluated_for_sla))) * 100.0, 1)

    breached_open = sum(
        1 for t, s in zip(tickets, sla_statuses) if t.get("status") in OPEN_TICKET_STATUSES and s["is_breached"]
    )
    at_risk_open = sum(
        1
        for t, s in zip(tickets, sla_statuses)
        if t.get("status") in OPEN_TICKET_STATUSES and s["semaphore"] == "Amarillo"
    )

    res_hours = []
    for t in resolved_closed:
        if t.get("created_at") and t.get("resolved_at"):
            try:
                c = pd.to_datetime(t["created_at"])
                r = pd.to_datetime(t["resolved_at"])
                hrs = max(0.05, (r - c).total_seconds() / 3600.0 - (t.get("paused_seconds", 0) / 3600.0))
                res_hours.append(hrs)
            except Exception:
                pass

    resp_mins = []
    for t in tickets:
        if t.get("created_at") and t.get("first_response_at"):
            try:
                c = pd.to_datetime(t["created_at"])
                f = pd.to_datetime(t["first_response_at"])
                mins = max(1.0, (f - c).total_seconds() / 60.0)
                resp_mins.append(mins)
            except Exception:
                pass

    reopened_count = sum(1 for t in tickets if t.get("status") == "Reabierto")
    csat_values = [float(t["csat_score"]) for t in tickets if t.get("csat_score") is not None]

    return {
        "total_tickets": total,
        "open_tickets": len(open_tickets),
        "resolved_or_closed": len(resolved_closed),
        "sla_compliance_pct": sla_pct,
        "avg_resolution_hours": round(float(np.mean(res_hours)), 2) if res_hours else 0.0,
        "avg_first_response_min": round(float(np.mean(resp_mins)), 1) if resp_mins else 0.0,
        "reopen_rate_pct": round((reopened_count / max(1, total)) * 100.0, 1),
        "avg_csat": round(float(np.mean(csat_values)), 2) if csat_values else 0.0,
        "breached_open_count": breached_open,
        "at_risk_open_count": at_risk_open,
    }


def compute_classification_metrics(
    y_true: Any,
    y_pred: Any,
    labels: List[str],
) -> Dict[str, Any]:
    """Calcula métricas predictivas estándar separadas de las métricas del software."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "labels": labels,
        "confusion_matrix": cm.tolist(),
    }


def compute_eta_squared(df: pd.DataFrame, group_col: str, target_col: str) -> float:
    """Calcula Eta-cuadrado (ANOVA unidireccional) para medir fuerza de relación categórico -> numérico."""
    clean = df[[group_col, target_col]].dropna()
    if clean.empty or clean[group_col].nunique() < 2:
        return 0.0
    grand_mean = clean[target_col].mean()
    ss_total = float(((clean[target_col] - grand_mean) ** 2).sum())
    if ss_total <= 0:
        return 0.0
    ss_between = 0.0
    for _, grp in clean.groupby(group_col):
        ss_between += len(grp) * float((grp[target_col].mean() - grand_mean) ** 2)
    return round(ss_between / ss_total, 4)


def compute_cramers_v(df: pd.DataFrame, col_a: str, col_b: str) -> float:
    """Calcula V de Cramér (chi-cuadrado normalizada) entre dos variables categóricas."""
    ct = pd.crosstab(df[col_a], df[col_b])
    n = int(ct.values.sum())
    if n == 0 or min(ct.shape) <= 1:
        return 0.0
    row_sums = ct.sum(axis=1).values[:, None]
    col_sums = ct.sum(axis=0).values[None, :]
    expected = (row_sums @ col_sums) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(expected > 0, ((ct.values - expected) ** 2) / expected, 0.0))
    phi2 = chi2 / n
    r, k = ct.shape
    return round(float(np.sqrt(phi2 / max(1, min(k - 1, r - 1)))), 4)
