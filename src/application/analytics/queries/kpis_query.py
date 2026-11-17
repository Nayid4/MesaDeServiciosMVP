"""Consultas CQRS de KPIs operativos ITIL v4 y exportación institucional RIU-10 (CSV/PDF)."""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.analytics.pdf_generator import build_riu10_pdf_report
from src.application.common import Query
from src.domain.exceptions import ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import (
    ALL_TICKET_STATUSES,
    ASSIGNED_LOAD_STATUSES,
    OPEN_TICKET_STATUSES,
    ROLE_LABELS,
    SLA_BY_PRIORITY,
    calculate_sla_status,
    now_bogota,
)
from src.metrics import compute_itil_kpis


@dataclass(frozen=True)
class GetKpiMetricsQuery(Query):
    actor: Dict[str, Any]
    sede: Optional[str] = None
    service_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


@dataclass(frozen=True)
class ExportKpiReportQuery(Query):
    actor: Dict[str, Any]
    report_format: str = "csv"
    sede: Optional[str] = None
    service_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    ip_address: str = "127.0.0.1"


def resolve_scope_for_actor(actor: Dict[str, Any]) -> tuple[Optional[int], Optional[int], str]:
    role = actor.get("role")
    if role == "usuario":
        return int(actor["id"]), None, "Mis solicitudes radicadas (RF-22)"
    if role == "tecnico":
        return None, int(actor["id"]), "Mis tickets asignados (RF-22)"
    return None, None, "Alcance institucional completo UPC (RF-22)"


class GetKpiMetricsQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetKpiMetricsQuery) -> Dict[str, Any]:
        requester_id, assigned_tech_id, scope_label = resolve_scope_for_actor(query.actor)
        with self._uow_factory() as uow:
            tickets = uow.tickets.list_tickets(
                requester_id=requester_id,
                assigned_tech_id=assigned_tech_id,
                sede=query.sede,
                service_name=query.service_name,
                priority=query.priority,
                status=query.status,
                limit=1000,
            )
            techs = uow.users.list_users(role="tecnico", is_active=True)

        kpis = compute_itil_kpis(tickets)
        kpis["csat_count"] = sum(1 for t in tickets if t.get("csat_score") is not None)
        by_service = dict(Counter(t["service_name"] for t in tickets))
        by_priority = {p: 0 for p in SLA_BY_PRIORITY.keys()}
        open_by_priority = {p: 0 for p in SLA_BY_PRIORITY.keys()}
        by_status = {s: 0 for s in ALL_TICKET_STATUSES}
        for t in tickets:
            by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
            if t.get("status") in OPEN_TICKET_STATUSES:
                open_by_priority[t["priority"]] = open_by_priority.get(t["priority"], 0) + 1

        service_breakdown = [
            {
                "service_name": svc_name,
                "received": rec_cnt,
                "resolved": sum(
                    1
                    for t in tickets
                    if t.get("service_name") == svc_name and t.get("status") in ("Resuelto", "Cerrado")
                ),
            }
            for svc_name, rec_cnt in by_service.items()
        ]
        csat_dist = {str(star): 0 for star in range(1, 6)}
        for t in tickets:
            if t.get("csat_score") is not None:
                key = str(int(t["csat_score"]))
                csat_dist[key] = csat_dist.get(key, 0) + 1

        workload = []
        for tech in techs:
            tech_tickets = [t for t in tickets if t.get("assigned_tech_id") == tech["id"]]
            workload.append(
                {
                    "tech_id": tech["id"],
                    "email": tech["email"],
                    "full_name": tech["full_name"],
                    "area": tech.get("area"),
                    "sede": tech.get("sede"),
                    "open_tickets": sum(1 for t in tech_tickets if t["status"] in ASSIGNED_LOAD_STATUSES),
                    "resolved_tickets": sum(1 for t in tech_tickets if t["status"] in ("Resuelto", "Cerrado")),
                }
            )

        priority_rank = {"P1 Crítica": 1, "P2 Alta": 2, "P3 Media": 3, "P4 Baja": 4}
        open_sorted = sorted(
            [t for t in tickets if t.get("status") in OPEN_TICKET_STATUSES],
            key=lambda t: (priority_rank.get(t.get("priority", ""), 9), str(t.get("resolution_deadline") or "9999")),
        )
        recent_pool = open_sorted[:6] if open_sorted else tickets[:6]
        recent_attention_tickets = [
            {
                "id": t["id"],
                "ticket_number": t["ticket_number"],
                "title": t["title"],
                "service_name": t["service_name"],
                "requester_email": t.get("requester_email"),
                "sede": t.get("sede"),
                "location": t.get("location"),
                "priority": t["priority"],
                "status": t["status"],
                "assigned_tech_email": t.get("assigned_tech_email"),
                "sla_status": calculate_sla_status(t),
            }
            for t in recent_pool
        ]

        return {
            "scope_label": scope_label,
            "kpis": kpis,
            "by_service": by_service,
            "service_breakdown": service_breakdown,
            "by_priority": by_priority,
            "open_by_priority": open_by_priority,
            "by_status": by_status,
            "csat_distribution": csat_dist,
            "technician_workload": workload,
            "recent_attention_tickets": recent_attention_tickets,
        }


