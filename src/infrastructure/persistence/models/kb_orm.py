"""Modelos ORM de Base de Conocimiento (ITIL v4) e historial de versiones."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import Base


class KnowledgeArticleORM(Base):
    __tablename__ = "kb_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_topic: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    probable_cause: Mapped[str] = mapped_column(
        Text, nullable=False, default="Por verificar en diagnóstico técnico [CONFIRMAR]."
    )
    solution_steps: Mapped[str] = mapped_column(Text, nullable=False)
    escalation_criteria: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Escalar a soporte Nivel 2 del área técnica si persiste el incidente.",
    )
    keywords: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="Pública")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Publicado")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeArticleVersionORM(Base):
    """Historial versionado inmutable de cada edición o transición de artículos KB."""

    __tablename__ = "kb_article_versions"
    __table_args__ = (Index("idx_kb_versions_art_ver", "article_id", "version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_topic: Mapped[str] = mapped_column(String(120), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    probable_cause: Mapped[str] = mapped_column(Text, nullable=False)
    solution_steps: Mapped[str] = mapped_column(Text, nullable=False)
    escalation_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
