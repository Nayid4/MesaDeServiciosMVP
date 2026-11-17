"""Fachada CQRS Analytics, MLOps, Auditoría y Base de Conocimiento."""

from __future__ import annotations

from src.application.analytics.commands.ml_admin_commands import (
    ActivateModelCommand,
    ActivateModelCommandHandler,
    TrainModelsCommand,
    TrainModelsCommandHandler,
)
from src.application.analytics.queries.kpis_query import (
    ExportKpiReportQuery,
    ExportKpiReportQueryHandler,
    GetKpiMetricsQuery,
    GetKpiMetricsQueryHandler,
)
from src.application.analytics.queries.ml_audit_queries import (
    GetModelComparisonQuery,
    GetModelComparisonQueryHandler,
    ListAuditLogsQuery,
    ListAuditLogsQueryHandler,
)
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

__all__ = [
    "ActivateModelCommand",
    "ActivateModelCommandHandler",
    "CompareKnowledgeArticleVersionsQuery",
    "CompareKnowledgeArticleVersionsQueryHandler",
    "ExportKpiReportQuery",
    "ExportKpiReportQueryHandler",
    "GetKbArticleDetailQuery",
    "GetKbArticleDetailQueryHandler",
    "GetKnowledgeArticleVersionsQuery",
    "GetKnowledgeArticleVersionsQueryHandler",
    "GetKpiMetricsQuery",
    "GetKpiMetricsQueryHandler",
    "GetModelComparisonQuery",
    "GetModelComparisonQueryHandler",
    "ListAuditLogsQuery",
    "ListAuditLogsQueryHandler",
    "ListKbArticlesPaginatedQuery",
    "ListKbArticlesPaginatedQueryHandler",
    "ListKnowledgeArticlesQuery",
    "ListKnowledgeArticlesQueryHandler",
    "RestoreKnowledgeArticleVersionCommand",
    "RestoreKnowledgeArticleVersionCommandHandler",
    "TrainModelsCommand",
    "TrainModelsCommandHandler",
    "TransitionKnowledgeArticleCommand",
    "TransitionKnowledgeArticleCommandHandler",
    "UpsertKnowledgeArticleCommand",
    "UpsertKnowledgeArticleCommandHandler",
]
