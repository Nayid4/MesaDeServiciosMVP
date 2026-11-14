"""Contenedor de Inyección de Dependencias (DIP) para CASAGBI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.application.ai_use_cases import AIService
from src.application.auth_use_cases import AuthService
from src.application.ticket_use_cases import TicketService
from src.domain.repositories import (
    IAuditRepository,
    ICatalogRepository,
    IKnowledgeRepository,
    INotificationRepository,
    IRefreshTokenRepository,
    ITicketRepository,
    IUserRepository,
)
from src.infrastructure.ml_pipeline import DEFAULT_REGISTRY_PATH
from src.infrastructure.sqlite_repositories import (
    SQLiteAuditLogRepository,
    SQLiteCatalogRepository,
    SQLiteKnowledgeBaseRepository,
    SQLiteNotificationRepository,
    SQLiteRefreshTokenRepository,
    SQLiteTicketRepository,
    SQLiteUserRepository,
)


class DependencyContainer:
    """Cablea interfaces de dominio, adaptadores SQLite y casos de uso de aplicación."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    ):
        self.db_path = db_path
        self.registry_path = Path(registry_path)

        # Repositorios concretos (implementan contratos I* de src.domain.repositories)
        self.user_repo: IUserRepository = SQLiteUserRepository(db_path)
        self.token_repo: IRefreshTokenRepository = SQLiteRefreshTokenRepository(db_path)
        self.ticket_repo: ITicketRepository = SQLiteTicketRepository(db_path)
        self.kb_repo: IKnowledgeRepository = SQLiteKnowledgeBaseRepository(db_path)
        self.audit_repo: IAuditRepository = SQLiteAuditLogRepository(db_path)
        self.notif_repo: INotificationRepository = SQLiteNotificationRepository(db_path)
        self.catalog_repo: ICatalogRepository = SQLiteCatalogRepository(db_path)

        # Servicios de Aplicación (Casos de Uso)
        self.auth_service = AuthService(
            db_path=db_path,
            user_repo=self.user_repo,
            token_repo=self.token_repo,
            ticket_repo=self.ticket_repo,
            audit_repo=self.audit_repo,
        )
        self.ticket_service = TicketService(
            db_path=db_path,
            ticket_repo=self.ticket_repo,
            user_repo=self.user_repo,
            kb_repo=self.kb_repo,
            audit_repo=self.audit_repo,
            notif_repo=self.notif_repo,
            catalog_repo=self.catalog_repo,
        )
        self.ai_service = AIService(
            db_path=db_path,
            registry_path=self.registry_path,
            kb_repo=self.kb_repo,
            ticket_repo=self.ticket_repo,
            audit_repo=self.audit_repo,
            catalog_repo=self.catalog_repo,
        )


_DEFAULT_CONTAINER: Optional[DependencyContainer] = None


def get_container(
    db_path: Optional[str] = None,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> DependencyContainer:
    """Retorna un contenedor configurado (singleton por proceso cuando usa ruta por defecto)."""
    global _DEFAULT_CONTAINER
    if db_path is not None or Path(registry_path) != Path(DEFAULT_REGISTRY_PATH):
        return DependencyContainer(db_path=db_path, registry_path=registry_path)
    if _DEFAULT_CONTAINER is None:
        _DEFAULT_CONTAINER = DependencyContainer()
    return _DEFAULT_CONTAINER


def reset_container() -> None:
    """Reinicia el contenedor singleton (útil tras reentrenamiento o en pruebas aisladas)."""
    global _DEFAULT_CONTAINER
    _DEFAULT_CONTAINER = None
