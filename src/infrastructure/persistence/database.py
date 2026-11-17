"""Motor SQLAlchemy 2.0 (SQLite modo WAL), SessionFactory e inicialización de esquema."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from src.infrastructure.persistence.migrations import (
    install_audit_immutability_and_migrate_legacy,
    migrate_schema_and_legacy_tickets,
)
from src.infrastructure.persistence.models import Base

DEFAULT_DB_PATH = Path("data/mesa_servicios_upc.db")

_ENGINE_CACHE: Dict[str, Engine] = {}
_SESSION_FACTORY_CACHE: Dict[str, sessionmaker[Session]] = {}


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Resuelve la ruta de SQLite permitiendo aislar pruebas vs operación."""
    if custom_path is not None:
        return Path(custom_path)
    env_path = os.environ.get("CASAGBI_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_engine(db_path: Optional[str | Path] = None) -> Engine:
    """Obtiene o crea el SQLAlchemy Engine SQLite con WAL y transacciones BEGIN IMMEDIATE."""
    target = get_db_path(db_path).resolve()
    key = str(target)
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]

    target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{target.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 30.0},
        poolclass=NullPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        # Anula isolation_level del driver pysqlite para emitir BEGIN IMMEDIATE explícito.
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _begin_immediate_transaction(conn) -> None:
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    _ENGINE_CACHE[key] = engine
    return engine


def get_session_factory(db_path: Optional[str | Path] = None) -> sessionmaker[Session]:
    """Retorna sessionmaker configurado para el Engine resuelto."""
    target = get_db_path(db_path).resolve()
    key = str(target)
    if key not in _SESSION_FACTORY_CACHE:
        engine = get_engine(target)
        _SESSION_FACTORY_CACHE[key] = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _SESSION_FACTORY_CACHE[key]


def dispose_engines() -> None:
    """Libera todos los motores en caché (útil en pruebas aisladas con tmp_path)."""
    for eng in _ENGINE_CACHE.values():
        eng.dispose()
    _ENGINE_CACHE.clear()
    _SESSION_FACTORY_CACHE.clear()


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Mantiene compatibilidad de conexión directa sqlite3 para utilidades o tests de triggers."""
    target = get_db_path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_database(db_path: Optional[str | Path] = None, seed: bool = True) -> Path:
    """Crea tablas ORM, aplica migración idempotente, triggers y ejecuta seed vía SQLAlchemy."""
    target = get_db_path(db_path)
    engine = get_engine(target)
    Base.metadata.create_all(bind=engine)
    install_audit_immutability_and_migrate_legacy(engine)
    migrate_schema_and_legacy_tickets(engine)

    if seed:
        from src.infrastructure.persistence.seeder import seed_initial_data

        session_factory = get_session_factory(target)
        with session_factory() as session:
            seed_initial_data(session)
            session.commit()

    return target
