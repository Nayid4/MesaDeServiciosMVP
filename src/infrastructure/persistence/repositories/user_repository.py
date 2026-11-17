"""Repositorios SQLAlchemy de usuarios, refresh tokens y recuperación de contraseña."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.orm import Session

from src.domain.common.pagination import PageRequest, PagedResult
from src.domain.ports import IPasswordResetTokenRepo, IRefreshTokenRepo, IUserRepo
from src.domain.rules import ASSIGNED_LOAD_STATUSES, now_bogota
from src.infrastructure.persistence.models import (
    PasswordResetTokenORM,
    RefreshTokenORM,
    TicketORM,
    UserORM,
)
from src.infrastructure.persistence.repositories.base import (
    execute_paginated_query,
    model_to_dict,
)


class SqlAlchemyUserRepo(IUserRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        obj = self.session.get(UserORM, int(user_id))
        return model_to_dict(obj) if obj is not None else None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        normalized = (email or "").strip().lower()
        stmt = select(UserORM).where(func.lower(UserORM.email) == normalized)
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None

    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        obj = UserORM(
            email=user_data["email"].strip().lower(),
            full_name=user_data["full_name"].strip(),
            password_hash=user_data["password_hash"],
            role=user_data.get("role", "usuario"),
            area=user_data.get("area"),
            sede=user_data.get("sede", "Sede Sabanas (Valledupar)"),
            is_active=bool(user_data.get("is_active", True)),
            privacy_accepted=bool(user_data.get("privacy_accepted", True)),
            last_assigned_at=user_data.get("last_assigned_at"),
            created_at=user_data.get("created_at") or now_bogota().isoformat(),
        )
        self.session.add(obj)
        self.session.flush()
        return model_to_dict(obj)

    def update(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        obj = self.session.get(UserORM, int(user_id))
        if obj is None:
            return None
        allowed = {
            "full_name",
            "password_hash",
            "role",
            "area",
            "sede",
            "is_active",
            "privacy_accepted",
            "last_assigned_at",
        }
        for key, value in updates.items():
            if key in allowed:
                setattr(obj, key, value)
        self.session.flush()
        return model_to_dict(obj)

    def _build_filtered_stmt(
        self,
        *,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Any:
        stmt = select(UserORM)
        if role:
            stmt = stmt.where(UserORM.role == role)
        if area:
            stmt = stmt.where(UserORM.area == area)
        if is_active is not None:
            stmt = stmt.where(UserORM.is_active == bool(is_active))
        if search:
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(UserORM.full_name).like(like),
                    func.lower(UserORM.email).like(like),
                )
            )
        return stmt.order_by(asc(UserORM.id))

    def list_users(
        self,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            role=role, area=area, is_active=is_active, search=search
        )
        return [model_to_dict(u) for u in self.session.scalars(stmt).all()]

    def list_users_paginated(
        self,
        page_request: PageRequest,
        *,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PagedResult[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            role=role, area=area, is_active=is_active, search=search
        )
        return execute_paginated_query(self.session, stmt, UserORM.id, page_request)

    def list_active_technicians_with_load(self, area: str) -> List[Dict[str, Any]]:
        load_subq = (
            select(
                TicketORM.assigned_tech_id.label("tech_id"),
                func.count(TicketORM.id).label("open_tickets_count"),
            )
            .where(TicketORM.status.in_(ASSIGNED_LOAD_STATUSES))
            .group_by(TicketORM.assigned_tech_id)
            .subquery()
        )
        stmt = (
            select(
                UserORM,
                func.coalesce(load_subq.c.open_tickets_count, 0).label("open_count"),
            )
            .outerjoin(load_subq, UserORM.id == load_subq.c.tech_id)
            .where(
                UserORM.role == "tecnico",
                UserORM.is_active.is_(True),
                UserORM.area == area,
            )
            .order_by(asc(UserORM.id))
        )
        results: List[Dict[str, Any]] = []
        for user_obj, open_count in self.session.execute(stmt).all():
            item = model_to_dict(user_obj)
            item["open_tickets_count"] = int(open_count or 0)
            results.append(item)
        return results

    def count_active_admins(self) -> int:
        stmt = select(func.count(UserORM.id)).where(
            UserORM.role == "admin",
            UserORM.is_active.is_(True),
        )
        return int(self.session.scalar(stmt) or 0)


class SqlAlchemyRefreshTokenRepo(IRefreshTokenRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: int, token_hash: str, expires_at: str) -> None:
        obj = RefreshTokenORM(
            user_id=int(user_id),
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
            created_at=now_bogota().isoformat(),
        )
        self.session.add(obj)
        self.session.flush()

    def get_valid(self, token_hash: str) -> Optional[Dict[str, Any]]:
        now_utc = datetime.now(timezone.utc).isoformat()
        stmt = select(RefreshTokenORM).where(
            RefreshTokenORM.token_hash == token_hash,
            RefreshTokenORM.revoked.is_(False),
            RefreshTokenORM.expires_at > now_utc,
        )
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None

    def revoke(self, token_hash: str) -> None:
        stmt = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.token_hash == token_hash)
            .values(revoked=True)
        )
        self.session.execute(stmt)
        self.session.flush()

    def revoke_all_for_user(self, user_id: int) -> None:
        stmt = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == int(user_id))
            .values(revoked=True)
        )
        self.session.execute(stmt)
        self.session.flush()


class SqlAlchemyPasswordResetTokenRepo(IPasswordResetTokenRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: int, token_hash: str, expires_at: str) -> None:
        obj = PasswordResetTokenORM(
            user_id=int(user_id),
            token_hash=token_hash,
            expires_at=expires_at,
            consumed=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.session.add(obj)
        self.session.flush()

    def consume_valid(self, token_hash: str, now_iso: str) -> Optional[Dict[str, Any]]:
        obj = self.session.scalars(
            select(PasswordResetTokenORM)
            .where(
                PasswordResetTokenORM.token_hash == token_hash,
                PasswordResetTokenORM.consumed.is_(False),
                PasswordResetTokenORM.expires_at > now_iso,
            )
            .order_by(desc(PasswordResetTokenORM.id))
        ).first()
        if obj is None:
            return None
        res = self.session.execute(
            update(PasswordResetTokenORM)
            .where(
                PasswordResetTokenORM.id == obj.id,
                PasswordResetTokenORM.consumed.is_(False),
            )
            .values(consumed=True)
        )
        self.session.flush()
        if (res.rowcount or 0) != 1:
            return None
        data = model_to_dict(obj)
        data["consumed"] = True
        return data
