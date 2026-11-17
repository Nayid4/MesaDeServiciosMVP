"""Herramienta check_ticket del Agente IA CASAGBI (lookup autenticado e invitado)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.application.ai_agent.agent_intents import EMAIL_REGEX
from src.application.tickets import (
    PublicTicketLookupCommand,
    PublicTicketLookupCommandHandler,
)
from src.domain.exceptions import TooManyRequestsError, UnauthorizedError
from src.domain.ports import IUnitOfWork
from src.domain.rules import calculate_sla_status
from src.infrastructure.ml.ai_engine import TICKET_ID_REGEX


def handle_check_ticket_tool(
    uow_factory: Callable[[], IUnitOfWork],
    guest_token_factory: Callable[..., str],
    query: str,
    user: Dict[str, Any],
    *,
    history: Optional[list[Dict[str, str]]],
    email: Optional[str],
    ip_address: str,
) -> Dict[str, Any]:
    """Resuelve consultas de radicado o bandeja reciente respetando RBAC y lookup invitado."""
    code: Optional[str] = None
    ticket_match = TICKET_ID_REGEX.search(query)
    if ticket_match:
        code = ticket_match.group(0).upper()
    elif history:
        for item in reversed(history[-6:]):
            m = TICKET_ID_REGEX.search(str(item.get("content") or ""))
            if m:
                code = m.group(0).upper()
                break

    candidate_email = (email or "").strip().lower() or None
    if not candidate_email:
        em = EMAIL_REGEX.search(query)
        if em:
            candidate_email = em.group(0).lower()

    if code:
        if user.get("role") == "public":
            if not candidate_email:
                return {
                    "status": "lookup_needs_email",
                    "tool_invoked": "check_ticket",
                    "pending_ticket_code": code,
                    "reply": (
                        f"Para consultar el radicado `{code}` por seguridad necesito validar el **correo institucional** "
                        "`@unicesar.edu.co` con el que fue registrado (escríbelo aquí junto al radicado o en el campo de correo)."
                    ),
                    "matched_articles": [],
                    "prediction": None,
                    "draft_card": None,
                }
            lookup_handler = PublicTicketLookupCommandHandler(uow_factory, guest_token_factory)
            try:
                pub = lookup_handler.handle(
                    PublicTicketLookupCommand(
                        ticket_code=code, email=candidate_email, ip_address=ip_address
                    )
                )
            except (TooManyRequestsError, UnauthorizedError) as exc:
                status = "lookup_blocked" if isinstance(exc, TooManyRequestsError) else "lookup_failed"
                return {
                    "status": status,
                    "tool_invoked": "check_ticket",
                    "reply": str(exc),
                    "matched_articles": [],
                    "prediction": None,
                    "draft_card": None,
                }
            tk = pub["ticket"]
            return {
                "status": "lookup_verified",
                "tool_invoked": "check_ticket",
                "reply": (
                    f"**Consulta validada de radicado `{tk['ticket_number']}`**\n"
                    f"- **Titular validado:** `{pub['masked_email']}`\n"
                    f"- **Servicio / Área:** {tk['service_name']} ({tk['area']})\n"
                    f"- **Estado actual:** `{tk['status']}` | **Prioridad OR-03:** `{tk['priority']}`\n"
                    f"- **Semáforo SLA:** {tk['sla_status']['semaphore']} — {tk['sla_status']['label']}\n"
                    f"- **Sede / Ubicación:** {tk['sede']} · {tk['location']}"
                ),
                "matched_articles": [],
                "prediction": None,
                "draft_card": None,
                "ticket_snapshot": tk,
                "ticket_guest_token": pub["ticket_guest_token"],
                "masked_email": pub["masked_email"],
            }

        with uow_factory() as uow:
            t = uow.tickets.get_by_number(code)
        if not t or (user["role"] == "usuario" and int(t["requester_id"]) != int(user["id"])):
            return {
                "status": "ok",
                "tool_invoked": "check_ticket",
                "reply": (
                    f"No encontré un ticket autorizado con el radicado **{code}**. "
                    "Por control RBAC solo puedes consultar tus propios radicados o los asignados a tu área."
                ),
                "matched_articles": [],
                "prediction": None,
                "draft_card": None,
            }
        sla = calculate_sla_status(t)
        return {
            "status": "ok",
            "tool_invoked": "check_ticket",
            "reply": (
                f"**Estado del ticket {t['ticket_number']}**\n"
                f"- **Asunto:** {t['title']}\n"
                f"- **Servicio / Área:** {t['service_name']} ({t['area']})\n"
                f"- **Estado:** `{t['status']}` | **Prioridad OR-03:** `{t['priority']}`\n"
                f"- **Técnico asignado:** {t.get('assigned_tech_email') or 'En cola de coordinación'}\n"
                f"- **Semáforo SLA:** {sla['semaphore']} — {sla['label']}"
            ),
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
            "ticket_snapshot": t,
        }

    if user.get("role") == "public":
        return {
            "status": "ok",
            "tool_invoked": "check_ticket",
            "reply": (
                "Para consultar un ticket sin iniciar sesión, escribe el código de radicado "
                "`MS-CAT-AAAA-NNNNNN` (o `MS-AAAA-NNNNNN`) y el correo institucional `@unicesar.edu.co` asociado."
            ),
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
        }

    with uow_factory() as uow:
        if user["role"] == "tecnico":
            own = uow.tickets.list_tickets(assigned_tech_id=int(user["id"]), limit=5)
        elif user["role"] in ("coordinador", "admin", "director"):
            own = uow.tickets.list_tickets(limit=5)
        else:
            own = uow.tickets.list_tickets(requester_id=int(user["id"]), limit=5)

    if not own:
        return {
            "status": "ok",
            "tool_invoked": "check_ticket",
            "reply": "Aún no tienes tickets registrados en CASAGBI. Cuéntame tu falla si deseas preparar un borrador.",
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
        }
    lines = "\n".join(
        f"- **{t['ticket_number']}** | {t['title']} — `{t['status']}` ({t['priority']}, {calculate_sla_status(t)['label']})"
        for t in own
    )
    return {
        "status": "ok",
        "tool_invoked": "check_ticket",
        "reply": f"Estos son los tickets más recientes asociados a tu perfil:\n{lines}",
        "matched_articles": [],
        "prediction": None,
        "draft_card": None,
    }
