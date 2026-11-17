"""Registro completo de Commands y Queries en CQRSBus para la capa de presentación."""

from __future__ import annotations

from typing import Callable

from src.application.ai_agent import (
    ConfirmAgentDraftCommand,
    ConfirmAgentDraftCommandHandler,
    ProcessAgentTurnCommand,
    ProcessAgentTurnCommandHandler,
)
from src.application.analytics import (
    ActivateModelCommand,
    ActivateModelCommandHandler,
    ExportKpiReportQuery,
    ExportKpiReportQueryHandler,
    GetKpiMetricsQuery,
    GetKpiMetricsQueryHandler,
    GetModelComparisonQuery,
    GetModelComparisonQueryHandler,
    ListAuditLogsQuery,
    ListAuditLogsQueryHandler,
    TrainModelsCommand,
    TrainModelsCommandHandler,
)
from src.application.common.cqrs_bus import CQRSBus
from src.application.knowledge_base import (
    CompareKnowledgeArticleVersionsQuery,
    CompareKnowledgeArticleVersionsQueryHandler,
    GetKbArticleDetailQuery,
    GetKbArticleDetailQueryHandler,
    GetKnowledgeArticleVersionsQuery,
    GetKnowledgeArticleVersionsQueryHandler,
    ListKbArticlesPaginatedQuery,
    ListKbArticlesPaginatedQueryHandler,
    ListKnowledgeArticlesQuery,
    ListKnowledgeArticlesQueryHandler,
    RestoreKnowledgeArticleVersionCommand,
    RestoreKnowledgeArticleVersionCommandHandler,
    TransitionKnowledgeArticleCommand,
    TransitionKnowledgeArticleCommandHandler,
    UpsertKnowledgeArticleCommand,
    UpsertKnowledgeArticleCommandHandler,
)
from src.application.tickets import (
    AdjustPriorityCommand,
    AdjustPriorityCommandHandler,
    CreateTicketCommand,
    CreateTicketCommandHandler,
    CreateWsTicketCommand,
    CreateWsTicketCommandHandler,
    DeleteChatMessageCommand,
    DeleteChatMessageCommandHandler,
    EditChatMessageCommand,
    EditChatMessageCommandHandler,
    GetPublicSummaryQuery,
    GetPublicSummaryQueryHandler,
    GetPublicTicketQuery,
    GetPublicTicketQueryHandler,
    GetTicketDetailQuery,
    GetTicketDetailQueryHandler,
    ListTicketMessagesQuery,
    ListTicketMessagesQueryHandler,
    ListTicketsPaginatedQuery,
    ListTicketsPaginatedQueryHandler,
    ListTicketsQuery,
    ListTicketsQueryHandler,
    MarkMessagesReadCommand,
    MarkMessagesReadCommandHandler,
    PublicTicketLookupCommand,
    PublicTicketLookupCommandHandler,
    RateTicketCommand,
    RateTicketCommandHandler,
    ReassignTicketCommand,
    ReassignTicketCommandHandler,
    SendChatMessageCommand,
    SendChatMessageCommandHandler,
    TransitionTicketCommand,
    TransitionTicketCommandHandler,
    UploadTicketAttachmentsCommand,
    UploadTicketAttachmentsCommandHandler,
)
from src.application.users import (
    ChangePasswordCommand,
    ChangePasswordCommandHandler,
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetCommandHandler,
    GetCurrentProfileQuery,
    GetCurrentProfileQueryHandler,
    GetMeQuery,
    GetMeQueryHandler,
    ListDemoUsersQuery,
    ListDemoUsersQueryHandler,
    ListUsersPaginatedQuery,
    ListUsersPaginatedQueryHandler,
    LoginCommand,
    LoginCommandHandler,
    LogoutCommand,
    LogoutCommandHandler,
    ManageUserAdminCommand,
    ManageUserAdminCommandHandler,
    RefreshTokenCommand,
    RefreshTokenCommandHandler,
    RegisterInstitutionalUserCommand,
    RegisterInstitutionalUserCommandHandler,
    RequestPasswordResetCommand,
    RequestPasswordResetCommandHandler,
    UpdateProfileCommand,
    UpdateProfileCommandHandler,
)
from src.domain.ports import IUnitOfWork
from src.infrastructure.ml.ai_engine import LocalNLPEngine
from src.infrastructure.security import create_ticket_guest_token


