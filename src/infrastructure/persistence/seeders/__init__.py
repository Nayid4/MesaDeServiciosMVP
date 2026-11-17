"""Orquestador modular de precarga inicial idempotente para CASAGBI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.domain.rules import now_bogota
from src.infrastructure.persistence.seeders.seed_kb_articles import (
    SEED_KB_ARTICLES,
    seed_kb_articles,
)
from src.infrastructure.persistence.seeders.seed_tickets import seed_sample_tickets
from src.infrastructure.persistence.seeders.seed_users import seed_catalog_sla_and_users


def seed_initial_data(session: Session) -> None:
    """Precarga de forma idempotente catálogo, SLA, usuarios, artículos KB y tickets demo."""
    now_iso = now_bogota().isoformat()
    seed_catalog_sla_and_users(session, now_iso)
    seed_kb_articles(session, now_iso)
    seed_sample_tickets(session, now_iso)


__all__ = ["SEED_KB_ARTICLES", "seed_initial_data"]
