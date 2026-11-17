"""Reexportaciones del paquete CQRS de Base de Conocimiento (ITIL v4)."""

from __future__ import annotations

from src.application.knowledge_base.commands.transition_article import (
    ChangeArticleStatusCommand,
    ChangeArticleStatusCommandHandler,
    RestoreKnowledgeArticleVersionCommand,
    RestoreKnowledgeArticleVersionCommandHandler,
    TransitionKnowledgeArticleCommand,
    TransitionKnowledgeArticleCommandHandler,
)
from src.application.knowledge_base.commands.upsert_article import (
    CreateArticleCommand,
    CreateArticleCommandHandler,
    UpdateArticleCommand,
    UpdateArticleCommandHandler,
    UpsertKnowledgeArticleCommand,
    UpsertKnowledgeArticleCommandHandler,
)
from src.application.knowledge_base.queries.kb_queries import (
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
)

__all__ = [
    "ChangeArticleStatusCommand",
    "ChangeArticleStatusCommandHandler",
    "CompareKnowledgeArticleVersionsQuery",
    "CompareKnowledgeArticleVersionsQueryHandler",
    "CreateArticleCommand",
    "CreateArticleCommandHandler",
    "GetKbArticleDetailQuery",
    "GetKbArticleDetailQueryHandler",
    "GetKnowledgeArticleVersionsQuery",
    "GetKnowledgeArticleVersionsQueryHandler",
    "ListKbArticlesPaginatedQuery",
    "ListKbArticlesPaginatedQueryHandler",
    "ListKnowledgeArticlesQuery",
    "ListKnowledgeArticlesQueryHandler",
    "RestoreKnowledgeArticleVersionCommand",
    "RestoreKnowledgeArticleVersionCommandHandler",
    "TransitionKnowledgeArticleCommand",
    "TransitionKnowledgeArticleCommandHandler",
    "UpdateArticleCommand",
    "UpdateArticleCommandHandler",
    "UpsertKnowledgeArticleCommand",
    "UpsertKnowledgeArticleCommandHandler",
]
