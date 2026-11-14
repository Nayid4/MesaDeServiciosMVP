"""Casos de uso de autenticación, JWT + Refresh Token, RBAC y gestión de usuarios."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import jwt

from src.domain.repositories import (
    IAuditRepository,
    IRefreshTokenRepository,
    ITicketRepository,
    IUserRepository,
)
from src.domain.rules import (
    ROLE_PERMISSIONS,
    VALID_ROLES,
    is_valid_institutional_email,
)
from src.infrastructure.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from src.infrastructure.sqlite_repositories import (
    SQLiteAuditLogRepository,
    SQLiteRefreshTokenRepository,
    SQLiteTicketRepository,
    SQLiteUserRepository,
)


class AuthService:
    """Orquesta autenticación institucional, rotación de tokens y control RBAC."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        user_repo: Optional[IUserRepository] = None,
        token_repo: Optional[IRefreshTokenRepository] = None,
        ticket_repo: Optional[ITicketRepository] = None,
        audit_repo: Optional[IAuditRepository] = None,
    ):
        self.user_repo: IUserRepository = user_repo or SQLiteUserRepository(db_path)
        self.token_repo: IRefreshTokenRepository = token_repo or SQLiteRefreshTokenRepository(db_path)
        self.ticket_repo: ITicketRepository = ticket_repo or SQLiteTicketRepository(db_path)
        self.audit_repo: IAuditRepository = audit_repo or SQLiteAuditLogRepository(db_path)

    def _issue_session_tokens(self, user: Dict[str, Any]) -> Dict[str, Any]:
        access_token = create_access_token(user)
        raw_refresh, refresh_hash, expires_at = generate_refresh_token()
        self.token_repo.create(user["id"], refresh_hash, expires_at)
        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return {
            "user": safe_user,
            "access_token": access_token,
            "refresh_token": raw_refresh,
        }

    def login(self, email: str, password: str, ip_address: str = "127.0.0.1") -> Dict[str, Any]:
        normalized_email = (email or "").strip().lower()
        if not is_valid_institutional_email(normalized_email):
            raise ValueError("Solo se permite el ingreso con cuentas institucionales (@unicesar.edu.co).")

        user = self.user_repo.get_by_email(normalized_email)
        if not user or not verify_password(password, user.get("password_hash", "")):
            self.audit_repo.append(
                {
                    "user_email": normalized_email or "desconocido",
                    "ip_address": ip_address,
                    "action": "LOGIN_FAILED",
                    "entity": "auth",
                    "entity_id": normalized_email,
                    "new_value": "Credenciales inválidas",
                }
            )
            raise ValueError("Correo o contraseña institucional incorrectos.")

        if not user.get("is_active", True):
            self.audit_repo.append(
                {
                    "user_email": normalized_email,
                    "ip_address": ip_address,
                    "action": "LOGIN_BLOCKED_INACTIVE",
                    "entity": "user",
                    "entity_id": str(user["id"]),
                    "new_value": "Cuenta inactiva",
                }
            )
            raise PermissionError(
                "Su cuenta está inactiva. Comuníquese con la Oficina de Informática y Sistemas."
            )

        session = self._issue_session_tokens(user)
        self.audit_repo.append(
            {
                "user_email": normalized_email,
                "ip_address": ip_address,
                "action": "LOGIN_SUCCESS",
                "entity": "auth",
                "entity_id": str(user["id"]),
                "new_value": f"Rol: {user['role']}",
            }
        )
        return session

    def register_institutional_user(
        self,
        email: str,
        full_name: str,
        password: str,
        sede: str,
        privacy_accepted: bool,
        ip_address: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        normalized_email = (email or "").strip().lower()
        if not is_valid_institutional_email(normalized_email):
            raise ValueError("Solo se permiten cuentas del dominio institucional @unicesar.edu.co.")
        if not full_name or len(full_name.strip()) < 4:
            raise ValueError("Ingrese su nombre completo (mínimo 4 caracteres).")
        if not password or len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if not privacy_accepted:
            raise ValueError(
                "Debe aceptar la política de tratamiento de datos personales (Ley 1581 de 2012)."
            )
        if self.user_repo.get_by_email(normalized_email):
            raise ValueError("Ya existe una cuenta registrada con ese correo institucional.")

        created = self.user_repo.create(
            {
                "email": normalized_email,
                "full_name": full_name.strip(),
                "password_hash": hash_password(password),
                "role": "usuario",
                "area": None,
                "sede": sede,
                "is_active": True,
                "privacy_accepted": True,
            }
        )
        self.audit_repo.append(
            {
                "user_email": normalized_email,
                "ip_address": ip_address,
                "action": "USER_SELF_REGISTERED",
                "entity": "user",
                "entity_id": str(created["id"]),
                "new_value": f"Sede: {sede}, Ley 1581 aceptada",
            }
        )
        return self._issue_session_tokens(created)

    def verify_or_refresh_session(
        self,
        access_token: Optional[str],
        refresh_token: Optional[str],
    ) -> Dict[str, Any]:
        """
        Valida el JWT Access Token. Si expiró, intenta rotación silenciosa con el Refresh Token.
        """
        if not access_token:
            return {"valid": False, "reason": "Sesión no iniciada."}

        try:
            claims = decode_access_token(access_token)
            user = self.user_repo.get_by_id(int(claims["sub"]))
            if not user or not user.get("is_active"):
                return {"valid": False, "reason": "Usuario inactivo o inexistente."}
            safe_user = {k: v for k, v in user.items() if k != "password_hash"}
            return {
                "valid": True,
                "refreshed": False,
                "user": safe_user,
                "claims": claims,
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        except jwt.ExpiredSignatureError:
            if not refresh_token:
                return {"valid": False, "reason": "Token expirado sin refresh token."}

            token_hash = hash_refresh_token(refresh_token)
            stored = self.token_repo.get_valid(token_hash)
            if not stored:
                return {"valid": False, "reason": "Refresh token inválido, expirado o revocado."}

            user = self.user_repo.get_by_id(int(stored["user_id"]))
            if not user or not user.get("is_active"):
                self.token_repo.revoke(token_hash)
                return {"valid": False, "reason": "Usuario inactivo."}

            # Rotación estricta del refresh token
            self.token_repo.revoke(token_hash)
            rotated = self._issue_session_tokens(user)
            self.audit_repo.append(
                {
                    "user_email": user["email"],
                    "ip_address": "127.0.0.1",
                    "action": "TOKEN_ROTATED",
                    "entity": "auth",
                    "entity_id": str(user["id"]),
                    "new_value": "Access y Refresh Token renovados silenciosamente",
                }
            )
            claims = decode_access_token(rotated["access_token"])
            return {
                "valid": True,
                "refreshed": True,
                "user": rotated["user"],
                "claims": claims,
                "access_token": rotated["access_token"],
                "refresh_token": rotated["refresh_token"],
            }
        except jwt.InvalidTokenError:
            return {"valid": False, "reason": "Token JWT inválido o manipulado."}

    def logout(
        self,
        user_email: Optional[str],
        refresh_token: Optional[str],
        ip_address: str = "127.0.0.1",
    ) -> None:
        if refresh_token:
            self.token_repo.revoke(hash_refresh_token(refresh_token))
        if user_email:
            self.audit_repo.append(
                {
                    "user_email": user_email,
                    "ip_address": ip_address,
                    "action": "LOGOUT",
                    "entity": "auth",
                    "entity_id": user_email,
                    "new_value": "Sesión cerrada y token revocado",
                }
            )

    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    def log_unauthorized_attempt(
        self,
        user_email: str,
        route: str,
        role: str,
        ip_address: str = "127.0.0.1",
    ) -> None:
        self.audit_repo.append(
            {
                "user_email": user_email or "anonimo",
                "ip_address": ip_address,
                "action": "UNAUTHORIZED_ROUTE_ACCESS",
                "entity": "rbac",
                "entity_id": route,
                "new_value": f"Rol '{role}' sin permiso",
            }
        )

    def list_users(
        self,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        users = self.user_repo.list_users(role=role, area=area, is_active=is_active, search=search)
        return [{k: v for k, v in u.items() if k != "password_hash"} for u in users]

    def list_active_technicians(self, area: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna técnicos activos sin exponer hashes ni repositorios a la capa UI."""
        return self.list_users(role="tecnico", area=area, is_active=True)

    def update_user_admin(
        self,
        actor_email: str,
        target_user_id: int,
        role: str,
        area: Optional[str],
        is_active: bool,
        sede: str,
        ip_address: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        if role not in VALID_ROLES:
            raise ValueError(f"Rol no válido: {role}")
        target = self.user_repo.get_by_id(target_user_id)
        if not target:
            raise ValueError("Usuario no encontrado.")

        # Regla RF-02 / CU-14: No inactivar al último administrador activo
        if target["role"] == "admin" and target["is_active"]:
            if (not is_active or role != "admin") and self.user_repo.count_active_admins() <= 1:
                raise ValueError("No es posible inactivar o cambiar de rol al último administrador activo.")

        # Regla CU-14: No inactivar un técnico con tickets abiertos
        if target["role"] == "tecnico" and target["is_active"] and not is_active:
            open_assigned = [
                t
                for t in self.ticket_repo.list_tickets(assigned_tech_id=target["id"])
                if t["status"] in ("Asignado", "En atención", "En espera", "Reabierto")
            ]
            if open_assigned:
                raise ValueError(
                    f"El técnico tiene {len(open_assigned)} tickets abiertos. Reasígnelos antes de inactivarlo."
                )

        old_summary = f"role={target['role']}, area={target['area']}, active={target['is_active']}"
        updated = self.user_repo.update(
            target_user_id,
            {"role": role, "area": area, "is_active": is_active, "sede": sede},
        )
        if not is_active:
            self.token_repo.revoke_all_for_user(target_user_id)

        new_summary = f"role={role}, area={area}, active={is_active}"
        self.audit_repo.append(
            {
                "user_email": actor_email,
                "ip_address": ip_address,
                "action": "USER_UPDATED",
                "entity": "user",
                "entity_id": str(target_user_id),
                "old_value": old_summary,
                "new_value": new_summary,
            }
        )
        return {k: v for k, v in (updated or {}).items() if k != "password_hash"}
