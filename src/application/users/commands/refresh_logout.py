"""Casos de uso CQRS de rotación estricta de Refresh Token y cierre de sesión."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command, sanitize_user_dict
from src.domain.exceptions import ForbiddenError, UnauthorizedError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS
from src.infrastructure.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


@dataclass(frozen=True)
class RefreshTokenCommand(Command):
    refresh_token: str
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class LogoutCommand(Command):
    refresh_token: Optional[str] = None
    user_email: str = "anon@unicesar.edu.co"
    ip_address: str = "127.0.0.1"


class RefreshTokenCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: RefreshTokenCommand) -> Dict[str, Any]:
        if not cmd.refresh_token or not cmd.refresh_token.strip():
            raise UnauthorizedError("Refresh token ausente.")

        old_hash = hash_refresh_token(cmd.refresh_token.strip())
        with self._uow_factory() as uow:
            record = uow.refresh_tokens.get_valid(old_hash)
            if not record:
                raise UnauthorizedError("Refresh token inválido, expirado o ya revocado.")

            user = uow.users.get_by_id(int(record["user_id"]))
            if not user or not bool(user.get("is_active", True)):
                uow.refresh_tokens.revoke(old_hash)
                uow.commit()
                raise ForbiddenError("Usuario asociado inactivo o inexistente.")

            uow.refresh_tokens.revoke(old_hash)
            new_access = create_access_token(user)
            new_raw_refresh, new_hash, new_exp = generate_refresh_token()
            uow.refresh_tokens.create(int(user["id"]), new_hash, new_exp)
            uow.audit_logs.append(
                {
                    "user_email": user["email"],
                    "ip_address": cmd.ip_address,
                    "action": "TOKEN_REFRESH_ROTATION",
                    "entity": "auth",
                    "entity_id": str(user["id"]),
                    "new_value": "Refresh token rotado exitosamente",
                }
            )
            uow.commit()

        clean_user = sanitize_user_dict(user)
        clean_user["role_label"] = ROLE_LABELS.get(clean_user["role"], clean_user["role"])
        clean_user["permissions"] = sorted(ROLE_PERMISSIONS.get(clean_user["role"], set()))
        return {
            "user": clean_user,
            "access_token": new_access,
            "refresh_token": new_raw_refresh,
            "token_type": "bearer",
            "expires_in_seconds": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }


class LogoutCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: LogoutCommand) -> Dict[str, Any]:
        with self._uow_factory() as uow:
            if cmd.refresh_token:
                uow.refresh_tokens.revoke(hash_refresh_token(cmd.refresh_token.strip()))
            uow.audit_logs.append(
                {
                    "user_email": cmd.user_email,
                    "ip_address": cmd.ip_address,
                    "action": "LOGOUT",
                    "entity": "auth",
                    "entity_id": cmd.user_email,
                    "new_value": "Sesión cerrada y refresh token revocado",
                }
            )
            uow.commit()
        return {"status": "logged_out"}
