"""Fachada de puertos abstractos del dominio (Repositorios, Unit of Work y Servicio IA)."""

from src.domain.knowledge_base.kb_repository_port import (
    IKnowledgeRepo,
    IKnowledgeRepository,
)
from src.domain.ports.ai_service_port import IAIService
from src.domain.ports.unit_of_work_port import IUnitOfWork
from src.domain.tickets.ticket_repository_port import (
    IAuditRepo,
    IAuditRepository,
    ICatalogRepo,
    ICatalogRepository,
    INotificationRepo,
    INotificationRepository,
    ITicketRepo,
    ITicketRepository,
)
from src.domain.users.user_repository_port import (
    IPasswordResetTokenRepo,
    IRefreshTokenRepo,
    IRefreshTokenRepository,
    IUserRepo,
    IUserRepository,
)

__all__ = [
    "IAIService",
    "IAuditRepo",
    "IAuditRepository",
    "ICatalogRepo",
    "ICatalogRepository",
    "IKnowledgeRepo",
    "IKnowledgeRepository",
    "INotificationRepo",
    "INotificationRepository",
    "IPasswordResetTokenRepo",
    "IRefreshTokenRepo",
    "IRefreshTokenRepository",
    "ITicketRepo",
    "ITicketRepository",
    "IUnitOfWork",
    "IUserRepo",
    "IUserRepository",
]
