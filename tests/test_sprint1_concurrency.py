"""Pruebas obligatorias de Sprint 1: radicados por categoría, concurrencia SQLite BEGIN IMMEDIATE, idempotencia y migración."""

from __future__ import annotations

import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.tickets import CreateTicketCommand, CreateTicketCommandHandler
from src.domain.exceptions import ValidationDomainError
from src.domain.rules import (
    CATEGORY_TICKET_NUMBER_PATTERN,
    LEGACY_TICKET_NUMBER_PATTERN,
    SERVICE_CATEGORY_PREFIXES,
    VALID_CATEGORY_PREFIXES,
    format_ticket_number,
    get_service_prefix,
)
from src.domain.value_objects import TicketCode
from src.infrastructure.composition import reset_runtime_dependencies, uow_factory
from src.infrastructure.persistence.database import dispose_engines, get_engine, init_database
from src.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.infrastructure.security.password_hasher import hash_password
from src.main import create_app


@pytest.fixture
def sprint1_client(tmp_path, monkeypatch):
    db_file = tmp_path / "sprint1_api.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.setenv("DEMO_MODE", "true")
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)

    app = create_app()
    with TestClient(app) as client:
        yield client, str(db_file)

    dispose_engines()
    reset_runtime_dependencies()


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "demo_mode": True})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_category_ticket_code_regex_all_prefixes_and_legacy_alias(sprint1_client):
    """Valida los 7 prefijos de TicketCode, compatibilidad de alias legado MS-AAAA-NNNNNN y rechazo inválido."""
    assert set(SERVICE_CATEGORY_PREFIXES.values()).issubset(set(VALID_CATEGORY_PREFIXES))

    for prefix in VALID_CATEGORY_PREFIXES:
        formatted = format_ticket_number(12, year=2026, prefix=prefix)
        assert CATEGORY_TICKET_NUMBER_PATTERN.match(formatted)
        vo = TicketCode(formatted)
        assert vo.value == f"MS-{prefix}-2026-000012"
        assert vo.prefix == prefix
        assert vo.year == 2026
        assert vo.seq == 12
        assert vo.is_legacy is False

    legacy_vo = TicketCode("ms-2026-000001")
    assert legacy_vo.value == "MS-2026-000001"
    assert legacy_vo.is_legacy is True
    assert legacy_vo.prefix is None
    assert legacy_vo.year == 2026
    assert legacy_vo.seq == 1
    assert LEGACY_TICKET_NUMBER_PATTERN.match(legacy_vo.value)

    for bad_code in ("MS-XYZ-2026-000001", "MS-RED-26-000001", "MS-RED-2026-1", "TICKET-1"):
        with pytest.raises(ValidationDomainError):
            TicketCode(bad_code)

    client, _db_path = sprint1_client
    new_pub = client.get("/api/v1/tickets/public/MS-RED-2026-000001")
    alias_pub = client.get("/api/v1/tickets/public/MS-2026-000001")
    assert new_pub.status_code == 200
    assert alias_pub.status_code == 200
    assert new_pub.json()["ticket_number"] == "MS-RED-2026-000001"
    assert alias_pub.json()["ticket_number"] == "MS-RED-2026-000001"
    assert alias_pub.json()["legacy_ticket_number"] == "MS-2026-000001"


