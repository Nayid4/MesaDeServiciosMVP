"""Entidad KnowledgeArticle para la Base de Conocimiento institucional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class KnowledgeArticle:
    """Artículo técnico o público de la Base de Conocimiento institucional."""

    id: Optional[int]
    code: str
    title: str
    service_name: str
    symptoms: str
    solution_steps: str
    keywords: str
    visibility: str = "Pública"
    status: str = "Publicado"
    version: int = 1
    author_email: str = "coordinador@unicesar.edu.co"
    reviewer_email: Optional[str] = None
    updated_at: Optional[str] = None
    category_topic: str = "General"
    probable_cause: str = ""
    escalation_criteria: str = ""
    review_notes: Optional[str] = None
    is_demo: bool = True
    created_at: Optional[str] = None
