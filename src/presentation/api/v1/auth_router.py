"""Router REST v1 de Autenticación JWT, Refresh Token, Recuperación y Notificaciones."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.application.auth import (
    ConfirmPasswordResetCommand,
    GetMeQuery,
    ListDemoUsersQuery,
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
    RegisterInstitutionalUserCommand,
    RequestPasswordResetCommand,
    is_demo_mode_enabled,
)
from src.infrastructure.composition import create_uow, get_cqrs_bus
from src.presentation.api.dependencies.auth_guards import (
    get_client_ip,
    get_current_user,
    get_optional_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación y RBAC"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: Optional[str] = None
    demo_mode: bool = False


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5)
    full_name: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    sede: str = "Sede Sabanas (Valledupar)"
    privacy_accepted: bool = True


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordResetRequestBody(BaseModel):
    email: str = Field(..., min_length=5)


class PasswordResetConfirmBody(BaseModel):
    token: str = Field(..., min_length=16)
    new_password: str = Field(..., min_length=8)


class NotificationPreferencesRequest(BaseModel):
    notify_in_app: bool = True
    notify_email_sim: bool = True
    notify_ticket_updates: bool = True
    notify_chat_messages: bool = True
    notify_sla_alerts: bool = True


@router.post("/login")
def login(payload: LoginRequest, request: Request) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        LoginCommand(
            email=payload.email,
            password=payload.password,
            demo_mode=payload.demo_mode,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, request: Request) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        RegisterInstitutionalUserCommand(
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
            sede=payload.sede,
            privacy_accepted=payload.privacy_accepted,
            ip_address=get_client_ip(request),
        )
    )


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, request: Request) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        RefreshTokenCommand(refresh_token=payload.refresh_token, ip_address=get_client_ip(request))
    )


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        LogoutCommand(
            refresh_token=payload.refresh_token,
            user_email=current_user["email"] if current_user else "anon@unicesar.edu.co",
            ip_address=get_client_ip(request),
        )
    )


@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequestBody, request: Request
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        RequestPasswordResetCommand(email=payload.email, ip_address=get_client_ip(request))
    )


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirmBody, request: Request
) -> Dict[str, Any]:
    return get_cqrs_bus().execute(
        ConfirmPasswordResetCommand(
            token=payload.token,
            new_password=payload.new_password,
            ip_address=get_client_ip(request),
        )
    )


@router.get("/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return get_cqrs_bus().query(GetMeQuery(user_id=int(current_user["id"])))


@router.get("/demo-users")
def list_demo_users() -> Dict[str, Any]:
    return {
        "demo_mode": is_demo_mode_enabled(),
        "users": get_cqrs_bus().query(ListDemoUsersQuery()),
    }


@router.post("/notifications/read-all")
def mark_notifications_read(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    with create_uow() as uow:
        uow.notifications.mark_all_read(current_user["email"])
        uow.commit()
    return {"status": "ok"}


@router.post("/notifications/{notification_id}/read")
def mark_single_notification_read(
    notification_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    with create_uow() as uow:
        updated = uow.notifications.mark_read(current_user["email"], notification_id)
        uow.commit()
    return {"status": "ok", "updated": updated}


@router.get("/notifications/preferences")
def get_notification_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    with create_uow() as uow:
        prefs = uow.notifications.get_preferences(current_user["email"])
    return {"preferences": prefs}


@router.put("/notifications/preferences")
def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    with create_uow() as uow:
        prefs = uow.notifications.update_preferences(current_user["email"], payload.model_dump())
        uow.commit()
    return {"preferences": prefs}