def test_200_parallel_ticket_creations_zero_duplicates(tmp_path):
    """200 creaciones concurrentes en 20 hilos no producen radicados duplicados ni huecos de secuencia."""
    db_file = tmp_path / "concurrency_200.db"
    dispose_engines()
    init_database(db_file, seed=True)

    try:
        with SqlAlchemyUnitOfWork(db_path=db_file) as uow:
            requester = uow.users.get_by_email("estudiante@unicesar.edu.co")
            assert requester is not None
            initial_counters = {
                (r[0], int(r[1])): int(r[2])
                for r in uow.session.execute(
                    text("SELECT prefix, year, last_seq FROM ticket_counters")
                ).fetchall()
            }

        services = list(SERVICE_CATEGORY_PREFIXES.keys())
        factory = uow_factory(str(db_file))

        def create_one(idx: int) -> dict:
            svc = services[idx % len(services)]
            handler = CreateTicketCommandHandler(factory)
            return handler.handle(
                CreateTicketCommand(
                    actor=requester,
                    title=f"Incidencia concurrente lote-{idx:03d} laboratorio",
                    description="Prueba de concurrencia con transacciones BEGIN IMMEDIATE en SQLite.",
                    ticket_type="Incidencia",
                    service_name=svc,
                    sede="Sede Sabanas (Valledupar)",
                    location="Laboratorios de Cómputo",
                    urgency="Media",
                )
            )

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(create_one, i) for i in range(200)]
            results = [fut.result() for fut in futures]

        assert len(results) == 200
        codes = [r["ticket_number"] for r in results]
        assert len(set(codes)) == 200
        assert all(CATEGORY_TICKET_NUMBER_PATTERN.match(c) for c in codes)

        by_prefix: dict[str, list[int]] = {}
        for r in results:
            by_prefix.setdefault(r["category_prefix"], []).append(int(r["sequence_number"]))

        engine = get_engine(db_file)
        with engine.connect() as conn:
            final_counters = {
                (r[0], int(r[1])): int(r[2])
                for r in conn.execute(
                    text("SELECT prefix, year, last_seq FROM ticket_counters")
                ).fetchall()
            }
            total_rows = int(conn.execute(text("SELECT COUNT(*) FROM tickets")).scalar_one())

        assert total_rows == 6 + 200
        for pref, seqs in by_prefix.items():
            start = initial_counters.get((pref, 2026), 0)
            expected = list(range(start + 1, start + len(seqs) + 1))
            assert sorted(seqs) == expected
            assert final_counters[(pref, 2026)] == expected[-1]
    finally:
        dispose_engines()


def test_parallel_assignments_balanced_across_technicians_and_coordinator_queue(tmp_path):
    """Enrutamiento paralelo reparte carga equitativa entre técnicos y usa cola del coordinador si no hay activos."""
    db_file = tmp_path / "parallel_assign.db"
    dispose_engines()
    init_database(db_file, seed=True)

    try:
        with SqlAlchemyUnitOfWork(db_path=db_file) as uow:
            requester = uow.users.get_by_email("docente@unicesar.edu.co")
            coordinator = uow.users.get_by_email("coordinador@unicesar.edu.co")
            assert requester is not None and coordinator is not None

            # Desactivar técnico semilla de Redes para aislar a 2 técnicos nuevos con carga inicial 0
            for existing in uow.users.list_users(role="tecnico", area="Redes e Infraestructura"):
                uow.users.update(int(existing["id"]), {"is_active": False})

            tech_a = uow.users.create(
                {
                    "email": "redes.a@unicesar.edu.co",
                    "full_name": "Técnico Redes A",
                    "password_hash": hash_password("UpcPassword2026!"),
                    "role": "tecnico",
                    "area": "Redes e Infraestructura",
                    "sede": "Sede Sabanas (Valledupar)",
                    "is_active": True,
                }
            )
            tech_b = uow.users.create(
                {
                    "email": "redes.b@unicesar.edu.co",
                    "full_name": "Técnico Redes B",
                    "password_hash": hash_password("UpcPassword2026!"),
                    "role": "tecnico",
                    "area": "Redes e Infraestructura",
                    "sede": "Sede Sabanas (Valledupar)",
                    "is_active": True,
                }
            )
            # Desactivar todos los técnicos de Mesa de Software para verificar cola del coordinador
            for sw_tech in uow.users.list_users(role="tecnico", area="Mesa de Software"):
                uow.users.update(int(sw_tech["id"]), {"is_active": False})
            uow.commit()

        factory = uow_factory(str(db_file))

        def create_net_ticket(idx: int) -> dict:
            return CreateTicketCommandHandler(factory).handle(
                CreateTicketCommand(
                    actor=requester,
                    title=f"Corte WiFi concurrente bloque-{idx:02d}",
                    description="Verificación de balanceo de carga bajo creación concurrente.",
                    ticket_type="Incidencia",
                    service_name="Conectividad y Redes Wi-Fi",
                    sede="Sede Sabanas (Valledupar)",
                    location="Bloque B",
                    urgency="Alta",
                )
            )

        with ThreadPoolExecutor(max_workers=10) as pool:
            assigned_tickets = [f.result() for f in [pool.submit(create_net_ticket, i) for i in range(20)]]

        assert all(t["status"] == "Asignado" for t in assigned_tickets)
        count_a = sum(1 for t in assigned_tickets if t["assigned_tech_id"] == int(tech_a["id"]))
        count_b = sum(1 for t in assigned_tickets if t["assigned_tech_id"] == int(tech_b["id"]))
        assert count_a + count_b == 20
        assert abs(count_a - count_b) <= 1

        # Ticket sin técnicos activos -> cola del coordinador sin romperse
        orphan_case = CreateTicketCommandHandler(factory).handle(
            CreateTicketCommand(
                actor=requester,
                title="Solicitud licencia IDE sin técnicos activos",
                description="El área Mesa de Software no tiene técnicos disponibles temporalmente.",
                ticket_type="Solicitud",
                service_name="Software y Licenciamiento",
                sede="Sede Hurtado (Valledupar)",
                location="Laboratorios de Cómputo",
                urgency="Baja",
            )
        )
        assert orphan_case["status"] == "Registrado"
        assert orphan_case["assigned_tech_id"] is None

        with SqlAlchemyUnitOfWork(db_path=db_file) as uow:
            events = uow.tickets.get_audit_events(int(orphan_case["id"]))
            notifs = uow.notifications.list_for_user(coordinator["email"], unread_only=True)

        assert any("cola del coordinador" in e["action"].lower() for e in events)
        assert any(n.get("ticket_number") == orphan_case["ticket_number"] for n in notifs)
    finally:
        dispose_engines()


