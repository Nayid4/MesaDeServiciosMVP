"""Caso de uso CQRS de inicio de sesión JWT + bitácora de auditoría."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command, sanitize_user_dict
from src.domain.exceptions import (
    ForbiddenError,
    UnauthorizedError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS, is_valid_institutional_email
from src.infrastructure.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    generate_refresh_token,
    verify_password,
)


def is_demo_mode_enabled() -> bool:
    """Retorna True únicamente si DEMO_MODE está habilitado explícitamente (apagado por defecto)."""
    return os.environ.get("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class LoginCommand(Command):
    email: str
    password: Optional[str] = None
    demo_mode: bool = False
    ip_address: str = "127.0.0.1"


class LoginCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: LoginCommand) -> Dict[str, Any]:
        if cmd.demo_mode and not is_demo_mode_enabled():
            raise ForbiddenError(
                "El acceso rápido de demostración está deshabilitado porque DEMO_MODE está apagado."
            )

        normalized_email = (cmd.email or "").strip().lower()
        if not is_valid_institutional_email(normalized_email):
            raise ValidationDomainError(
                "Solo se permite el acceso con correo institucional @unicesar.edu.co."
            )

        with self._uow_factory() as uow:
            user = uow.users.get_by_email(normalized_email)
            if not user:
                uow.audit_logs.append(
                    {
                        "user_email": normalized_email,
                        "ip_address": cmd.ip_address,
                        "action": "LOGIN_FAILED",
                        "entity": "auth",
                        "entity_id": normalized_email,
                        "new_value": "Usuario no registrado",
                    }
                )
                uow.commit()
                raise UnauthorizedError("Credenciales institucionales inválidas.")

            if not bool(user.get("is_active", True)):
                raise ForbiddenError(
                    "Su cuenta institucional se encuentra inactiva. Contacte al Administrador."
                )

            if not cmd.demo_mode and (
                not cmd.password or not verify_password(cmd.password, user.get("password_hash") or "")
            ):
                uow.audit_logs.append(
                    {
                        "user_email": normalized_email,
                        "ip_address": cmd.ip_address,
                        "action": "LOGIN_FAILED",
                        "entity": "auth",
                        "entity_id": normalized_email,
                        "new_value": "Contraseña incorrecta",
                    }
                )
                uow.commit()
                raise UnauthorizedError("Credenciales institucionales inválidas.")

            access_token = create_access_token(user)
            raw_refresh, token_hash, expires_at = generate_refresh_token()
            uow.refresh_tokens.create(int(user["id"]), token_hash, expires_at)
            uow.audit_logs.append(
                {
                    "user_email": normalized_email,
                    "ip_address": cmd.ip_address,
                    "action": "DEMO_QUICK_LOGIN" if cmd.demo_mode else "LOGIN_SUCCESS",
                    "entity": "auth",
                    "entity_id": str(user["id"]),
                    "new_value": f"Rol={user['role']}",
                }
            )
            uow.commit()

        clean_user = sanitize_user_dict(user)
        clean_user["role_label"] = ROLE_LABELS.get(clean_user["role"], clean_user["role"])
        clean_user["permissions"] = sorted(ROLE_PERMISSIONS.get(clean_user["role"], set()))
        return {
            "user": clean_user,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in_seconds": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
