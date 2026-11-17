"""Subpaquete de dominio para Base de Conocimiento."""

from src.domain.knowledge_base.article_entity import KnowledgeArticle
from src.domain.knowledge_base.kb_repository_port import (
    IKnowledgeRepo,
    IKnowledgeRepository,
)
from src.domain.knowledge_base.kb_rules import (
    KB_ARTICLE_STATUSES,
    KB_CATEGORIES,
    KB_VALID_TRANSITIONS,
    KB_VISIBILITIES,
    sanitize_kb_html,
)

__all__ = [
    "IKnowledgeRepo",
    "IKnowledgeRepository",
    "KB_ARTICLE_STATUSES",
    "KB_CATEGORIES",
    "KB_VALID_TRANSITIONS",
    "KB_VISIBILITIES",
    "KnowledgeArticle",
    "sanitize_kb_html",
]
