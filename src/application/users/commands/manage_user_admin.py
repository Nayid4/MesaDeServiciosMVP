"""Caso de uso CQRS administrativo para gestión de roles, áreas, sedes y estado activo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command, sanitize_user_dict
from src.domain.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.domain.ports import IUnitOfWork
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS, UPC_SEDES

VALID_ROLES = {"usuario", "tecnico", "coordinador", "director", "admin"}


@dataclass(frozen=True)
class ManageUserAdminCommand(Command):
    actor_id: int
    actor_email: str
    actor_role: str
    target_user_id: int
    role: Optional[str] = None
    area: Optional[str] = None
    sede: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    ip_address: str = "127.0.0.1"


class ManageUserAdminCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: ManageUserAdminCommand) -> Dict[str, Any]:
        if cmd.actor_role != "admin":
            raise ForbiddenError("Solo el rol Administrador puede gestionar usuarios y roles.")

        updates: Dict[str, Any] = {}
        if cmd.role is not None:
            clean_role = cmd.role.strip().lower()
            if clean_role not in VALID_ROLES:
                raise ValidationError(f"Rol inválido: '{clean_role}'.")
            updates["role"] = clean_role
        if cmd.area is not None:
            updates["area"] = cmd.area.strip() or None
        if cmd.sede is not None:
            clean_sede = cmd.sede.strip()
            if clean_sede not in UPC_SEDES:
                raise ValidationError(f"Sede inválida: '{clean_sede}'.")
            updates["sede"] = clean_sede
        if cmd.is_active is not None:
            updates["is_active"] = bool(cmd.is_active)
        if cmd.full_name is not None:
            clean_name = cmd.full_name.strip()
            if len(clean_name) < 3:
                raise ValidationError("El nombre debe tener mínimo 3 caracteres.")
            updates["full_name"] = clean_name
        if not updates:
            raise ValidationError("Debe especificar al menos un cambio sobre el usuario.")

        with self._uow_factory() as uow:
            target = uow.users.get_by_id(cmd.target_user_id)
            if not target:
                raise NotFoundError("Usuario destino no encontrado.")

            new_role = updates.get("role", target["role"])
            new_active = updates.get("is_active", bool(target.get("is_active", True)))
            if target["role"] == "admin" and (new_role != "admin" or not new_active):
                if uow.users.count_active_admins() <= 1:
                    raise ConflictError(
                        "No puede desactivar ni retirar el rol al último Administrador activo del sistema."
                    )

            updated = uow.users.update(cmd.target_user_id, updates)
            assert updated is not None
            if not new_active:
                uow.refresh_tokens.revoke_all_for_user(cmd.target_user_id)

            uow.audit_logs.append(
                {
                    "user_email": cmd.actor_email,
                    "ip_address": cmd.ip_address,
                    "action": "USER_ADMIN_UPDATED",
                    "entity": "users",
                    "entity_id": str(cmd.target_user_id),
                    "old_value": f"role={target['role']}, area={target.get('area')}, active={target.get('is_active')}",
                    "new_value": f"role={updated['role']}, area={updated.get('area')}, active={updated.get('is_active')}",
                }
            )
            uow.commit()

        clean = sanitize_user_dict(updated)
        clean["role_label"] = ROLE_LABELS.get(clean["role"], clean["role"])
        clean["permissions"] = sorted(ROLE_PERMISSIONS.get(clean["role"], set()))
        return {"user": clean}
