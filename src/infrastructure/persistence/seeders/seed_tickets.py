"""Seeder idempotente de tickets iniciales, bitácora, contadores y chat demo."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.rules import (
    UPC_SERVICE_CATALOG,
    add_business_hours,
    calculate_priority_or03,
    compute_content_dedup_hash,
    format_ticket_number,
    get_service_prefix,
    now_bogota,
)
from src.infrastructure.persistence.models import (
    AuditLogORM,
    TicketAuditEventORM,
    TicketCounterORM,
    TicketMessageORM,
    TicketORM,
    UserORM,
)

SAMPLE_TICKETS: List[Dict[str, Any]] = [
    {
        "seq": 1,
        "title": "Caída total de red Wi-Fi Eduroam en Bloque B",
        "description": "Ningún estudiante ni docente logra conectarse a Eduroam en el segundo piso del Bloque B. Impide clase práctica en curso.",
        "service_name": "Conectividad y Redes Wi-Fi",
        "sede": "Sede Sabanas (Valledupar)",
        "location": "Bloque B",
        "urgency": "Alta",
        "status": "En atención",
        "requester_email": "docente@unicesar.edu.co",
        "tech_email": "tecnico1@unicesar.edu.co",
        "hours_ago": 1.2,
        "first_resp_mins": 14,
        "diagnosis": None,
        "solution": None,
        "csat_score": None,
    },
    {
        "seq": 2,
        "title": "Error 500 al registrar notas parciales en Vortal",
        "description": "Al guardar las notas del grupo 02 en Vortal académico aparece error de servidor y cierra la sesión.",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "sede": "Sede Sabanas (Valledupar)",
        "location": "Bloque A",
        "urgency": "Alta",
        "status": "Asignado",
        "requester_email": "docente@unicesar.edu.co",
        "tech_email": "tecnico2@unicesar.edu.co",
        "hours_ago": 0.6,
        "first_resp_mins": None,
        "diagnosis": None,
        "solution": None,
        "csat_score": None,
    },
    {
        "seq": 3,
        "title": "Videoproyector sin señal HDMI en aula 204",
        "description": "Al conectar el portátil al módulo de piso HDMI el proyector indica Sin Señal. Hay alternativa usando televisor auxiliar.",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "sede": "Sede Hurtado (Valledupar)",
        "location": "Bloque C",
        "urgency": "Media",
        "status": "En espera",
        "requester_email": "docente@unicesar.edu.co",
        "tech_email": "tecnico4@unicesar.edu.co",
        "hours_ago": 5.0,
        "first_resp_mins": 25,
        "diagnosis": None,
        "solution": None,
        "csat_score": None,
    },
    {
        "seq": 4,
        "title": "Desbloqueo de cuenta institucional @unicesar.edu.co",
        "description": "Mi correo quedó bloqueado después de cambiar el celular y no recibo el código MFA para ingresar.",
        "service_name": "Correo Institucional y Cuentas",
        "sede": "Sede Sabanas (Valledupar)",
        "location": "Biblioteca",
        "urgency": "Media",
        "status": "Resuelto",
        "requester_email": "estudiante@unicesar.edu.co",
        "tech_email": "tecnico3@unicesar.edu.co",
        "hours_ago": 10.0,
        "first_resp_mins": 18,
        "diagnosis": "Token MFA vinculado a dispositivo anterior extraviado por el estudiante.",
        "solution": "Se validó identidad institucional y se restableció el segundo factor MFA enviando enlace temporal al correo alterno.",
        "csat_score": None,
    },
    {
        "seq": 5,
        "title": "Instalación de SPSS y RStudio en Laboratorio 3",
        "description": "Se solicita instalar SPSS versión 29 y RStudio en 25 equipos para talleres de estadística de la próxima semana.",
        "service_name": "Software y Licenciamiento",
        "sede": "Seccional Aguachica",
        "location": "Laboratorios de Cómputo",
        "urgency": "Baja",
        "status": "Cerrado",
        "requester_email": "docente@unicesar.edu.co",
        "tech_email": "tecnico5@unicesar.edu.co",
        "hours_ago": 30.0,
        "first_resp_mins": 40,
        "diagnosis": "Equipos de laboratorio sin paquetes estadísticos actualizados para el semestre 2026-2.",
        "solution": "Se desplegó imagen institucional con SPSS 29 licenciado y RStudio 2026 en los 25 equipos y se probó ejecución.",
        "csat_score": 5,
    },
    {
        "seq": 6,
        "title": "Impresora administrativa con atasco recurrente",
        "description": "La impresora multifuncional de Registro y Control atascó hojas en el fusor y detuvo la cola de impresión.",
        "service_name": "Equipos de Cómputo e Impresoras",
        "sede": "Sede Sabanas (Valledupar)",
        "location": "Edificio Administrativo",
        "urgency": "Media",
        "status": "En atención",
        "requester_email": "estudiante@unicesar.edu.co",
        "tech_email": "tecnico6@unicesar.edu.co",
        "hours_ago": 3.2,
        "first_resp_mins": 32,
        "diagnosis": None,
        "solution": None,
        "csat_score": None,
    },
]


def seed_sample_tickets(session: Session, now_iso: str) -> None:
    """Precarga 6 tickets demostrativos solo cuando la tabla tickets está vacía."""
    if (session.scalar(select(func.count(TicketORM.id))) or 0) > 0:
        return
    users_map = {u.email: u for u in session.scalars(select(UserORM)).all()}
    now_dt = now_bogota()
    seq_by_key: dict[tuple[str, int], int] = {}

    for item in SAMPLE_TICKETS:
        svc = item["service_name"]
        meta = UPC_SERVICE_CATALOG[svc]
        prefix = get_service_prefix(svc)
        prio = calculate_priority_or03(meta["base_impact"], item["urgency"])
        created_dt = now_dt - timedelta(hours=item["hours_ago"])
        req_user = users_map[item["requester_email"]]
        tech_user = users_map[item["tech_email"]]
        yr = 2026
        seq = seq_by_key.get((prefix, yr), 0) + 1
        seq_by_key[(prefix, yr)] = seq

        ticket_obj = TicketORM(
            ticket_number=format_ticket_number(seq, year=yr, prefix=prefix),
            category_prefix=prefix,
            ticket_year=yr,
            sequence_number=seq,
            legacy_ticket_number=format_ticket_number(item["seq"], year=yr),
            content_dedup_hash=compute_content_dedup_hash(req_user.id, svc, item["title"]),
            version=1,
            title=item["title"],
            description=item["description"],
            ticket_type=meta["default_type"],
            service_name=svc,
            area=meta["area"],
            sede=item["sede"],
            location=item["location"],
            impact=prio["impact"],
            urgency=prio["urgency"],
            priority=prio["priority"],
            status=item["status"],
            requester_id=req_user.id,
            requester_email=req_user.email,
            requester_role=req_user.role,
            assigned_tech_id=tech_user.id,
            assigned_tech_email=tech_user.email,
            sla_response_hours=prio["sla_response_hours"],
            sla_resolution_hours=prio["sla_resolution_hours"],
            response_deadline=add_business_hours(created_dt, prio["sla_response_hours"]).isoformat(),
            resolution_deadline=add_business_hours(created_dt, prio["sla_resolution_hours"]).isoformat(),
            first_response_at=(
                (created_dt + timedelta(minutes=item["first_resp_mins"])).isoformat()
                if item["first_resp_mins"] is not None
                else None
            ),
            paused_at=(now_dt - timedelta(hours=1)).isoformat() if item["status"] == "En espera" else None,
            paused_seconds=0,
            resolved_at=(
                (created_dt + timedelta(hours=3.5)).isoformat()
                if item["status"] in ("Resuelto", "Cerrado")
                else None
            ),
            closed_at=(created_dt + timedelta(hours=6.0)).isoformat() if item["status"] == "Cerrado" else None,
            diagnosis=item["diagnosis"],
            solution=item["solution"],
            closing_category="Solución definitiva en sitio" if item["solution"] else None,
            csat_score=item["csat_score"],
            ai_suggested_service=svc,
            ai_confidence=94.5,
            ai_human_validated=True,
            created_at=created_dt.isoformat(),
            updated_at=now_iso,
        )
        session.add(ticket_obj)
        session.flush()
        tech_user.last_assigned_at = created_dt.isoformat()

        session.add(
            TicketAuditEventORM(
                ticket_id=ticket_obj.id,
                actor_email=req_user.email,
                action="Creación y Asignación automática",
                old_status=None,
                new_status="Asignado",
                comment=f"Asignado automáticamente a {tech_user.email} por menor carga.",
                created_at=created_dt.isoformat(),
            )
        )
        if item["status"] != "Asignado":
            session.add(
                TicketAuditEventORM(
                    ticket_id=ticket_obj.id,
                    actor_email=tech_user.email,
                    action="Actualización operativa",
                    old_status="Asignado",
                    new_status=item["status"],
                    comment="Atención iniciada por el técnico asignado.",
                    created_at=now_iso,
                )
            )
        session.add(
            TicketMessageORM(
                ticket_id=ticket_obj.id,
                sender_id=req_user.id,
                sender_email=req_user.email,
                sender_role=req_user.role,
                message=f"Buenos días, adjunto el detalle del caso: {item['description']}",
                is_read=True,
                created_at=created_dt.isoformat(),
            )
        )
        session.add(
            TicketMessageORM(
                ticket_id=ticket_obj.id,
                sender_id=tech_user.id,
                sender_email=tech_user.email,
                sender_role="tecnico",
                message="Caso recibido en la mesa de servicios UPC. Iniciando verificación técnica.",
                is_read=False,
                created_at=(created_dt + timedelta(minutes=12)).isoformat(),
            )
        )

    for (pref, yr), last_seq in seq_by_key.items():
        existing_cnt = session.get(TicketCounterORM, (pref, yr))
        if existing_cnt is None:
            session.add(TicketCounterORM(prefix=pref, year=yr, last_seq=last_seq, updated_at=now_iso))
        else:
            existing_cnt.last_seq = max(existing_cnt.last_seq, last_seq)
            existing_cnt.updated_at = now_iso

    session.add(
        AuditLogORM(
            timestamp=now_iso,
            user_email="system@unicesar.edu.co",
            ip_address="127.0.0.1",
            action="SEED_INITIALIZATION",
            entity="system",
            entity_id="casagbi",
            old_value=None,
            new_value="Base inicial CASAGBI UPC cargada con SQLAlchemy",
        )
    )