class ExportKpiReportQueryHandler:
    """Genera informes ejecutivos CSV o PDF bajo formato institucional RIU-10 y alcance RBAC (RF-22)."""

    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: ExportKpiReportQuery) -> Dict[str, Any]:
        fmt = (query.report_format or "csv").strip().lower()
        if fmt not in ("csv", "pdf"):
            raise ValidationDomainError("Formato de reporte no soportado. Use 'csv' o 'pdf'.")

        requester_id, assigned_tech_id, scope_label = resolve_scope_for_actor(query.actor)
        with self._uow_factory() as uow:
            tickets = uow.tickets.list_tickets(
                requester_id=requester_id,
                assigned_tech_id=assigned_tech_id,
                sede=query.sede,
                service_name=query.service_name,
                priority=query.priority,
                status=query.status,
                limit=1000,
            )
            kpis = compute_itil_kpis(tickets)
            filters_parts = [
                f"{k}={v}"
                for k, v in (
                    ("Sede", query.sede),
                    ("Servicio", query.service_name),
                    ("Prioridad", query.priority),
                    ("Estado", query.status),
                )
                if v
            ]
            meta = {
                "format": "RIU-10",
                "generated_at": now_bogota().strftime("%Y-%m-%d %H:%M COT"),
                "actor_name": query.actor.get("full_name") or query.actor.get("email"),
                "actor_role": ROLE_LABELS.get(query.actor.get("role", ""), query.actor.get("role", "")),
                "scope_label": scope_label,
                "filters_summary": ", ".join(filters_parts) if filters_parts else "Sin filtros adicionales",
            }
            if fmt == "csv":
                content_bytes = _build_csv_report(meta, kpis, tickets)
                media_type = "text/csv; charset=utf-8"
                filename = "informe_casagbi_riu10.csv"
            else:
                content_bytes = build_riu10_pdf_report(meta=meta, kpis=kpis, tickets=tickets)
                media_type = "application/pdf"
                filename = "informe_casagbi_riu10.pdf"

            uow.audit_logs.append(
                {
                    "user_email": query.actor["email"],
                    "ip_address": query.ip_address,
                    "action": f"REPORT_EXPORTED_{fmt.upper()}",
                    "entity": "analytics_reports",
                    "entity_id": filename,
                    "new_value": f"Total={len(tickets)} | {meta['filters_summary']}",
                }
            )
            uow.commit()

        return {"content_bytes": content_bytes, "media_type": media_type, "filename": filename}


def _build_csv_report(meta: Dict[str, Any], kpis: Dict[str, Any], tickets: list[Dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["CASAGBI - UNIVERSIDAD POPULAR DEL CESAR", "FORMATO OFICIAL RIU-10"])
    writer.writerow(["Fecha de generacion", meta["generated_at"]])
    writer.writerow(["Generado por", f"{meta['actor_name']} ({meta['actor_role']})"])
    writer.writerow(["Alcance (RF-22)", meta["scope_label"]])
    writer.writerow(["Filtros aplicados", meta["filters_summary"]])
    writer.writerow([])
    writer.writerow(["INDICADORES KPI", "VALOR"])
    writer.writerow(["Total de tickets", kpis["total_tickets"]])
    writer.writerow(["Tickets abiertos", kpis["open_tickets"]])
    writer.writerow(["Resueltos o cerrados", kpis["resolved_or_closed"]])
    writer.writerow(["Cumplimiento SLA (%)", kpis["sla_compliance_pct"]])
    writer.writerow(["Primera respuesta promedio (min)", kpis["avg_first_response_min"]])
    writer.writerow(["Resolucion promedio (h)", kpis["avg_resolution_hours"]])
    writer.writerow(["CSAT promedio (1-5)", kpis["avg_csat"]])
    writer.writerow(["Tasa de reapertura (%)", kpis["reopen_rate_pct"]])
    writer.writerow([])
    writer.writerow(["Radicado", "Asunto", "Servicio", "Sede", "Ubicacion", "Prioridad", "Estado", "Tecnico", "Creado"])
    for t in tickets:
        writer.writerow(
            [
                t.get("ticket_number", ""),
                t.get("title", ""),
                t.get("service_name", ""),
                t.get("sede", ""),
                t.get("location", ""),
                t.get("priority", ""),
                t.get("status", ""),
                t.get("assigned_tech_email") or "Sin asignar",
                t.get("created_at", ""),
            ]
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