def test_idempotency_key_and_2min_exact_content_deduplication(sprint1_client):
    """Idempotency-Key repetida devuelve el mismo ticket y deduplicación exacta en 2 min evita falsos positivos."""
    client, _db_path = sprint1_client
    headers = _auth_header(client, "estudiante@unicesar.edu.co")

    payload_1 = {
        "title": "  Caída   WiFi   Bíblioteca ",
        "description": "No responde ningún punto de acceso inalámbrico en el segundo piso de biblioteca.",
        "service_name": "Conectividad y Redes Wi-Fi",
        "sede": "Sede Sabanas (Valledupar)",
        "location": "Biblioteca",
        "urgency": "Alta",
    }

    r1 = client.post("/api/v1/tickets", json=payload_1, headers={**headers, "Idempotency-Key": "idem-upc-001"})
    assert r1.status_code == 201, r1.text
    t1 = r1.json()
    assert t1["deduplicated"] is False
    assert t1["ticket_number"].startswith("MS-RED-2026-")

    # Replay con la misma Idempotency-Key -> devuelve exactamente el mismo radicado
    r2 = client.post("/api/v1/tickets", json=payload_1, headers={**headers, "Idempotency-Key": "idem-upc-001"})
    assert r2.status_code == 200, r2.text
    t2 = r2.json()
    assert t2["deduplicated"] is True
    assert t2["dedup_reason"] == "idempotency_key"
    assert t2["id"] == t1["id"]
    assert t2["ticket_number"] == t1["ticket_number"]

    # Distinta Idempotency-Key, mismo usuario + servicio + asunto normalizado equivalente dentro de 2 minutos
    payload_norm_dup = {
        **payload_1,
        "title": "caida wifi biblioteca",
    }
    r3 = client.post(
        "/api/v1/tickets",
        json=payload_norm_dup,
        headers={**headers, "Idempotency-Key": "idem-upc-002"},
    )
    assert r3.status_code == 200, r3.text
    t3 = r3.json()
    assert t3["deduplicated"] is True
    assert t3["dedup_reason"] == "content_duplicate_2m"
    assert t3["id"] == t1["id"]

    # Asunto similar pero distinto (no usa similitud difusa) -> SÍ crea un segundo ticket
    payload_distinct = {
        **payload_1,
        "title": "Caida WiFi Biblioteca ala norte",
    }
    r4 = client.post(
        "/api/v1/tickets",
        json=payload_distinct,
        headers={**headers, "Idempotency-Key": "idem-upc-003"},
    )
    assert r4.status_code == 201, r4.text
    t4 = r4.json()
    assert t4["deduplicated"] is False
    assert t4["id"] != t1["id"]
    assert t4["ticket_number"] != t1["ticket_number"]


