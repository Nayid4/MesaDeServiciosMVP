"""Caso de uso CQRS de autorregistro de usuario institucional @unicesar.edu.co."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from src.application.common import Command, sanitize_user_dict
from src.domain.exceptions import ConflictError, ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS, is_valid_institutional_email
from src.infrastructure.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    generate_refresh_token,
    hash_password,
)


@dataclass(frozen=True)
class RegisterInstitutionalUserCommand(Command):
    email: str
    full_name: str
    password: str
    sede: str
    privacy_accepted: bool
    ip_address: str = "127.0.0.1"


class RegisterInstitutionalUserCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: RegisterInstitutionalUserCommand) -> Dict[str, Any]:
        normalized_email = (cmd.email or "").strip().lower()
        if not is_valid_institutional_email(normalized_email):
            raise ValidationDomainError("El correo debe pertenecer al dominio @unicesar.edu.co.")
        if not cmd.full_name or len(cmd.full_name.strip()) < 3:
            raise ValidationDomainError("Debe ingresar su nombre completo (mínimo 3 caracteres).")
        if not cmd.password or len(cmd.password) < 8:
            raise ValidationDomainError("La contraseña debe tener al menos 8 caracteres.")
        if not cmd.privacy_accepted:
            raise ValidationDomainError(
                "Debe aceptar el aviso de privacidad institucional (Ley 1581 de 2012)."
            )

        with self._uow_factory() as uow:
            if uow.users.get_by_email(normalized_email):
                raise ConflictError("Ya existe una cuenta registrada con este correo institucional.")

            created = uow.users.create(
                {
                    "email": normalized_email,
                    "full_name": cmd.full_name.strip(),
                    "password_hash": hash_password(cmd.password),
                    "role": "usuario",
                    "area": None,
                    "sede": cmd.sede,
                    "is_active": True,
                    "privacy_accepted": True,
                }
            )
            access_token = create_access_token(created)
            raw_refresh, token_hash, expires_at = generate_refresh_token()
            uow.refresh_tokens.create(int(created["id"]), token_hash, expires_at)
            uow.audit_logs.append(
                {
                    "user_email": normalized_email,
                    "ip_address": cmd.ip_address,
                    "action": "USER_SELF_REGISTERED",
                    "entity": "users",
                    "entity_id": str(created["id"]),
                    "new_value": f"Sede={cmd.sede}",
                }
            )
            uow.commit()

        clean_user = sanitize_user_dict(created)
        clean_user["role_label"] = ROLE_LABELS.get(clean_user["role"], clean_user["role"])
        clean_user["permissions"] = sorted(ROLE_PERMISSIONS.get(clean_user["role"], set()))
        return {
            "user": clean_user,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in_seconds": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
