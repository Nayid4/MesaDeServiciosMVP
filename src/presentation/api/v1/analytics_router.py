"""Router REST v1 de KPIs ejecutivos ITIL v4, Laboratorio MLOps y Auditoría."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from src.application.analytics import (
    ActivateModelCommand,
    ExportKpiReportQuery,
    GetKpiMetricsQuery,
    GetModelComparisonQuery,
    ListAuditLogsQuery,
    TrainModelsCommand,
)
from src.infrastructure.composition import get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analítica KPI y MLOps"])


class SimulateModelsRequest(BaseModel):
    text: str = Field(..., min_length=3)


class TrainModelsRequest(BaseModel):
    n_rows: int = Field(18000, ge=500, le=50000)


class ActivateModelRequest(BaseModel):
    model_id: str = Field(..., min_length=2)


@router.get("/kpis")
def get_kpis(
    sede: Optional[str] = None,
    service_name: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        GetKpiMetricsQuery(
            actor=current_user,
            sede=sede or None,
            service_name=service_name or None,
            priority=priority or None,
            status=status or None,
        )
    )


def _export_report_response(
    *,
    fmt: str,
    request: Request,
    current_user: Dict[str, Any],
    sede: Optional[str],
    service_name: Optional[str],
    priority: Optional[str],
    status: Optional[str],
) -> Response:
    res = get_cqrs_bus().query(
        ExportKpiReportQuery(
            actor=current_user,
            report_format=fmt,
            sede=sede or None,
            service_name=service_name or None,
            priority=priority or None,
            status=status or None,
            ip_address=get_client_ip(request),
        )
    )
    return Response(
        content=res["content_bytes"],
        media_type=res["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{res["filename"]}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/export.csv")
def export_kpis_csv(
    request: Request,
    sede: Optional[str] = None,
    service_name: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    return _export_report_response(
        fmt="csv",
        request=request,
        current_user=current_user,
        sede=sede,
        service_name=service_name,
        priority=priority,
        status=status,
    )


@router.get("/export.pdf")
def export_kpis_pdf(
    request: Request,
    sede: Optional[str] = None,
    service_name: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    return _export_report_response(
        fmt="pdf",
        request=request,
        current_user=current_user,
        sede=sede,
        service_name=service_name,
        priority=priority,
        status=status,
    )


@router.get("/ml/models")
def get_ml_models(
    _current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "director", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetModelComparisonQuery())


@router.post("/ml/simulate")
def simulate_ml_models(
    payload: SimulateModelsRequest,
    _current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "director", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetModelComparisonQuery(simulate_text=payload.text))


@router.post("/ml/train")
def train_ml_models(
    payload: TrainModelsRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        TrainModelsCommand(actor=current_user, n_rows=payload.n_rows, ip_address=get_client_ip(request))
    )


@router.post("/ml/activate")
def activate_ml_model(
    payload: ActivateModelRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        ActivateModelCommand(
            actor=current_user, model_id=payload.model_id, ip_address=get_client_ip(request)
        )
    )


@router.get("/audit-logs")
def list_audit_logs(
    user_email: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 200,
    current_user: Dict[str, Any] = Depends(require_roles(["coordinador", "admin"])),
) -> Dict[str, Any]:
    logs = get_cqrs_bus().query(
        ListAuditLogsQuery(
            actor=current_user,
            user_email=user_email or None,
            action=action or None,
            limit=limit,
        )
    )
    return {"logs": logs}