def test_optimistic_concurrency_version_conflict_returns_409_problem_details(sprint1_client):
    """Una versión obsoleta en transición o reasignación produce HTTP 409 RFC 7807."""
    client, _db_path = sprint1_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")

    created = client.post(
        "/api/v1/tickets",
        json={
            "title": "Sin enlace en punto de red Sala 204",
            "description": "El switch de pared no entrega IP al equipo docente.",
            "service_name": "Conectividad y Redes Wi-Fi",
            "sede": "Sede Sabanas (Valledupar)",
            "location": "Bloque B",
            "urgency": "Media",
        },
        headers=student_headers,
    )
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["version"] == 1

    # Técnico 1 actualiza con version=1 -> pasa a version=2
    tr_ok = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        json={"new_status": "En atención", "version": 1},
        headers=tech_headers,
    )
    assert tr_ok.status_code == 200, tr_ok.text
    assert tr_ok.json()["version"] == 2

    # Coordinador intenta reasignar usando la versión obsoleta version=1 -> 409 Conflict RFC 7807
    reassign_conflict = client.post(
        f"/api/v1/tickets/{ticket['id']}/reassign",
        json={
            "new_tech_id": int(ticket["assigned_tech_id"]),
            "reason": "Balanceo manual tras detección de cambio concurrente.",
            "version": 1,
        },
        headers=coord_headers,
    )
    assert reassign_conflict.status_code == 409
    assert reassign_conflict.headers["content-type"].startswith("application/problem+json")
    problem = reassign_conflict.json()
    assert problem["status"] == 409
    assert "resource-conflict" in problem["type"]


