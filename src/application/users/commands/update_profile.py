"""Caso de uso CQRS para actualización del perfil personal (nombre y sede)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command, sanitize_user_dict
from src.domain.exceptions import NotFoundError, ValidationError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS, UPC_SEDES


@dataclass(frozen=True)
class UpdateProfileCommand(Command):
    user_id: int
    full_name: str
    sede: Optional[str] = None
    ip_address: str = "127.0.0.1"


class UpdateProfileCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: UpdateProfileCommand) -> Dict[str, Any]:
        clean_name = (cmd.full_name or "").strip()
        if len(clean_name) < 3:
            raise ValidationError("El nombre completo debe contener al menos 3 caracteres.")

        updates: Dict[str, Any] = {"full_name": clean_name}
        if cmd.sede is not None:
            clean_sede = cmd.sede.strip()
            if clean_sede not in UPC_SEDES:
                raise ValidationError(f"Sede inválida: '{clean_sede}'.")
            updates["sede"] = clean_sede

        with self._uow_factory() as uow:
            current = uow.users.get_by_id(cmd.user_id)
            if not current:
                raise NotFoundError("Usuario no encontrado.")

            updated = uow.users.update(cmd.user_id, updates)
            assert updated is not None
            uow.audit_logs.append(
                {
                    "user_email": current["email"],
                    "ip_address": cmd.ip_address,
                    "action": "PROFILE_UPDATED",
                    "entity": "users",
                    "entity_id": str(cmd.user_id),
                    "old_value": f"name={current['full_name']}, sede={current.get('sede')}",
                    "new_value": f"name={updated['full_name']}, sede={updated.get('sede')}",
                }
            )
            uow.commit()

        clean = sanitize_user_dict(updated)
        clean["role_label"] = ROLE_LABELS.get(clean["role"], clean["role"])
        clean["permissions"] = sorted(ROLE_PERMISSIONS.get(clean["role"], set()))
        return {"user": clean}
