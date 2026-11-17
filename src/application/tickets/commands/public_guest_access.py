"""Casos de uso CQRS de acceso externo de invitado, OTP y tickets efímeros WebSocket."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.application.tickets.ticket_helpers import (
    GUEST_OTP_OUTBOX,
    LOOKUP_LOCKOUT_SECONDS,
    LOOKUP_MAX_ATTEMPTS,
    authorize_ticket_access,
    is_guest_otp_enabled,
    sanitize_for_guest,
)
from src.domain.exceptions import (
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import calculate_sla_status, constant_time_email_matches, mask_email
from src.domain.value_objects import TicketCode


@dataclass(frozen=True)
class PublicTicketLookupCommand(Command):
    ticket_code: str
    email: str
    otp_code: Optional[str] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class CreateWsTicketCommand(Command):
    actor: Dict[str, Any]
    ticket_id: int


class PublicTicketLookupCommandHandler:
    """Consulta externa segura por {ticket_code, email} con anti-enumeración, bloqueo e invitado 2h."""

    def __init__(
        self, uow_factory: Callable[[], IUnitOfWork], guest_token_factory: Callable[..., str]
    ) -> None:
        self._uow_factory = uow_factory
        self._guest_token_factory = guest_token_factory

    def handle(self, cmd: PublicTicketLookupCommand) -> Dict[str, Any]:
        raw_code = (cmd.ticket_code or "").strip().upper()
        raw_email = (cmd.email or "").strip().lower()
        ip_addr = (cmd.ip_address or "127.0.0.1").strip()
        now_utc_iso = datetime.now(timezone.utc).isoformat()
        code_bucket = raw_code or "EMPTY"

        with self._uow_factory() as uow:
            uow.begin_immediate()
            for bucket_ip, bucket_code in ((ip_addr, code_bucket), (ip_addr, "*"), ("*", code_bucket)):
                att = uow.tickets.get_lookup_attempt(bucket_ip, bucket_code)
                if att and att.get("locked_until") and str(att["locked_until"]) > now_utc_iso:
                    uow.audit_logs.append(
                        {
                            "user_email": raw_email or "anonymous",
                            "ip_address": ip_addr,
                            "action": "PUBLIC_LOOKUP_BLOCKED",
                            "entity": "tickets",
                            "entity_id": code_bucket,
                            "new_value": f"locked_until={att['locked_until']}",
                        }
                    )
                    uow.commit()
                    raise TooManyRequestsError(
                        "Demasiados intentos fallidos. La consulta externa ha sido bloqueada temporalmente."
                    )

            is_valid_syntax = True
            try:
                TicketCode(raw_code)
            except ValidationDomainError:
                is_valid_syntax = False

            ticket = (
                uow.tickets.get_by_number(raw_code)
                if is_valid_syntax
                else uow.tickets.get_by_number("MS-GEN-0000-000000")
            )
            target_email = (
                ticket["requester_email"]
                if (is_valid_syntax and ticket is not None)
                else "dummy-constant-time@unicesar.edu.co"
            )
            email_matched = constant_time_email_matches(raw_email, target_email)

            if not is_valid_syntax or ticket is None or not email_matched:
                for b_ip, b_code, m_att in (
                    (ip_addr, code_bucket, LOOKUP_MAX_ATTEMPTS),
                    ("*", code_bucket, LOOKUP_MAX_ATTEMPTS),
                    (ip_addr, "*", LOOKUP_MAX_ATTEMPTS * 2),
                ):
                    uow.tickets.record_lookup_failure(
                        b_ip, b_code, max_attempts=m_att, lockout_seconds=LOOKUP_LOCKOUT_SECONDS
                    )
                uow.audit_logs.append(
                    {
                        "user_email": mask_email(raw_email) if "@" in raw_email else "anonymous",
                        "ip_address": ip_addr,
                        "action": "PUBLIC_LOOKUP_FAILED",
                        "entity": "tickets",
                        "entity_id": code_bucket,
                    }
                )
                uow.commit()
                raise UnauthorizedError(
                    "No fue posible validar el radicado con el correo institucional indicado.",
                    title="Credenciales de consulta inválidas",
                )

            if is_guest_otp_enabled():
                provided_otp = (cmd.otp_code or "").strip()
                if not provided_otp:
                    otp_plain = f"{secrets.randbelow(1_000_000):06d}"
                    otp_hash = hashlib.sha256(otp_plain.encode("utf-8")).hexdigest()
                    exp_iso = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
                    uow.tickets.create_guest_otp(
                        int(ticket["id"]), ticket["requester_email"], otp_hash, exp_iso
                    )
                    GUEST_OTP_OUTBOX[(ticket["ticket_number"], ticket["requester_email"].lower())] = otp_plain
                    print(
                        f"[CASAGBI OTP OUTBOX] ticket={ticket['ticket_number']} "
                        f"para={mask_email(ticket['requester_email'])} codigo={otp_plain}"
                    )
                    uow.commit()
                    return {
                        "otp_required": True,
                        "ticket_number": ticket["ticket_number"],
                        "masked_email": mask_email(ticket["requester_email"]),
                        "detail": "Se envió un código de un solo uso al correo institucional.",
                    }
                otp_hash = hashlib.sha256(provided_otp.encode("utf-8")).hexdigest()
                if not uow.tickets.consume_guest_otp(
                    int(ticket["id"]), ticket["requester_email"], otp_hash, now_utc_iso
                ):
                    uow.tickets.record_lookup_failure(
                        ip_addr, code_bucket, max_attempts=LOOKUP_MAX_ATTEMPTS, lockout_seconds=LOOKUP_LOCKOUT_SECONDS
                    )
                    uow.commit()
                    raise UnauthorizedError(
                        "El código OTP es inválido o ha expirado.",
                        title="Credenciales de consulta inválidas",
                    )

            for b_ip, b_code in ((ip_addr, code_bucket), ("*", code_bucket), (ip_addr, "*")):
                uow.tickets.reset_lookup_attempts(b_ip, b_code)

            events = uow.tickets.get_audit_events(ticket["id"])
            messages = uow.tickets.get_messages(ticket["id"])
            uow.tickets.mark_messages_read(ticket["id"], ticket["requester_email"])
            masked = mask_email(ticket["requester_email"])
            uow.audit_logs.append(
                {
                    "user_email": masked,
                    "ip_address": ip_addr,
                    "action": "PUBLIC_LOOKUP_SUCCESS",
                    "entity": "tickets",
                    "entity_id": ticket["ticket_number"],
                }
            )
            uow.commit()

        guest_token = self._guest_token_factory(
            ticket_id=int(ticket["id"]),
            ticket_number=ticket["ticket_number"],
            requester_id=int(ticket["requester_id"]),
            requester_email=ticket["requester_email"],
            masked_email=masked,
        )
        ticket["sla_status"] = calculate_sla_status(ticket)
        clean_ticket, clean_events, clean_messages = sanitize_for_guest(ticket, events, messages)
        return {
            "otp_required": False,
            "ticket_guest_token": guest_token,
            "expires_in": 7200,
            "role": "invitado",
            "masked_email": masked,
            "ticket": clean_ticket,
            "timeline": clean_events,
            "messages": clean_messages,
            "chat_read_only": ticket["status"] in ("Cerrado", "Anulado"),
        }


class CreateWsTicketCommandHandler:
    """Emite un ticket efímero de un solo uso (60 s) para autenticar el handshake WebSocket."""

    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: CreateWsTicketCommand) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            uow.begin_immediate()
            ticket = uow.tickets.get_by_id(cmd.ticket_id)
            if not ticket:
                raise NotFoundError(f"Ticket #{cmd.ticket_id} no encontrado.")
            authorize_ticket_access(cmd.actor, ticket)

            raw_ticket = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_ticket.encode("utf-8")).hexdigest()
            exp_iso = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
            actor_snapshot = {
                "id": int(cmd.actor["id"]),
                "email": cmd.actor["email"],
                "masked_email": cmd.actor.get("masked_email"),
                "full_name": cmd.actor.get("full_name") or cmd.actor["email"],
                "role": cmd.actor["role"],
                "ticket_id": int(ticket["id"]),
            }
            uow.tickets.create_ws_ticket(
                token_hash=token_hash,
                ticket_id=int(ticket["id"]),
                user_json=json.dumps(actor_snapshot, ensure_ascii=False),
                expires_at=exp_iso,
            )
            uow.commit()
        return {"ws_ticket": raw_ticket, "expires_in": 60}
