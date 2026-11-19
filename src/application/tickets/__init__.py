"""Fachada CQRS de tickets: Commands transaccionales y Queries paginadas/detalle."""

from __future__ import annotations

from src.application.tickets.commands.change_status import (
    RateTicketCommand,
    RateTicketCommandHandler,
    TransitionTicketCommand,
    TransitionTicketCommandHandler,
)
from src.application.tickets.commands.chat_attachments import (
    UploadTicketAttachmentsCommand,
    UploadTicketAttachmentsCommandHandler,
)
from src.application.tickets.commands.chat_messages import (
    DeleteChatMessageCommand,
    DeleteChatMessageCommandHandler,
    EditChatMessageCommand,
    EditChatMessageCommandHandler,
    MarkMessagesReadCommand,
    MarkMessagesReadCommandHandler,
    SendChatMessageCommand,
    SendChatMessageCommandHandler,
)
from src.application.tickets.commands.create_ticket import (
    CreateTicketCommand,
    CreateTicketCommandHandler,
)
from src.application.tickets.commands.public_guest_access import (
    CreateWsTicketCommand,
    CreateWsTicketCommandHandler,
    PublicTicketLookupCommand,
    PublicTicketLookupCommandHandler,
)
from src.application.tickets.commands.reassign_priority import (
    AdjustPriorityCommand,
    AdjustPriorityCommandHandler,
    ReassignTicketCommand,
    ReassignTicketCommandHandler,
)
from src.application.tickets.queries.get_ticket_detail import (
    GetPublicSummaryQuery,
    GetPublicSummaryQueryHandler,
    GetPublicTicketQuery,
    GetPublicTicketQueryHandler,
    GetTicketDetailQuery,
    GetTicketDetailQueryHandler,
    ListTicketMessagesQuery,
    ListTicketMessagesQueryHandler,
    compute_technician_workloads,
)
from src.application.tickets.queries.list_tickets import (
    ListTicketsPaginatedQuery,
    ListTicketsPaginatedQueryHandler,
    ListTicketsQuery,
    ListTicketsQueryHandler,
    compute_ticket_list_summary,
)
from src.application.tickets.ticket_helpers import (
    GUEST_OTP_OUTBOX,
    LOOKUP_LOCKOUT_SECONDS,
    LOOKUP_MAX_ATTEMPTS,
    MESSAGE_EDIT_WINDOW_SECONDS,
    PRIVATE_ATTACHMENTS_ROOT,
    _authorize_ticket_access,
    _is_guest_otp_enabled,
    authorize_ticket_access,
    is_guest_otp_enabled,
)

__all__ = [
    "AdjustPriorityCommand",
    "AdjustPriorityCommandHandler",
    "CreateTicketCommand",
    "CreateTicketCommandHandler",
    "CreateWsTicketCommand",
    "CreateWsTicketCommandHandler",
    "DeleteChatMessageCommand",
    "DeleteChatMessageCommandHandler",
    "EditChatMessageCommand",
    "EditChatMessageCommandHandler",
    "GUEST_OTP_OUTBOX",
    "GetPublicSummaryQuery",
    "GetPublicSummaryQueryHandler",
    "GetPublicTicketQuery",
    "GetPublicTicketQueryHandler",
    "GetTicketDetailQuery",
    "GetTicketDetailQueryHandler",
    "LOOKUP_LOCKOUT_SECONDS",
    "LOOKUP_MAX_ATTEMPTS",
    "ListTicketMessagesQuery",
    "ListTicketMessagesQueryHandler",
    "ListTicketsPaginatedQuery",
    "ListTicketsPaginatedQueryHandler",
    "ListTicketsQuery",
    "ListTicketsQueryHandler",
    "MESSAGE_EDIT_WINDOW_SECONDS",
    "MarkMessagesReadCommand",
    "MarkMessagesReadCommandHandler",
    "PRIVATE_ATTACHMENTS_ROOT",
    "PublicTicketLookupCommand",
    "PublicTicketLookupCommandHandler",
    "RateTicketCommand",
    "RateTicketCommandHandler",
    "ReassignTicketCommand",
    "ReassignTicketCommandHandler",
    "SendChatMessageCommand",
    "SendChatMessageCommandHandler",
    "TransitionTicketCommand",
    "TransitionTicketCommandHandler",
    "UploadTicketAttachmentsCommand",
    "UploadTicketAttachmentsCommandHandler",
    "_authorize_ticket_access",
    "_is_guest_otp_enabled",
    "authorize_ticket_access",
    "compute_technician_workloads",
    "compute_ticket_list_summary",
    "is_guest_otp_enabled",
]
