"""Puertos de repositorio para usuarios, refresh tokens y recuperación de contraseña."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.common.pagination import PageRequest, PagedResult


class IUserRepo(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def update(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list_users(
        self,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def list_users_paginated(
        self,
        page_request: PageRequest,
        *,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PagedResult[Dict[str, Any]]: ...

    @abstractmethod
    def list_active_technicians_with_load(self, area: str) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def count_active_admins(self) -> int: ...


class IRefreshTokenRepo(ABC):
    @abstractmethod
    def create(self, user_id: int, token_hash: str, expires_at: str) -> None: ...

    @abstractmethod
    def get_valid(self, token_hash: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def revoke(self, token_hash: str) -> None: ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int) -> None: ...


class IPasswordResetTokenRepo(ABC):
    @abstractmethod
    def create(self, user_id: int, token_hash: str, expires_at: str) -> None: ...

    @abstractmethod
    def consume_valid(self, token_hash: str, now_iso: str) -> Optional[Dict[str, Any]]: ...


IUserRepository = IUserRepo
IRefreshTokenRepository = IRefreshTokenRepo
