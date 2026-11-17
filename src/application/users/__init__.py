"""Reexportaciones del módulo CQRS de usuarios, autenticación y perfiles."""

from __future__ import annotations

from src.application.users.commands.change_password import (
    ChangePasswordCommand,
    ChangePasswordCommandHandler,
)
from src.application.users.commands.login import (
    LoginCommand,
    LoginCommandHandler,
    is_demo_mode_enabled,
)
from src.application.users.commands.manage_user_admin import (
    ManageUserAdminCommand,
    ManageUserAdminCommandHandler,
)
from src.application.users.commands.password_reset import (
    PASSWORD_RESET_OUTBOX,
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetCommandHandler,
    RequestPasswordResetCommand,
    RequestPasswordResetCommandHandler,
)
from src.application.users.commands.refresh_logout import (
    LogoutCommand,
    LogoutCommandHandler,
    RefreshTokenCommand,
    RefreshTokenCommandHandler,
)
from src.application.users.commands.register_user import (
    RegisterInstitutionalUserCommand,
    RegisterInstitutionalUserCommandHandler,
)
from src.application.users.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileCommandHandler,
)
from src.application.users.queries.get_profile import (
    GetCurrentProfileQuery,
    GetCurrentProfileQueryHandler,
    GetMeQuery,
    GetMeQueryHandler,
    ListDemoUsersQuery,
    ListDemoUsersQueryHandler,
)
from src.application.users.queries.list_users_paginated import (
    ListUsersPaginatedQuery,
    ListUsersPaginatedQueryHandler,
)

__all__ = [
    "PASSWORD_RESET_OUTBOX",
    "ChangePasswordCommand",
    "ChangePasswordCommandHandler",
    "ConfirmPasswordResetCommand",
    "ConfirmPasswordResetCommandHandler",
    "GetCurrentProfileQuery",
    "GetCurrentProfileQueryHandler",
    "GetMeQuery",
    "GetMeQueryHandler",
    "ListDemoUsersQuery",
    "ListDemoUsersQueryHandler",
    "ListUsersPaginatedQuery",
    "ListUsersPaginatedQueryHandler",
    "LoginCommand",
    "LoginCommandHandler",
    "LogoutCommand",
    "LogoutCommandHandler",
    "ManageUserAdminCommand",
    "ManageUserAdminCommandHandler",
    "RefreshTokenCommand",
    "RefreshTokenCommandHandler",
    "RegisterInstitutionalUserCommand",
    "RegisterInstitutionalUserCommandHandler",
    "RequestPasswordResetCommand",
    "RequestPasswordResetCommandHandler",
    "UpdateProfileCommand",
    "UpdateProfileCommandHandler",
    "is_demo_mode_enabled",
]
