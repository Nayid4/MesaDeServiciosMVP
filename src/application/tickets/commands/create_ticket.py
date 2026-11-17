"""Caso de uso CQRS de radicación atómica de tickets con idempotencia y menor carga."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.domain.exceptions import ForbiddenError, ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import (
    ROLE_LABELS,
    UPC_SERVICE_CATALOG,
    calculate_sla_status,
    compute_content_dedup_hash,
    get_service_prefix,
    now_bogota,
    select_technician_least_load,
)
from src.domain.value_objects import PriorityMatrix, SLADeadline


@dataclass(frozen=True)
class CreateTicketCommand(Command):
    actor: Dict[str, Any]
    title: str
    description: str
    ticket_type: str
    service_name: str
    sede: str
    location: str
    urgency: str
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_human_validated: bool = False
    initial_transcript: Optional[str] = None
    idempotency_key: Optional[str] = None
    ip_address: str = "127.0.0.1"


def _record_routing_and_notifications(
    uow: IUnitOfWork,
    cmd: CreateTicketCommand,
    created_ticket: Dict[str, Any],
    svc_meta: Dict[str, Any],
    selected_tech: Optional[Dict[str, Any]],
    priority_label: str,
    created_iso: str,
) -> None:
    ticket_code = created_ticket["ticket_number"]
    uow.tickets.add_audit_event(
        {
            "ticket_id": created_ticket["id"],
            "actor_email": cmd.actor["email"],
            "action": "Creación de ticket",
            "old_status": None,
            "new_status": "Registrado",
            "comment": f"Radicado {ticket_code} en {cmd.sede} ({cmd.location}).",
            "created_at": created_iso,
        }
    )
    if cmd.ai_suggested_service:
        uow.tickets.add_audit_event(
            {
                "ticket_id": created_ticket["id"],
                "actor_email": "casagbi-agent@unicesar.edu.co",
                "action": "Clasificación IA (Human-in-the-Loop)",
                "old_status": "Registrado",
                "new_status": "Registrado",
                "comment": (
                    f"Sugerencia IA: {cmd.ai_suggested_service} ({cmd.ai_confidence or 0:.1f}%). "
                    f"Confirmado por solicitante: {cmd.service_name}."
                ),
                "created_at": created_iso,
            }
        )
    if selected_tech:
        uow.users.update(int(selected_tech["id"]), {"last_assigned_at": created_iso})
        uow.tickets.add_audit_event(
            {
                "ticket_id": created_ticket["id"],
                "actor_email": "system@unicesar.edu.co",
                "action": "Asignación automática (menor carga)",
                "old_status": "Registrado",
                "new_status": "Asignado",
                "comment": f"Enrutado a {selected_tech['email']} (Área {svc_meta['area']}).",
                "created_at": created_iso,
            }
        )
        uow.notifications.create(
            {
                "user_email": selected_tech["email"],
                "ticket_number": ticket_code,
                "title": f"Nuevo ticket asignado ({priority_label})",
                "message": f"{ticket_code}: {cmd.title.strip()} — {cmd.sede}",
                "created_at": created_iso,
            }
        )
        return

    uow.tickets.add_audit_event(
        {
            "ticket_id": created_ticket["id"],
            "actor_email": "system@unicesar.edu.co",
            "action": "En cola del coordinador (sin técnicos activos)",
            "old_status": "Registrado",
            "new_status": "Registrado",
            "comment": (
                f"No hay técnicos activos disponibles en el área {svc_meta['area']}. "
                "El ticket permanece en estado Registrado en la cola del coordinador."
            ),
            "created_at": created_iso,
        }
    )
    coordinators = uow.users.list_users(role="coordinador", is_active=True) or uow.users.list_users(
        role="admin", is_active=True
    )
    for coord in coordinators:
        uow.notifications.create(
            {
                "user_email": coord["email"],
                "ticket_number": ticket_code,
                "title": f"Ticket en cola sin técnico activo ({priority_label})",
                "message": (
                    f"{ticket_code} ({svc_meta['area']}): requiere asignación manual "
                    "porque no hay técnicos activos en el área."
                ),
                "created_at": created_iso,
            }
        )


class CreateTicketCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: CreateTicketCommand) -> Dict[str, Any]:
        if cmd.actor.get("role") == "director":
            raise ForbiddenError("El rol Director es de consulta ejecutiva y no radica tickets operativos.")
        if not cmd.title or len(cmd.title.strip()) < 5:
            raise ValidationDomainError("El asunto debe tener al menos 5 caracteres.")
        if not cmd.description or len(cmd.description.strip()) < 15:
            raise ValidationDomainError("La descripción debe detallar el caso (mínimo 15 caracteres).")
        if not cmd.sede or not cmd.location:
            raise ValidationDomainError("Debe seleccionar la sede y la ubicación del reporte.")

        clean_idem_key = (cmd.idempotency_key or "").strip() or None
        with self._uow_factory() as uow:
            uow.begin_immediate()
            if clean_idem_key:
                existing_idem = uow.tickets.get_by_idempotency_key(int(cmd.actor["id"]), clean_idem_key)
                if existing_idem:
                    existing_idem["sla_status"] = calculate_sla_status(existing_idem)
                    existing_idem["deduplicated"] = True
                    existing_idem["dedup_reason"] = "idempotency_key"
                    existing_idem["notice"] = (
                        "Petición duplicada detectada por Idempotency-Key. "
                        f"Se conserva el radicado {existing_idem['ticket_number']}."
                    )
                    return existing_idem

            services_map = {s["service_name"]: s for s in uow.catalog.list_services(active_only=True)}
            if cmd.service_name in services_map:
                svc_meta = services_map[cmd.service_name]
            elif cmd.service_name in UPC_SERVICE_CATALOG:
                svc_meta = UPC_SERVICE_CATALOG[cmd.service_name]
            else:
                raise ValidationDomainError(f"El servicio '{cmd.service_name}' no está activo en el catálogo UPC.")

            created_dt = now_bogota()
            dedup_hash = compute_content_dedup_hash(int(cmd.actor["id"]), cmd.service_name, cmd.title)
            since_iso = (created_dt - timedelta(minutes=2)).isoformat()
            recent_dup = uow.tickets.find_recent_duplicate(int(cmd.actor["id"]), dedup_hash, since_iso)
            if recent_dup is not None:
                if clean_idem_key:
                    uow.tickets.save_idempotency_key(int(cmd.actor["id"]), clean_idem_key, int(recent_dup["id"]))
                    uow.commit()
                recent_dup["sla_status"] = calculate_sla_status(recent_dup)
                recent_dup["deduplicated"] = True
                recent_dup["dedup_reason"] = "content_duplicate_2m"
                recent_dup["notice"] = (
                    f"Ya radicaste un caso idéntico en los últimos 2 minutos "
                    f"({recent_dup['ticket_number']}). Se devolvió el ticket existente."
                )
                return recent_dup

            prio_matrix = PriorityMatrix.evaluate(
                impact=svc_meta["base_impact"],
                urgency=cmd.urgency,
                custom_sla_table=uow.catalog.get_sla_table() or None,
            )
            sla_deadline = SLADeadline.compute(prio_matrix, created_at=created_dt)
            created_iso = created_dt.isoformat()
            selected_tech = select_technician_least_load(
                uow.users.list_active_technicians_with_load(svc_meta["area"])
            )
            prefix = svc_meta.get("category_prefix") or get_service_prefix(cmd.service_name)
            ticket_code, seq_num = uow.tickets.allocate_next_ticket_code(prefix, year=created_dt.year)

            created_ticket = uow.tickets.create(
                {
                    "ticket_number": ticket_code,
                    "category_prefix": prefix,
                    "ticket_year": created_dt.year,
                    "sequence_number": seq_num,
                    "content_dedup_hash": dedup_hash,
                    "version": 1,
                    "title": cmd.title.strip(),
                    "description": cmd.description.strip(),
                    "ticket_type": cmd.ticket_type or svc_meta["default_type"],
                    "service_name": cmd.service_name,
                    "area": svc_meta["area"],
                    "sede": cmd.sede,
                    "location": cmd.location,
                    "impact": prio_matrix.impact,
                    "urgency": prio_matrix.urgency,
                    "priority": prio_matrix.priority,
                    "status": "Asignado" if selected_tech else "Registrado",
                    "requester_id": int(cmd.actor["id"]),
                    "requester_email": cmd.actor["email"],
                    "requester_role": ROLE_LABELS.get(cmd.actor["role"], cmd.actor["role"]),
                    "assigned_tech_id": int(selected_tech["id"]) if selected_tech else None,
                    "assigned_tech_email": selected_tech["email"] if selected_tech else None,
                    "sla_response_hours": prio_matrix.sla_response_hours,
                    "sla_resolution_hours": prio_matrix.sla_resolution_hours,
                    "response_deadline": sla_deadline.response_deadline.isoformat(),
                    "resolution_deadline": sla_deadline.resolution_deadline.isoformat(),
                    "ai_suggested_service": cmd.ai_suggested_service,
                    "ai_confidence": cmd.ai_confidence,
                    "ai_human_validated": bool(cmd.ai_human_validated),
                    "created_at": created_iso,
                    "updated_at": created_iso,
                }
            )
            if clean_idem_key:
                uow.tickets.save_idempotency_key(int(cmd.actor["id"]), clean_idem_key, int(created_ticket["id"]))

            _record_routing_and_notifications(
                uow, cmd, created_ticket, svc_meta, selected_tech, prio_matrix.priority, created_iso
            )
            first_msg = cmd.description.strip()
            if cmd.initial_transcript:
                first_msg += f"\n\n[Transcripción Agente IA Nivel 0]\n{cmd.initial_transcript.strip()}"
            uow.tickets.add_message(
                {
                    "ticket_id": created_ticket["id"],
                    "sender_id": int(cmd.actor["id"]),
                    "sender_email": cmd.actor["email"],
                    "sender_role": cmd.actor["role"],
                    "message": first_msg,
                    "is_read": False,
                    "created_at": created_iso,
                }
            )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TICKET_CREATED",
                    "entity": "tickets",
                    "entity_id": ticket_code,
                    "new_value": f"Servicio={cmd.service_name}, Prioridad={prio_matrix.priority}, Tech={created_ticket.get('assigned_tech_email')}",
                }
            )
            uow.commit()

        created_ticket["sla_status"] = calculate_sla_status(created_ticket)
        created_ticket["deduplicated"] = False
        return created_ticket
