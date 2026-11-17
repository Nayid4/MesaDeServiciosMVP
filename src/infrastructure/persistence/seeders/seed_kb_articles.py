"""Seeder idempotente para los 42 artículos de demostración de Base de Conocimiento."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import (
    KnowledgeArticleORM,
    KnowledgeArticleVersionORM,
)
from src.infrastructure.persistence.seeders.seed_kb_data_a import KB_DATA_A
from src.infrastructure.persistence.seeders.seed_kb_data_b import KB_DATA_B
from src.infrastructure.persistence.seeders.seed_kb_data_c import KB_DATA_C
from src.infrastructure.persistence.seeders.seed_kb_data_d import KB_DATA_D

SEED_KB_ARTICLES: List[Dict[str, Any]] = KB_DATA_A + KB_DATA_B + KB_DATA_C + KB_DATA_D


def seed_kb_articles(session: Session, now_iso: str) -> None:
    """Precarga de forma idempotente artículos KB con historial inicial."""
    existing_by_code = {k.code: k for k in session.scalars(select(KnowledgeArticleORM)).all()}
    for item in SEED_KB_ARTICLES:
        art = existing_by_code.get(item["code"])
        if art is None:
            art = KnowledgeArticleORM(
                code=item["code"],
                title=item["title"],
                service_name=item["service_name"],
                category_topic=item["category_topic"],
                symptoms=item["symptoms"],
                probable_cause=item["probable_cause"],
                solution_steps=item["solution_steps"],
                escalation_criteria=item["escalation_criteria"],
                keywords=item["keywords"],
                visibility=item["visibility"],
                status=item["status"],
                version=1,
                author_email=item["author_email"],
                reviewer_email=item["reviewer_email"],
                review_notes=None,
                is_demo=True,
                created_at=now_iso,
                updated_at=now_iso,
            )
            session.add(art)
            session.flush()
            session.add(
                KnowledgeArticleVersionORM(
                    article_id=art.id,
                    version_number=1,
                    title=art.title,
                    service_name=art.service_name,
                    category_topic=art.category_topic,
                    symptoms=art.symptoms,
                    probable_cause=art.probable_cause,
                    solution_steps=art.solution_steps,
                    escalation_criteria=art.escalation_criteria,
                    keywords=art.keywords,
                    visibility=art.visibility,
                    status=art.status,
                    review_notes=None,
                    actor_email=art.author_email,
                    change_summary="Carga inicial catálogo demostrativo CASAGBI [CONFIRMAR]",
                    created_at=now_iso,
                )
            )
            continue

        if not art.category_topic or art.category_topic == "General":
            art.category_topic = item["category_topic"]
        if not art.probable_cause or art.probable_cause.startswith("Por verificar"):
            art.probable_cause = item["probable_cause"]
        if not art.escalation_criteria or art.escalation_criteria.startswith("Escalar a soporte Nivel 2"):
            art.escalation_criteria = item["escalation_criteria"]
        if not art.created_at:
            art.created_at = art.updated_at or now_iso
        art.is_demo = True
        has_ver = (
            session.scalar(
                select(func.count(KnowledgeArticleVersionORM.id)).where(
                    KnowledgeArticleVersionORM.article_id == art.id
                )
            )
            or 0
        )
        if has_ver == 0:
            session.add(
                KnowledgeArticleVersionORM(
                    article_id=art.id,
                    version_number=int(art.version or 1),
                    title=art.title,
                    service_name=art.service_name,
                    category_topic=art.category_topic,
                    symptoms=art.symptoms,
                    probable_cause=art.probable_cause,
                    solution_steps=art.solution_steps,
                    escalation_criteria=art.escalation_criteria,
                    keywords=art.keywords,
                    visibility=art.visibility,
                    status=art.status,
                    review_notes=art.review_notes,
                    actor_email=art.author_email,
                    change_summary="Migración inicial de versión base KB",
                    created_at=art.created_at or now_iso,
                )
            )
    session.flush()
