"""Casos de uso CQRS de solicitud y confirmación de restablecimiento de contraseña (15 min)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from src.application.common import Command
from src.domain.exceptions import UnauthorizedError, ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import is_valid_institutional_email
from src.infrastructure.security import (
    PASSWORD_RESET_EXPIRE_MINUTES,
    generate_password_reset_token,
    hash_password,
    hash_password_reset_token,
    validate_password_complexity,
)

# Outbox en memoria para demostración / pruebas cuando no hay servidor SMTP externo
PASSWORD_RESET_OUTBOX: Dict[str, Dict[str, str]] = {}


@dataclass(frozen=True)
class RequestPasswordResetCommand(Command):
    email: str
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class ConfirmPasswordResetCommand(Command):
    token: str
    new_password: str
    ip_address: str = "127.0.0.1"


class RequestPasswordResetCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: RequestPasswordResetCommand) -> Dict[str, Any]:
        normalized = (cmd.email or "").strip().lower()
        if not is_valid_institutional_email(normalized):
            raise ValidationDomainError("Solo se admiten cuentas institucionales @unicesar.edu.co.")

        with self._uow_factory() as uow:
            user = uow.users.get_by_email(normalized)
            if user and bool(user.get("is_active", True)):
                raw_token, token_hash, expires_at = generate_password_reset_token(
                    minutes_valid=PASSWORD_RESET_EXPIRE_MINUTES
                )
                uow.password_reset_tokens.create(int(user["id"]), token_hash, expires_at)
                PASSWORD_RESET_OUTBOX[normalized] = {
                    "token": raw_token,
                    "expires_at": expires_at,
                    "reset_url": f"/reset-password?token={raw_token}",
                }
                uow.audit_logs.append(
                    {
                        "user_email": normalized,
                        "ip_address": cmd.ip_address,
                        "action": "PASSWORD_RESET_REQUESTED",
                        "entity": "users",
                        "entity_id": str(user["id"]),
                        "new_value": f"Enlace temporal emitido (vigencia {PASSWORD_RESET_EXPIRE_MINUTES} min)",
                    }
                )
            else:
                uow.audit_logs.append(
                    {
                        "user_email": normalized,
                        "ip_address": cmd.ip_address,
                        "action": "PASSWORD_RESET_REQUESTED_NOOP",
                        "entity": "users",
                        "entity_id": normalized,
                        "new_value": "Respuesta uniforme anti-enumeración",
                    }
                )
            uow.commit()

        return {
            "status": "accepted",
            "message": "Si el correo institucional existe y está activo, recibirá un enlace de recuperación válido por 15 minutos.",
            "expires_in_minutes": PASSWORD_RESET_EXPIRE_MINUTES,
        }


class ConfirmPasswordResetCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: ConfirmPasswordResetCommand) -> Dict[str, Any]:
        raw_token = (cmd.token or "").strip()
        if len(raw_token) < 16:
            raise UnauthorizedError("El token de recuperación es inválido o está incompleto.")
        validate_password_complexity(cmd.new_password)

        token_hash = hash_password_reset_token(raw_token)
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._uow_factory() as uow:
            record = uow.password_reset_tokens.consume_valid(token_hash, now_iso)
            if not record:
                raise UnauthorizedError("El enlace de recuperación es inválido, expiró o ya fue utilizado.")

            user_id = int(record["user_id"])
            user = uow.users.get_by_id(user_id)
            if not user or not bool(user.get("is_active", True)):
                raise UnauthorizedError("Cuenta institucional no disponible para restablecimiento.")

            uow.users.update(user_id, {"password_hash": hash_password(cmd.new_password)})
            uow.refresh_tokens.revoke_all_for_user(user_id)
            uow.audit_logs.append(
                {
                    "user_email": user["email"],
                    "ip_address": cmd.ip_address,
                    "action": "PASSWORD_RESET_CONFIRMED",
                    "entity": "users",
                    "entity_id": str(user_id),
                    "new_value": "Contraseña restablecida con token temporal de 15 min",
                }
            )
            uow.commit()

        return {"status": "password_reset_completed"}
