"""Consultas CQRS de perfil actual y usuarios demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from src.application.common import Query, sanitize_user_dict
from src.application.users.commands.login import is_demo_mode_enabled
from src.domain.exceptions import NotFoundError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS


@dataclass(frozen=True)
class GetMeQuery(Query):
    user_id: int


@dataclass(frozen=True)
class GetCurrentProfileQuery(Query):
    user_id: int


@dataclass(frozen=True)
class ListDemoUsersQuery(Query):
    pass


class GetMeQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetMeQuery) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            user = uow.users.get_by_id(query.user_id)
            if not user:
                raise NotFoundError("Usuario no encontrado.")
            notifications = uow.notifications.list_for_user(user["email"], unread_only=False)
            prefs = uow.notifications.get_preferences(user["email"])

        clean_user = sanitize_user_dict(user)
        clean_user["role_label"] = ROLE_LABELS.get(clean_user["role"], clean_user["role"])
        clean_user["permissions"] = sorted(ROLE_PERMISSIONS.get(clean_user["role"], set()))
        return {
            "user": clean_user,
            "notifications": notifications,
            "unread_count": sum(1 for n in notifications if not n.get("is_read")),
            "notification_preferences": prefs,
        }


class GetCurrentProfileQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, query: GetCurrentProfileQuery) -> Dict[str, Any]:
        return GetMeQueryHandler(self._uow_factory).handle(GetMeQuery(user_id=query.user_id))


class ListDemoUsersQueryHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, _query: ListDemoUsersQuery) -> List[Dict[str, Any]]:
        if not is_demo_mode_enabled():
            return []
        demo_emails = [
            "estudiante@unicesar.edu.co",
            "docente@unicesar.edu.co",
            "tecnico1@unicesar.edu.co",
            "tecnico2@unicesar.edu.co",
            "coordinador@unicesar.edu.co",
            "admin@unicesar.edu.co",
        ]
        with self._uow_factory() as uow:
            all_users = {u["email"]: u for u in uow.users.list_users(is_active=True)}
        items = []
        for email in demo_emails:
            if email in all_users:
                u = sanitize_user_dict(all_users[email])
                u["role_label"] = ROLE_LABELS.get(u["role"], u["role"])
                u["is_fictitious_demo"] = True
                items.append(u)
        return items
