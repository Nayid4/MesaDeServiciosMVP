"""Mixin SQLAlchemy para chat multimedia, versionado y adjuntos de tickets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, func, select, update

from src.infrastructure.persistence.models import (
    MessageVersionORM,
    TicketAttachmentORM,
    TicketMessageORM,
)
from src.infrastructure.persistence.repositories.base import model_to_dict
from src.infrastructure.security import build_signed_attachment_url


class TicketCommsMixin:
    """Provee operaciones de mensajería y adjuntos para SqlAlchemyTicketRepo."""

    session: Any

    def _serialize_attachment(
        self, obj: TicketAttachmentORM, *, include_internal: bool = False
    ) -> Dict[str, Any]:
        data = {
            "id": obj.id,
            "ticket_id": obj.ticket_id,
            "message_id": obj.message_id,
            "uploader_id": obj.uploader_id,
            "uploader_email": obj.uploader_email,
            "original_name": obj.original_name,
            "mime_type": obj.mime_type,
            "size_bytes": obj.size_bytes,
            "sha256_hash": obj.sha256_hash,
            "is_audio": bool(obj.is_audio),
            "duration_seconds": obj.duration_seconds,
            "created_at": obj.created_at,
            "signed_download_url": build_signed_attachment_url(obj.ticket_id, obj.id),
        }
        if include_internal:
            data["stored_name"] = obj.stored_name
            data["storage_rel_path"] = obj.storage_rel_path
        return data

    def _serialize_message(
        self, obj: TicketMessageORM, attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        d = model_to_dict(obj)
        d["message_id"] = d["id"]
        if d.get("is_deleted"):
            d["message"] = "Este mensaje fue eliminado"
            d["attachments"] = []
        else:
            d["attachments"] = list(attachments or [])
        return d

    def _attachments_for_message(self, message_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(TicketAttachmentORM)
            .where(TicketAttachmentORM.message_id == int(message_id))
            .order_by(asc(TicketAttachmentORM.id))
        )
        return [self._serialize_attachment(a) for a in self.session.scalars(stmt).all()]

    def add_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc).isoformat()
        created_at = message_data.get("created_at") or now_utc
        obj = TicketMessageORM(
            ticket_id=int(message_data["ticket_id"]),
            sender_id=int(message_data["sender_id"]),
            sender_email=message_data["sender_email"],
            sender_role=message_data["sender_role"],
            client_message_id=(message_data.get("client_message_id") or None),
            reply_to_message_id=message_data.get("reply_to_message_id"),
            message_type=message_data.get("message_type") or "text",
            message=message_data["message"].strip(),
            attachment_name=message_data.get("attachment_name"),
            attachment_path=message_data.get("attachment_path"),
            is_read=bool(message_data.get("is_read", False)),
            delivered_at=message_data.get("delivered_at") or created_at,
            read_at=message_data.get("read_at"),
            edited_at=message_data.get("edited_at"),
            is_deleted=bool(message_data.get("is_deleted", False)),
            created_at=created_at,
        )
        self.session.add(obj)
        self.session.flush()
        return self._serialize_message(obj, [])

    def get_messages(self, ticket_id: int, *, after_id: int = 0) -> List[Dict[str, Any]]:
        stmt = (
            select(TicketMessageORM)
            .where(
                TicketMessageORM.ticket_id == int(ticket_id),
                TicketMessageORM.id > int(after_id),
            )
            .order_by(asc(TicketMessageORM.id))
        )
        msgs = self.session.scalars(stmt).all()
        if not msgs:
            return []
        msg_ids = [m.id for m in msgs]
        att_stmt = (
            select(TicketAttachmentORM)
            .where(TicketAttachmentORM.message_id.in_(msg_ids))
            .order_by(asc(TicketAttachmentORM.id))
        )
        atts_by_msg: Dict[int, List[Dict[str, Any]]] = {}
        for att in self.session.scalars(att_stmt).all():
            atts_by_msg.setdefault(att.message_id, []).append(self._serialize_attachment(att))
        return [self._serialize_message(m, atts_by_msg.get(m.id, [])) for m in msgs]

    def get_message_by_id(self, ticket_id: int, message_id: int) -> Optional[Dict[str, Any]]:
        stmt = select(TicketMessageORM).where(
            TicketMessageORM.ticket_id == int(ticket_id),
            TicketMessageORM.id == int(message_id),
        )
        obj = self.session.scalars(stmt).first()
        if obj is None:
            return None
        return self._serialize_message(obj, self._attachments_for_message(obj.id))

    def get_message_by_client_id(
        self, ticket_id: int, sender_id: int, client_message_id: str
    ) -> Optional[Dict[str, Any]]:
        clean = (client_message_id or "").strip()
        if not clean:
            return None
        stmt = select(TicketMessageORM).where(
            TicketMessageORM.ticket_id == int(ticket_id),
            TicketMessageORM.sender_id == int(sender_id),
            TicketMessageORM.client_message_id == clean,
        )
        obj = self.session.scalars(stmt).first()
        if obj is None:
            return None
        return self._serialize_message(obj, self._attachments_for_message(obj.id))

    def update_message(self, message_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        obj = self.session.get(TicketMessageORM, int(message_id))
        if obj is None:
            return None
        allowed = {"message", "edited_at", "is_deleted", "is_read", "read_at", "delivered_at"}
        for key, value in updates.items():
            if key in allowed:
                setattr(obj, key, value)
        self.session.flush()
        return self._serialize_message(obj, self._attachments_for_message(obj.id))

    def add_message_version(self, version_data: Dict[str, Any]) -> Dict[str, Any]:
        obj = MessageVersionORM(
            message_id=int(version_data["message_id"]),
            ticket_id=int(version_data["ticket_id"]),
            version_number=int(version_data["version_number"]),
            previous_content=version_data["previous_content"],
            action=version_data.get("action", "edit"),
            actor_email=version_data["actor_email"],
            created_at=version_data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(obj)
        self.session.flush()
        return model_to_dict(obj)

    def get_message_versions(self, message_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(MessageVersionORM)
            .where(MessageVersionORM.message_id == int(message_id))
            .order_by(asc(MessageVersionORM.version_number))
        )
        return [model_to_dict(v) for v in self.session.scalars(stmt).all()]

    def add_attachment(self, attachment_data: Dict[str, Any]) -> Dict[str, Any]:
        obj = TicketAttachmentORM(
            ticket_id=int(attachment_data["ticket_id"]),
            message_id=int(attachment_data["message_id"]),
            uploader_id=int(attachment_data["uploader_id"]),
            uploader_email=attachment_data["uploader_email"],
            original_name=attachment_data["original_name"],
            stored_name=attachment_data["stored_name"],
            storage_rel_path=attachment_data["storage_rel_path"],
            mime_type=attachment_data["mime_type"],
            size_bytes=int(attachment_data["size_bytes"]),
            sha256_hash=attachment_data["sha256_hash"],
            is_audio=bool(attachment_data.get("is_audio", False)),
            duration_seconds=attachment_data.get("duration_seconds"),
            created_at=attachment_data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(obj)
        self.session.flush()
        return self._serialize_attachment(obj)

    def get_attachment_by_id(self, ticket_id: int, attachment_id: int) -> Optional[Dict[str, Any]]:
        stmt = select(TicketAttachmentORM).where(
            TicketAttachmentORM.ticket_id == int(ticket_id),
            TicketAttachmentORM.id == int(attachment_id),
        )
        obj = self.session.scalars(stmt).first()
        return self._serialize_attachment(obj, include_internal=True) if obj is not None else None

    def list_attachments_for_ticket(self, ticket_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(TicketAttachmentORM)
            .where(TicketAttachmentORM.ticket_id == int(ticket_id))
            .order_by(asc(TicketAttachmentORM.id))
        )
        return [self._serialize_attachment(a) for a in self.session.scalars(stmt).all()]

    def mark_messages_read(self, ticket_id: int, reader_email: str) -> List[int]:
        clean_reader = (reader_email or "").strip().lower()
        target_ids = list(
            self.session.scalars(
                select(TicketMessageORM.id).where(
                    TicketMessageORM.ticket_id == int(ticket_id),
                    func.lower(TicketMessageORM.sender_email) != clean_reader,
                    TicketMessageORM.is_read.is_(False),
                )
            ).all()
        )
        if not target_ids:
            return []
        now_utc = datetime.now(timezone.utc).isoformat()
        self.session.execute(
            update(TicketMessageORM)
            .where(TicketMessageORM.id.in_(target_ids))
            .values(is_read=True, read_at=now_utc)
        )
        self.session.flush()
        return [int(mid) for mid in target_ids]
