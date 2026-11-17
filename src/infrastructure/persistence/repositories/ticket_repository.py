"""Repositorio SQLAlchemy de tickets con contadores atómicos y bloqueo optimista."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.domain.exceptions import ConflictError
from src.domain.ports import ITicketRepo
from src.domain.rules import format_ticket_number, get_service_prefix, now_bogota
from src.infrastructure.persistence.models import (
    IdempotencyKeyORM,
    TicketCounterORM,
    TicketORM,
)
from src.infrastructure.persistence.repositories.base import model_to_dict
from src.infrastructure.persistence.repositories.ticket_comms_repository import (
    TicketCommsMixin,
)
from src.infrastructure.persistence.repositories.ticket_guest_repository import (
    TicketGuestAccessMixin,
)
from src.infrastructure.persistence.repositories.ticket_queries_repository import (
    TicketQueriesMixin,
)

_ALLOWED_TICKET_UPDATES = {
    "status", "assigned_tech_id", "assigned_tech_email", "area", "impact", "urgency",
    "priority", "sla_response_hours", "sla_resolution_hours", "response_deadline",
    "resolution_deadline", "first_response_at", "paused_at", "paused_seconds",
    "resolved_at", "closed_at", "diagnosis", "solution", "closing_category",
    "csat_score", "csat_comment", "priority_justification", "sla_breached",
    "sla_alert_75_sent", "updated_at",
}


class SqlAlchemyTicketRepo(
    TicketQueriesMixin, TicketCommsMixin, TicketGuestAccessMixin, ITicketRepo
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_ticket_number(self, year: int = 2026) -> str:
        code, _ = self.allocate_next_ticket_code("GEN", year=year)
        return code

    def allocate_next_ticket_code(self, prefix: str, year: int = 2026) -> tuple[str, int]:
        """Reserva e incrementa atómicamente el contador por (prefijo, año)."""
        clean_prefix = (prefix or "GEN").strip().upper()
        year_int = int(year)
        now_iso = now_bogota().isoformat()
        stmt = (
            sqlite_insert(TicketCounterORM)
            .values(prefix=clean_prefix, year=year_int, last_seq=1, updated_at=now_iso)
            .on_conflict_do_update(
                index_elements=[TicketCounterORM.prefix, TicketCounterORM.year],
                set_={"last_seq": TicketCounterORM.last_seq + 1, "updated_at": now_iso},
            )
            .returning(TicketCounterORM.last_seq)
        )
        next_seq = int(self.session.execute(stmt).scalar_one())
        return format_ticket_number(next_seq, year=year_int, prefix=clean_prefix), next_seq

    def get_by_idempotency_key(self, user_id: int, key: str) -> Optional[Dict[str, Any]]:
        clean_key = (key or "").strip()
        if not clean_key:
            return None
        record = self.session.scalars(
            select(IdempotencyKeyORM).where(
                IdempotencyKeyORM.user_id == int(user_id),
                IdempotencyKeyORM.idempotency_key == clean_key,
            )
        ).first()
        if record is None:
            return None
        ticket_obj = self.session.get(TicketORM, int(record.ticket_id))
        return model_to_dict(ticket_obj) if ticket_obj is not None else None

    def save_idempotency_key(self, user_id: int, key: str, ticket_id: int) -> None:
        clean_key = (key or "").strip()
        if not clean_key:
            return
        self.session.add(
            IdempotencyKeyORM(
                user_id=int(user_id),
                idempotency_key=clean_key,
                ticket_id=int(ticket_id),
                created_at=now_bogota().isoformat(),
            )
        )
        self.session.flush()

    def find_recent_duplicate(
        self, requester_id: int, content_dedup_hash: str, since_iso: str
    ) -> Optional[Dict[str, Any]]:
        if not content_dedup_hash:
            return None
        stmt = (
            select(TicketORM)
            .where(
                TicketORM.requester_id == int(requester_id),
                TicketORM.content_dedup_hash == content_dedup_hash,
                TicketORM.created_at >= since_iso,
                TicketORM.status != "Anulado",
            )
            .order_by(desc(TicketORM.id))
        )
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None

    def create(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        now_dt = now_bogota()
        now_iso = ticket_data.get("created_at") or now_dt.isoformat()
        raw_code = str(ticket_data["ticket_number"]).strip().upper()
        try:
            fallback_seq = int(raw_code.rsplit("-", 1)[-1])
        except ValueError:
            fallback_seq = 1
        obj = TicketORM(
            ticket_number=raw_code,
            category_prefix=ticket_data.get("category_prefix")
            or get_service_prefix(ticket_data.get("service_name", "")),
            ticket_year=int(ticket_data.get("ticket_year") or now_dt.year),
            sequence_number=int(ticket_data.get("sequence_number") or fallback_seq),
            legacy_ticket_number=ticket_data.get("legacy_ticket_number"),
            content_dedup_hash=ticket_data.get("content_dedup_hash"),
            version=int(ticket_data.get("version", 1)),
            title=ticket_data["title"].strip(),
            description=ticket_data["description"].strip(),
            ticket_type=ticket_data["ticket_type"],
            service_name=ticket_data["service_name"],
            area=ticket_data["area"],
            sede=ticket_data["sede"],
            location=ticket_data["location"],
            impact=ticket_data["impact"],
            urgency=ticket_data["urgency"],
            priority=ticket_data["priority"],
            status=ticket_data["status"],
            requester_id=int(ticket_data["requester_id"]),
            requester_email=ticket_data["requester_email"],
            requester_role=ticket_data["requester_role"],
            assigned_tech_id=ticket_data.get("assigned_tech_id"),
            assigned_tech_email=ticket_data.get("assigned_tech_email"),
            sla_response_hours=float(ticket_data["sla_response_hours"]),
            sla_resolution_hours=float(ticket_data["sla_resolution_hours"]),
            response_deadline=ticket_data.get("response_deadline"),
            resolution_deadline=ticket_data.get("resolution_deadline"),
            first_response_at=ticket_data.get("first_response_at"),
            paused_at=ticket_data.get("paused_at"),
            paused_seconds=int(ticket_data.get("paused_seconds", 0)),
            resolved_at=ticket_data.get("resolved_at"),
            closed_at=ticket_data.get("closed_at"),
            diagnosis=ticket_data.get("diagnosis"),
            solution=ticket_data.get("solution"),
            closing_category=ticket_data.get("closing_category"),
            csat_score=ticket_data.get("csat_score"),
            csat_comment=ticket_data.get("csat_comment"),
            ai_suggested_service=ticket_data.get("ai_suggested_service"),
            ai_confidence=ticket_data.get("ai_confidence"),
            ai_human_validated=bool(ticket_data.get("ai_human_validated", False)),
            priority_justification=ticket_data.get("priority_justification"),
            sla_breached=bool(ticket_data.get("sla_breached", False)),
            sla_alert_75_sent=bool(ticket_data.get("sla_alert_75_sent", False)),
            created_at=now_iso,
            updated_at=ticket_data.get("updated_at") or now_iso,
        )
        self.session.add(obj)
        self.session.flush()
        return model_to_dict(obj)

    def get_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        obj = self.session.get(TicketORM, int(ticket_id))
        return model_to_dict(obj) if obj is not None else None

    def get_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        code = (ticket_number or "").strip().upper()
        if not code:
            return None
        stmt = select(TicketORM).where(
            or_(
                func.upper(TicketORM.ticket_number) == code,
                func.upper(TicketORM.legacy_ticket_number) == code,
            )
        )
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None

    def update(
        self, ticket_id: int, updates: Dict[str, Any], *, expected_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        payload = {k: v for k, v in dict(updates).items() if k in _ALLOWED_TICKET_UPDATES}
        payload.setdefault("updated_at", now_bogota().isoformat())

        if expected_version is not None:
            result = self.session.execute(
                update(TicketORM)
                .where(TicketORM.id == int(ticket_id), TicketORM.version == int(expected_version))
                .values(**payload, version=TicketORM.version + 1)
            )
            self.session.flush()
            if (result.rowcount or 0) == 0:
                existing = self.session.scalar(
                    select(TicketORM).where(TicketORM.id == int(ticket_id)).execution_options(populate_existing=True)
                )
                if existing is None:
                    return None
                raise ConflictError(
                    f"El ticket #{ticket_id} fue modificado por otra operación concurrente "
                    f"(versión esperada {expected_version}, versión actual {existing.version}). "
                    "Recargue el ticket e intente de nuevo.",
                    title="Conflicto de concurrencia optimista",
                )
            refreshed = self.session.scalar(
                select(TicketORM).where(TicketORM.id == int(ticket_id)).execution_options(populate_existing=True)
            )
            return model_to_dict(refreshed) if refreshed is not None else None

        obj = self.session.get(TicketORM, int(ticket_id))
        if obj is None:
            return None
        for key, value in payload.items():
            setattr(obj, key, value)
        obj.version = int(obj.version or 1) + 1
        self.session.flush()
        return model_to_dict(obj)