def build_cqrs_bus(
    uow_factory_fn: Callable[[], IUnitOfWork],
    ai_engine: LocalNLPEngine,
) -> CQRSBus:
    """Construye y puebla el bus CQRS con todos los handlers de la aplicación."""
    bus = CQRSBus()

    # Users & Auth
    bus.register_command(LoginCommand, LoginCommandHandler(uow_factory_fn))
    bus.register_command(RegisterInstitutionalUserCommand, RegisterInstitutionalUserCommandHandler(uow_factory_fn))
    bus.register_command(RefreshTokenCommand, RefreshTokenCommandHandler(uow_factory_fn))
    bus.register_command(LogoutCommand, LogoutCommandHandler(uow_factory_fn))
    bus.register_command(UpdateProfileCommand, UpdateProfileCommandHandler(uow_factory_fn))
    bus.register_command(ChangePasswordCommand, ChangePasswordCommandHandler(uow_factory_fn))
    bus.register_command(RequestPasswordResetCommand, RequestPasswordResetCommandHandler(uow_factory_fn))
    bus.register_command(ConfirmPasswordResetCommand, ConfirmPasswordResetCommandHandler(uow_factory_fn))
    bus.register_command(ManageUserAdminCommand, ManageUserAdminCommandHandler(uow_factory_fn))
    bus.register_query(GetMeQuery, GetMeQueryHandler(uow_factory_fn))
    bus.register_query(GetCurrentProfileQuery, GetCurrentProfileQueryHandler(uow_factory_fn))
    bus.register_query(ListDemoUsersQuery, ListDemoUsersQueryHandler(uow_factory_fn))
    bus.register_query(ListUsersPaginatedQuery, ListUsersPaginatedQueryHandler(uow_factory_fn))

    # Tickets & Chat
    bus.register_command(CreateTicketCommand, CreateTicketCommandHandler(uow_factory_fn))
    bus.register_command(TransitionTicketCommand, TransitionTicketCommandHandler(uow_factory_fn))
    bus.register_command(ReassignTicketCommand, ReassignTicketCommandHandler(uow_factory_fn))
    bus.register_command(AdjustPriorityCommand, AdjustPriorityCommandHandler(uow_factory_fn))
    bus.register_command(RateTicketCommand, RateTicketCommandHandler(uow_factory_fn))
    bus.register_command(SendChatMessageCommand, SendChatMessageCommandHandler(uow_factory_fn))
    bus.register_command(EditChatMessageCommand, EditChatMessageCommandHandler(uow_factory_fn))
    bus.register_command(DeleteChatMessageCommand, DeleteChatMessageCommandHandler(uow_factory_fn))
    bus.register_command(MarkMessagesReadCommand, MarkMessagesReadCommandHandler(uow_factory_fn))
    bus.register_command(UploadTicketAttachmentsCommand, UploadTicketAttachmentsCommandHandler(uow_factory_fn))
    bus.register_command(
        PublicTicketLookupCommand,
        PublicTicketLookupCommandHandler(uow_factory_fn, create_ticket_guest_token),
    )
    bus.register_command(CreateWsTicketCommand, CreateWsTicketCommandHandler(uow_factory_fn))
    bus.register_query(ListTicketsQuery, ListTicketsQueryHandler(uow_factory_fn))
    bus.register_query(ListTicketsPaginatedQuery, ListTicketsPaginatedQueryHandler(uow_factory_fn))
    bus.register_query(ListTicketMessagesQuery, ListTicketMessagesQueryHandler(uow_factory_fn))
    bus.register_query(GetTicketDetailQuery, GetTicketDetailQueryHandler(uow_factory_fn))
    bus.register_query(GetPublicTicketQuery, GetPublicTicketQueryHandler(uow_factory_fn))
    bus.register_query(GetPublicSummaryQuery, GetPublicSummaryQueryHandler(uow_factory_fn))

    # Knowledge Base
    bus.register_command(UpsertKnowledgeArticleCommand, UpsertKnowledgeArticleCommandHandler(uow_factory_fn))
    bus.register_command(TransitionKnowledgeArticleCommand, TransitionKnowledgeArticleCommandHandler(uow_factory_fn))
    bus.register_command(RestoreKnowledgeArticleVersionCommand, RestoreKnowledgeArticleVersionCommandHandler(uow_factory_fn))
    bus.register_query(ListKnowledgeArticlesQuery, ListKnowledgeArticlesQueryHandler(uow_factory_fn))
    bus.register_query(ListKbArticlesPaginatedQuery, ListKbArticlesPaginatedQueryHandler(uow_factory_fn))
    bus.register_query(GetKbArticleDetailQuery, GetKbArticleDetailQueryHandler(uow_factory_fn))
    bus.register_query(GetKnowledgeArticleVersionsQuery, GetKnowledgeArticleVersionsQueryHandler(uow_factory_fn))
    bus.register_query(CompareKnowledgeArticleVersionsQuery, CompareKnowledgeArticleVersionsQueryHandler(uow_factory_fn))

    # Analytics & MLOps
    bus.register_query(GetKpiMetricsQuery, GetKpiMetricsQueryHandler(uow_factory_fn))
    bus.register_query(ExportKpiReportQuery, ExportKpiReportQueryHandler(uow_factory_fn))
    bus.register_query(GetModelComparisonQuery, GetModelComparisonQueryHandler(ai_engine))
    bus.register_query(ListAuditLogsQuery, ListAuditLogsQueryHandler(uow_factory_fn))
    bus.register_command(TrainModelsCommand, TrainModelsCommandHandler(uow_factory_fn, ai_engine))
    bus.register_command(ActivateModelCommand, ActivateModelCommandHandler(uow_factory_fn, ai_engine))

    # AI Agent
    bus.register_command(
        ProcessAgentTurnCommand,
        ProcessAgentTurnCommandHandler(uow_factory_fn, ai_engine, guest_token_factory=create_ticket_guest_token),
    )
    bus.register_command(ConfirmAgentDraftCommand, ConfirmAgentDraftCommandHandler(uow_factory_fn))

    return bus
