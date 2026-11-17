"""Repositorios SQLAlchemy de auditoría inmutable, notificaciones y catálogo SLA."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.orm import Session

from src.domain.ports import IAuditRepo, ICatalogRepo, INotificationRepo
from src.domain.rules import now_bogota
from src.infrastructure.persistence.models import (
    AuditLogORM,
    NotificationORM,
    SLAConfigORM,
    ServiceCatalogORM,
    UserNotificationPreferenceORM,
)
from src.infrastructure.persistence.repositories.base import model_to_dict


class SqlAlchemyAuditRepo(IAuditRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, log_data: Dict[str, Any]) -> None:
        self.session.add(
            AuditLogORM(
                timestamp=log_data.get("timestamp") or now_bogota().isoformat(),
                user_email=log_data["user_email"],
                ip_address=log_data.get("ip_address", "127.0.0.1"),
                action=log_data["action"],
                entity=log_data["entity"],
                entity_id=str(log_data["entity_id"]),
                old_value=log_data.get("old_value"),
                new_value=log_data.get("new_value"),
            )
        )
        self.session.flush()

    def list_logs(
        self, user_email: Optional[str] = None, action: Optional[str] = None, limit: int = 500
    ) -> List[Dict[str, Any]]:
        stmt = select(AuditLogORM)
        if user_email:
            stmt = stmt.where(
                func.lower(AuditLogORM.user_email).like(f"%{user_email.strip().lower()}%")
            )
        if action:
            stmt = stmt.where(func.upper(AuditLogORM.action).like(f"%{action.strip().upper()}%"))
        stmt = stmt.order_by(desc(AuditLogORM.id)).limit(limit)
        return [model_to_dict(r) for r in self.session.scalars(stmt).all()]


class SqlAlchemyNotificationRepo(INotificationRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_preferences(self, user_email: str) -> Dict[str, Any]:
        clean_email = (user_email or "").strip().lower()
        obj = self.session.get(UserNotificationPreferenceORM, clean_email)
        if obj is None:
            return {
                "user_email": clean_email,
                "notify_in_app": True,
                "notify_email_sim": True,
                "notify_ticket_updates": True,
                "notify_chat_messages": True,
                "notify_sla_alerts": True,
                "updated_at": None,
            }
        return model_to_dict(obj)

    def update_preferences(self, user_email: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        clean_email = (user_email or "").strip().lower()
        now_iso = now_bogota().isoformat()
        obj = self.session.get(UserNotificationPreferenceORM, clean_email)
        if obj is None:
            obj = UserNotificationPreferenceORM(
                user_email=clean_email,
                notify_in_app=bool(prefs.get("notify_in_app", True)),
                notify_email_sim=bool(prefs.get("notify_email_sim", True)),
                notify_ticket_updates=bool(prefs.get("notify_ticket_updates", True)),
                notify_chat_messages=bool(prefs.get("notify_chat_messages", True)),
                notify_sla_alerts=bool(prefs.get("notify_sla_alerts", True)),
                updated_at=now_iso,
            )
            self.session.add(obj)
        else:
            for field_name in (
                "notify_in_app",
                "notify_email_sim",
                "notify_ticket_updates",
                "notify_chat_messages",
                "notify_sla_alerts",
            ):
                if field_name in prefs:
                    setattr(obj, field_name, bool(prefs[field_name]))
            obj.updated_at = now_iso
        self.session.flush()
        return model_to_dict(obj)

    def create(self, notification_data: Dict[str, Any]) -> None:
        target_email = (notification_data["user_email"] or "").strip().lower()
        prefs = self.get_preferences(target_email)
        if not prefs.get("notify_in_app", True):
            return
        cat = (notification_data.get("category") or "").strip().lower()
        if cat == "chat" and not prefs.get("notify_chat_messages", True):
            return
        if cat == "status" and not prefs.get("notify_ticket_updates", True):
            return
        if cat == "sla" and not prefs.get("notify_sla_alerts", True):
            return

        self.session.add(
            NotificationORM(
                user_email=notification_data["user_email"],
                ticket_number=notification_data.get("ticket_number"),
                title=notification_data["title"],
                message=notification_data["message"],
                is_read=False,
                created_at=notification_data.get("created_at") or now_bogota().isoformat(),
            )
        )
        self.session.flush()

    def list_for_user(self, user_email: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        stmt = select(NotificationORM).where(
            func.lower(NotificationORM.user_email) == (user_email or "").strip().lower()
        )
        if unread_only:
            stmt = stmt.where(NotificationORM.is_read.is_(False))
        stmt = stmt.order_by(desc(NotificationORM.id)).limit(100)
        return [model_to_dict(n) for n in self.session.scalars(stmt).all()]

    def mark_all_read(self, user_email: str) -> None:
        self.session.execute(
            update(NotificationORM)
            .where(func.lower(NotificationORM.user_email) == (user_email or "").strip().lower())
            .values(is_read=True)
        )
        self.session.flush()

    def mark_read(self, user_email: str, notification_id: int) -> bool:
        res = self.session.execute(
            update(NotificationORM)
            .where(
                NotificationORM.id == int(notification_id),
                func.lower(NotificationORM.user_email) == (user_email or "").strip().lower(),
            )
            .values(is_read=True)
        )
        self.session.flush()
        return (res.rowcount or 0) > 0


class SqlAlchemyCatalogRepo(ICatalogRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_services(self, active_only: bool = False) -> List[Dict[str, Any]]:
        stmt = select(ServiceCatalogORM)
        if active_only:
            stmt = stmt.where(ServiceCatalogORM.is_active.is_(True))
        stmt = stmt.order_by(asc(ServiceCatalogORM.id))
        return [model_to_dict(s) for s in self.session.scalars(stmt).all()]

    def upsert_service(self, data: Dict[str, Any]) -> None:
        name = data["service_name"].strip()
        obj = self.session.scalars(
            select(ServiceCatalogORM).where(ServiceCatalogORM.service_name == name)
        ).first()
        if obj is not None:
            obj.area = data["area"]
            obj.base_impact = data["base_impact"]
            obj.default_type = data.get("default_type", "Incidencia")
            obj.description = data.get("description", "")
            obj.is_active = bool(data.get("is_active", True))
        else:
            self.session.add(
                ServiceCatalogORM(
                    service_name=name,
                    area=data["area"],
                    base_impact=data["base_impact"],
                    default_type=data.get("default_type", "Incidencia"),
                    description=data.get("description", ""),
                    is_active=bool(data.get("is_active", True)),
                )
            )
        self.session.flush()

    def get_sla_table(self) -> Dict[str, Dict[str, float]]:
        rows = self.session.scalars(select(SLAConfigORM)).all()
        return {
            r.priority: {
                "sla_response_hours": float(r.sla_response_hours),
                "sla_resolution_hours": float(r.sla_resolution_hours),
            }
            for r in rows
        }

    def update_sla(self, priority: str, response_hours: float, resolution_hours: float) -> None:
        if resolution_hours < response_hours:
            raise ValueError("El tiempo de resolución no puede ser menor al tiempo de respuesta.")
        obj = self.session.get(SLAConfigORM, priority)
        now_iso = now_bogota().isoformat()
        if obj is not None:
            obj.sla_response_hours = float(response_hours)
            obj.sla_resolution_hours = float(resolution_hours)
            obj.updated_at = now_iso
        else:
            self.session.add(
                SLAConfigORM(
                    priority=priority,
                    sla_response_hours=float(response_hours),
                    sla_resolution_hours=float(resolution_hours),
                    updated_at=now_iso,
                )
            )
        self.session.flush()
