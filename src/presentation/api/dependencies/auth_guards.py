"""Guardianes de autenticación JWT y autorización RBAC para FastAPI Depends."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.common import sanitize_user_dict
from src.domain.exceptions import ForbiddenError, UnauthorizedError
from src.domain.rules import ROLE_LABELS, ROLE_PERMISSIONS
from src.infrastructure.composition import create_uow
from src.infrastructure.security import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def resolve_user_from_token(token: str, *, allow_guest: bool = False) -> Dict[str, Any]:
    """Decodifica JWT (usuario o invitado de ticket) y valida acceso."""
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Su Access Token JWT ha expirado. Renueve sesión.") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Token JWT inválido o malformado.") from exc

    if payload.get("token_type") == "ticket_guest" or payload.get("role") == "invitado":
        if not allow_guest:
            raise ForbiddenError(
                "El token de invitado está restringido exclusivamente al ticket consultado."
            )
        try:
            ticket_id = int(payload["ticket_id"])
            requester_id = int(payload["requester_id"])
            email = str(payload["email"]).strip().lower()
        except (KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedError("Token de invitado malformado.") from exc
        masked = str(payload.get("masked_email") or email)
        return {
            "id": requester_id,
            "email": email,
            "masked_email": masked,
            "full_name": f"Invitado ({masked})",
            "role": "invitado",
            "role_label": "Invitado externo",
            "ticket_id": ticket_id,
            "ticket_number": payload.get("ticket_number"),
            "permissions": ["guest_ticket_access"],
        }

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Token JWT inválido o malformado.") from exc

    with create_uow() as uow:
        user = uow.users.get_by_id(user_id)
    if not user:
        raise UnauthorizedError("El usuario propietario del token no existe.")
    if not bool(user.get("is_active", True)):
        raise ForbiddenError("Su cuenta institucional se encuentra deshabilitada.")

    clean = sanitize_user_dict(user)
    clean["role_label"] = ROLE_LABELS.get(clean["role"], clean["role"])
    clean["permissions"] = sorted(ROLE_PERMISSIONS.get(clean["role"], set()))
    return clean


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """Dependencia estricta FastAPI: exige Bearer JWT institucional válido (bloquea invitados)."""
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise UnauthorizedError("Se requiere token de acceso Bearer JWT para acceder a este recurso.")
    return resolve_user_from_token(credentials.credentials, allow_guest=False)


async def get_ticket_actor(
    ticket_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """Dependencia para endpoints de ticket/chat: acepta JWT institucional o guest token de ESE ticket."""
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise UnauthorizedError("Se requiere token de acceso Bearer JWT para acceder a este ticket.")
    actor = resolve_user_from_token(credentials.credentials, allow_guest=True)
    if actor.get("role") == "invitado" and int(actor.get("ticket_id", -1)) != int(ticket_id):
        raise ForbiddenError("El token de invitado no tiene permiso sobre otro ticket distinto.")
    return actor


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """Dependencia opcional: retorna usuario institucional si existe Bearer JWT válido (nunca invitados), o None."""
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        return None
    try:
        return resolve_user_from_token(credentials.credentials, allow_guest=False)
    except Exception:
        return None


async def get_optional_ticket_actor(
    ticket_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """Dependencia opcional para descargas de adjuntos: acepta usuario o invitado de ESE ticket."""
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        return None
    try:
        actor = resolve_user_from_token(credentials.credentials, allow_guest=True)
        if actor.get("role") == "invitado" and int(actor.get("ticket_id", -1)) != int(ticket_id):
            return None
        return actor
    except Exception:
        return None


def require_roles(allowed_roles: Iterable[str]) -> Callable[..., Dict[str, Any]]:
    """Fábrica de dependencia FastAPI que aplica control estricto RBAC por rol."""
    allowed_set = set(allowed_roles)

    async def _guard(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") not in allowed_set:
            raise ForbiddenError(
                f"Permiso denegado para el rol '{user.get('role')}'. Roles requeridos: {', '.join(sorted(allowed_set))}."
            )
        return user

    return _guard


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
