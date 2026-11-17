"""Caso de uso CQRS de cambio seguro de contraseña con revocación de sesiones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from src.application.common import Command
from src.domain.exceptions import NotFoundError, UnauthorizedError, ValidationError
from src.domain.ports import IUnitOfWork
from src.infrastructure.security import (
    hash_password,
    validate_password_complexity,
    verify_password,
)


@dataclass(frozen=True)
class ChangePasswordCommand(Command):
    user_id: int
    current_password: str
    new_password: str
    ip_address: str = "127.0.0.1"


class ChangePasswordCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: ChangePasswordCommand) -> Dict[str, Any]:
        validate_password_complexity(cmd.new_password)
        with self._uow_factory() as uow:
            user = uow.users.get_by_id(cmd.user_id)
            if not user:
                raise NotFoundError("Usuario no encontrado.")
            if not verify_password(cmd.current_password or "", user.get("password_hash") or ""):
                raise UnauthorizedError("La contraseña actual ingresada es incorrecta.")
            if verify_password(cmd.new_password, user.get("password_hash") or ""):
                raise ValidationError("La nueva contraseña debe ser diferente a la contraseña actual.")

            uow.users.update(cmd.user_id, {"password_hash": hash_password(cmd.new_password)})
            uow.refresh_tokens.revoke_all_for_user(cmd.user_id)
            uow.audit_logs.append(
                {
                    "user_email": user["email"],
                    "ip_address": cmd.ip_address,
                    "action": "PASSWORD_CHANGED",
                    "entity": "users",
                    "entity_id": str(cmd.user_id),
                    "new_value": "Contraseña actualizada y tokens de sesión revocados",
                }
            )
            uow.commit()

        return {"status": "password_updated", "sessions_revoked": True}