def test_idempotent_migration_on_database_with_legacy_tickets(tmp_path):
    """Migra una BD heredada (MS-AAAA-NNNNNN sin columnas Sprint 1) preservando alias legado de manera idempotente."""
    legacy_db = tmp_path / "legacy_pre_sprint1.db"
    dispose_engines()

    conn = sqlite3.connect(legacy_db)
    try:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                area TEXT,
                sede TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                privacy_accepted INTEGER NOT NULL DEFAULT 1,
                last_assigned_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE service_catalog (
                service_name TEXT PRIMARY KEY,
                area TEXT NOT NULL,
                base_impact TEXT NOT NULL,
                default_type TEXT NOT NULL,
                description TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                ticket_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                area TEXT NOT NULL,
                sede TEXT NOT NULL,
                location TEXT NOT NULL,
                impact TEXT NOT NULL,
                urgency TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                requester_id INTEGER NOT NULL,
                requester_email TEXT NOT NULL,
                requester_role TEXT NOT NULL,
                assigned_tech_id INTEGER,
                assigned_tech_email TEXT,
                sla_response_hours REAL NOT NULL,
                sla_resolution_hours REAL NOT NULL,
                response_deadline TEXT,
                resolution_deadline TEXT,
                first_response_at TEXT,
                paused_at TEXT,
                paused_seconds INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT,
                closed_at TEXT,
                diagnosis TEXT,
                solution TEXT,
                closing_category TEXT,
                csat_score INTEGER,
                csat_comment TEXT,
                ai_suggested_service TEXT,
                ai_confidence REAL,
                ai_human_validated INTEGER NOT NULL DEFAULT 0,
                priority_justification TEXT,
                sla_breached INTEGER NOT NULL DEFAULT 0,
                sla_alert_75_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                ticket_number TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO users (id, email, full_name, password_hash, role, area, sede, created_at) "
            "VALUES (1, 'est@unicesar.edu.co', 'Est', 'hash', 'usuario', 'Comunidad Universitaria', 'Sede Sabanas (Valledupar)', '2026-01-10T09:00:00-05:00')"
        )
        conn.execute(
            "INSERT INTO service_catalog VALUES ('Conectividad y Redes Wi-Fi', 'Redes e Infraestructura', 'Alto', 'Incidencia', 'WiFi', 1, '2026-01-10T09:00:00-05:00')"
        )
        conn.execute(
            """
            INSERT INTO tickets (
                id, ticket_number, title, description, ticket_type, service_name, area, sede, location,
                impact, urgency, priority, status, requester_id, requester_email, requester_role,
                sla_response_hours, sla_resolution_hours, created_at, updated_at
            ) VALUES
            (1, 'MS-2026-000001', 'Sin wifi', 'Detalle wifi heredado', 'Incidencia', 'Conectividad y Redes Wi-Fi',
             'Redes e Infraestructura', 'Sede Sabanas (Valledupar)', 'Bloque A', 'Alto', 'Alta', 'P1 Crítica',
             'Registrado', 1, 'est@unicesar.edu.co', 'Usuario institucional', 0.5, 4.0,
             '2026-01-10T09:00:00-05:00', '2026-01-10T09:00:00-05:00'),
            (2, 'MS-2026-000002', 'Clave correo', 'Bloqueo cuenta heredado', 'Solicitud', 'Correo Institucional y Cuentas',
             'Identidad y Accesos', 'Sede Sabanas (Valledupar)', 'Biblioteca', 'Medio', 'Media', 'P3 Media',
             'Registrado', 1, 'est@unicesar.edu.co', 'Usuario institucional', 4.0, 24.0,
             '2026-01-11T09:00:00-05:00', '2026-01-11T09:00:00-05:00')
            """
        )
        conn.execute(
            "INSERT INTO notifications (user_email, ticket_number, title, message, is_read, created_at) "
            "VALUES ('est@unicesar.edu.co', 'MS-2026-000001', 'Notif', 'Msg', 0, '2026-01-10T09:00:00-05:00')"
        )
        conn.commit()
    finally:
        conn.close()

    try:
        # Ejecutar migración dos veces seguidas para comprobar idempotencia total
        init_database(legacy_db, seed=False)
        init_database(legacy_db, seed=False)

        with SqlAlchemyUnitOfWork(db_path=legacy_db) as uow:
            by_new_1 = uow.tickets.get_by_number("MS-RED-2026-000001")
            by_alias_1 = uow.tickets.get_by_number("MS-2026-000001")
            by_alias_2 = uow.tickets.get_by_number("MS-2026-000002")
            notifs = uow.notifications.list_for_user("est@unicesar.edu.co")
            counters = {
                (r[0], int(r[1])): int(r[2])
                for r in uow.session.execute(
                    text("SELECT prefix, year, last_seq FROM ticket_counters")
                ).fetchall()
            }

        assert by_new_1 is not None and by_alias_1 is not None
        assert by_new_1["id"] == by_alias_1["id"] == 1
        assert by_new_1["legacy_ticket_number"] == "MS-2026-000001"
        assert by_new_1["version"] == 1

        assert by_alias_2 is not None
        assert by_alias_2["ticket_number"] == f"MS-{get_service_prefix('Correo Institucional y Cuentas')}-2026-000001"
        assert by_alias_2["legacy_ticket_number"] == "MS-2026-000002"

        assert notifs[0]["ticket_number"] == "MS-RED-2026-000001"
        assert counters[("RED", 2026)] == 1
        assert counters[("ACC", 2026)] == 1
    finally:
        dispose_engines()
