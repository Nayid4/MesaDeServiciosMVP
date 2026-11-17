"""Fachada de compatibilidad para precarga inicial idempotente CASAGBI."""

from __future__ import annotations

from src.infrastructure.persistence.seeders import seed_initial_data

__all__ = ["seed_initial_data"]
