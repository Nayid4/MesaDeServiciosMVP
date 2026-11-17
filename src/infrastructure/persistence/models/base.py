"""Base declarativa SQLAlchemy 2.0 compartida entre modelos ORM."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy 2.0 para el esquema relacional CASAGBI."""
