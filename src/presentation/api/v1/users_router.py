"""Router REST v1 de perfil personal, contraseña segura y directorio paginado de usuarios."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from src.application.users import (
    ChangePasswordCommand,
    GetCurrentProfileQuery,
    ListUsersPaginatedQuery,
    ManageUserAdminCommand,
    UpdateProfileCommand,
)
from src.infrastructure.composition import get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/api/v1/users", tags=["Usuarios y Perfil"])


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=3)
    sede: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class AdminUpdateUserRequest(BaseModel):
    role: Optional[str] = None
    area: Optional[str] = None
    sede: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


@router.get("/me")
def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetCurrentProfileQuery(user_id=int(current_user["id"])))


@router.patch("/me/profile")
def update_my_profile(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        UpdateProfileCommand(
            user_id=int(current_user["id"]),
            full_name=payload.full_name,
            sede=payload.sede,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/me/password")
def change_my_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        ChangePasswordCommand(
            user_id=int(current_user["id"]),
            current_password=payload.current_password,
            new_password=payload.new_password,
            ip_address=get_client_ip(request),
        )
    )


@router.get("")
def list_users_paginated(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    role: Optional[str] = None,
    area: Optional[str] = None,
    is_active: Optional[bool] = None,
    q: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_roles(["admin", "coordinador", "director"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().query(
        ListUsersPaginatedQuery(
            actor_role=current_user["role"],
            page=page,
            page_size=page_size,
            role=role or None,
            area=area or None,
            is_active=is_active,
            search=q or None,
        )
    )


@router.patch("/{user_id}")
def admin_update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"])),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        ManageUserAdminCommand(
            actor_id=int(current_user["id"]),
            actor_email=current_user["email"],
            actor_role=current_user["role"],
            target_user_id=user_id,
            role=payload.role,
            area=payload.area,
            sede=payload.sede,
            is_active=payload.is_active,
            full_name=payload.full_name,
            ip_address=get_client_ip(request),
        )
    )
