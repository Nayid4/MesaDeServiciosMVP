"""Mixin SQLAlchemy para control anti-fuerza-bruta público, OTP invitado y tickets WS."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import desc, select, update

from src.infrastructure.persistence.models import (
    GuestOtpChallengeORM,
    PublicLookupAttemptORM,
    WsConnectionTicketORM,
)
from src.infrastructure.persistence.repositories.base import model_to_dict


class TicketGuestAccessMixin:
    """Provee operaciones de lookup público, OTP invitado y tickets WebSocket."""

    session: Any

    def get_lookup_attempt(self, ip_address: str, ticket_code: str) -> Optional[Dict[str, Any]]:
        stmt = select(PublicLookupAttemptORM).where(
            PublicLookupAttemptORM.ip_address == (ip_address or "127.0.0.1"),
            PublicLookupAttemptORM.ticket_code == (ticket_code or "*").strip().upper(),
        )
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None

    def record_lookup_failure(
        self,
        ip_address: str,
        ticket_code: str,
        *,
        max_attempts: int = 5,
        lockout_seconds: int = 900,
    ) -> Dict[str, Any]:
        ip = ip_address or "127.0.0.1"
        code = (ticket_code or "*").strip().upper()
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        obj = self.session.scalars(
            select(PublicLookupAttemptORM).where(
                PublicLookupAttemptORM.ip_address == ip,
                PublicLookupAttemptORM.ticket_code == code,
            )
        ).first()
        if obj is None:
            obj = PublicLookupAttemptORM(
                ip_address=ip,
                ticket_code=code,
                attempt_count=1,
                locked_until=None,
                updated_at=now_iso,
            )
            self.session.add(obj)
        else:
            if obj.locked_until and obj.locked_until <= now_iso:
                obj.attempt_count = 1
                obj.locked_until = None
            else:
                obj.attempt_count = int(obj.attempt_count or 0) + 1
            obj.updated_at = now_iso
        if int(obj.attempt_count) >= int(max_attempts):
            obj.locked_until = (now_dt + timedelta(seconds=int(lockout_seconds))).isoformat()
        self.session.flush()
        return model_to_dict(obj)

    def reset_lookup_attempts(self, ip_address: str, ticket_code: str) -> None:
        ip = ip_address or "127.0.0.1"
        code = (ticket_code or "*").strip().upper()
        self.session.execute(
            update(PublicLookupAttemptORM)
            .where(
                PublicLookupAttemptORM.ip_address == ip,
                PublicLookupAttemptORM.ticket_code == code,
            )
            .values(
                attempt_count=0,
                locked_until=None,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.session.flush()

    def create_guest_otp(self, ticket_id: int, email: str, otp_hash: str, expires_at: str) -> None:
        obj = GuestOtpChallengeORM(
            ticket_id=int(ticket_id),
            email=email.strip().lower(),
            otp_hash=otp_hash,
            expires_at=expires_at,
            consumed=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(obj)
        self.session.flush()

    def consume_guest_otp(self, ticket_id: int, email: str, otp_hash: str, now_iso: str) -> bool:
        obj = self.session.scalars(
            select(GuestOtpChallengeORM)
            .where(
                GuestOtpChallengeORM.ticket_id == int(ticket_id),
                GuestOtpChallengeORM.email == email.strip().lower(),
                GuestOtpChallengeORM.otp_hash == otp_hash,
                GuestOtpChallengeORM.consumed.is_(False),
                GuestOtpChallengeORM.expires_at > now_iso,
            )
            .order_by(desc(GuestOtpChallengeORM.id))
        ).first()
        if obj is None:
            return False
        res = self.session.execute(
            update(GuestOtpChallengeORM)
            .where(GuestOtpChallengeORM.id == obj.id, GuestOtpChallengeORM.consumed.is_(False))
            .values(consumed=True)
        )
        self.session.flush()
        return (res.rowcount or 0) == 1

    def create_ws_ticket(self, token_hash: str, ticket_id: int, user_json: str, expires_at: str) -> None:
        obj = WsConnectionTicketORM(
            token_hash=token_hash,
            ticket_id=int(ticket_id),
            user_json=user_json,
            expires_at=expires_at,
            consumed=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(obj)
        self.session.flush()

    def consume_ws_ticket(
        self, token_hash: str, ticket_id: int, now_iso: str
    ) -> Optional[Dict[str, Any]]:
        obj = self.session.scalars(
            select(WsConnectionTicketORM).where(
                WsConnectionTicketORM.token_hash == token_hash,
                WsConnectionTicketORM.ticket_id == int(ticket_id),
                WsConnectionTicketORM.consumed.is_(False),
                WsConnectionTicketORM.expires_at > now_iso,
            )
        ).first()
        if obj is None:
            return None
        res = self.session.execute(
            update(WsConnectionTicketORM)
            .where(
                WsConnectionTicketORM.id == obj.id,
                WsConnectionTicketORM.consumed.is_(False),
            )
            .values(consumed=True)
        )
        self.session.flush()
        if (res.rowcount or 0) != 1:
            return None
        return json.loads(obj.user_json)
