"""Migraciones idempotentes de esquema SQLite y triggers de auditoría inmutable."""

from __future__ import annotations

from typing import Dict

from sqlalchemy import Engine, text

from src.domain.rules import (
    LEGACY_TICKET_NUMBER_PATTERN,
    UPC_SERVICE_CATALOG,
    compute_content_dedup_hash,
    format_ticket_number,
    get_service_prefix,
    now_bogota,
)


def install_audit_immutability_and_migrate_legacy(engine: Engine) -> None:
    """Instala triggers append-only sobre audit_logs y migra historial heredado si existe."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_update
                BEFORE UPDATE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'audit_logs es inmutable (append-only): no se permiten modificaciones');
                END;
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_delete
                BEFORE DELETE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'audit_logs es inmutable (append-only): no se permiten eliminaciones');
                END;
                """
            )
        )
        has_legacy = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ticket_history'")
        ).scalar_one()
        if has_legacy and conn.execute(text("SELECT COUNT(*) FROM ticket_audit_events")).scalar_one() == 0:
            conn.execute(
                text(
                    """
                    INSERT INTO ticket_audit_events
                    (ticket_id, actor_email, action, old_status, new_status, comment, created_at)
                    SELECT ticket_id, actor_email, action, old_status, new_status, comment, created_at
                    FROM ticket_history ORDER BY id ASC
                    """
                )
            )


def _table_columns(conn, table_name: str) -> set[str]:
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()}


def _add_missing_columns(conn, table_name: str, alterations: list[tuple[str, str]]) -> None:
    cols = _table_columns(conn, table_name)
    for col_name, ddl in alterations:
        if col_name not in cols:
            conn.execute(text(ddl))


def _migrate_legacy_ticket_rows(conn, now_iso: str) -> None:
    rows = conn.execute(
        text(
            """
            SELECT id, ticket_number, service_name, requester_id, title,
                   category_prefix, ticket_year, sequence_number,
                   legacy_ticket_number, content_dedup_hash, version
            FROM tickets ORDER BY id ASC
            """
        )
    ).fetchall()
    counters: Dict[tuple[str, int], int] = {
        (str(p), int(y)): int(s)
        for p, y, s in conn.execute(text("SELECT prefix, year, last_seq FROM ticket_counters")).fetchall()
    }
    for row in rows:
        t_id, t_num, svc_name, req_id, title = int(row[0]), str(row[1]), str(row[2]), int(row[3]), str(row[4])
        cur_pref, cur_year, cur_seq = str(row[5] or "GEN"), int(row[6] or 2026), int(row[7] or 1)
        cur_dedup, cur_ver = row[9], int(row[10] or 1)
        dedup = cur_dedup or compute_content_dedup_hash(req_id, svc_name, title)
        leg_match = LEGACY_TICKET_NUMBER_PATTERN.match(t_num.strip().upper())

        if leg_match:
            yr = int(leg_match.group(1))
            pref = get_service_prefix(svc_name)
            next_seq = counters.get((pref, yr), 0) + 1
            counters[(pref, yr)] = next_seq
            new_num = format_ticket_number(next_seq, year=yr, prefix=pref)
            conn.execute(
                text(
                    """
                    UPDATE tickets
                    SET ticket_number = :new_num, legacy_ticket_number = :old_num,
                        category_prefix = :pref, ticket_year = :yr, sequence_number = :seq,
                        content_dedup_hash = :dedup, version = :ver
                    WHERE id = :tid
                    """
                ),
                {
                    "new_num": new_num,
                    "old_num": t_num.strip().upper(),
                    "pref": pref,
                    "yr": yr,
                    "seq": next_seq,
                    "dedup": dedup,
                    "ver": cur_ver,
                    "tid": t_id,
                },
            )
            conn.execute(
                text("UPDATE notifications SET ticket_number = :new_num WHERE ticket_number = :old_num"),
                {"new_num": new_num, "old_num": t_num},
            )
        else:
            if cur_pref == "GEN" and "-" in t_num:
                parts = t_num.split("-")
                if len(parts) == 4:
                    cur_pref, cur_year, cur_seq = parts[1], int(parts[2]), int(parts[3])
            counters[(cur_pref, cur_year)] = max(counters.get((cur_pref, cur_year), 0), cur_seq)
            if cur_dedup is None:
                conn.execute(
                    text(
                        "UPDATE tickets SET content_dedup_hash = :dedup, category_prefix = :pref, "
                        "ticket_year = :yr, sequence_number = :seq WHERE id = :tid"
                    ),
                    {"dedup": dedup, "pref": cur_pref, "yr": cur_year, "seq": cur_seq, "tid": t_id},
                )

    for (pref, yr), max_s in counters.items():
        conn.execute(
            text(
                """
                INSERT INTO ticket_counters (prefix, year, last_seq, updated_at)
                VALUES (:pref, :yr, :seq, :now)
                ON CONFLICT(prefix, year) DO UPDATE SET
                    last_seq = MAX(ticket_counters.last_seq, excluded.last_seq),
                    updated_at = excluded.updated_at
                """
            ),
            {"pref": pref, "yr": yr, "seq": max_s, "now": now_iso},
        )


def migrate_schema_and_legacy_tickets(engine: Engine) -> None:
    """Migración idempotente de columnas, contadores, índices y tokens de recuperación."""
    now_iso = now_bogota().isoformat()
    with engine.begin() as conn:
        _add_missing_columns(
            conn,
            "service_catalog",
            [("category_prefix", "ALTER TABLE service_catalog ADD COLUMN category_prefix TEXT NOT NULL DEFAULT 'GEN'")],
        )
        for svc_name in UPC_SERVICE_CATALOG:
            conn.execute(
                text("UPDATE service_catalog SET category_prefix = :pref WHERE service_name = :svc"),
                {"pref": get_service_prefix(svc_name), "svc": svc_name},
            )

        _add_missing_columns(
            conn,
            "tickets",
            [
                ("category_prefix", "ALTER TABLE tickets ADD COLUMN category_prefix TEXT NOT NULL DEFAULT 'GEN'"),
                ("ticket_year", "ALTER TABLE tickets ADD COLUMN ticket_year INTEGER NOT NULL DEFAULT 2026"),
                ("sequence_number", "ALTER TABLE tickets ADD COLUMN sequence_number INTEGER NOT NULL DEFAULT 1"),
                ("legacy_ticket_number", "ALTER TABLE tickets ADD COLUMN legacy_ticket_number TEXT"),
                ("content_dedup_hash", "ALTER TABLE tickets ADD COLUMN content_dedup_hash TEXT"),
                ("version", "ALTER TABLE tickets ADD COLUMN version INTEGER NOT NULL DEFAULT 1"),
            ],
        )
        _migrate_legacy_ticket_rows(conn, now_iso)

        for ddl in (
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_prefix_year_seq ON tickets(category_prefix, ticket_year, sequence_number)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_legacy_number ON tickets(legacy_ticket_number)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_dedup ON tickets(requester_id, content_dedup_hash, created_at)",
        ):
            conn.execute(text(ddl))

        _add_missing_columns(
            conn,
            "ticket_messages",
            [
                ("client_message_id", "ALTER TABLE ticket_messages ADD COLUMN client_message_id TEXT"),
                ("reply_to_message_id", "ALTER TABLE ticket_messages ADD COLUMN reply_to_message_id INTEGER"),
                ("message_type", "ALTER TABLE ticket_messages ADD COLUMN message_type TEXT NOT NULL DEFAULT 'text'"),
                ("delivered_at", "ALTER TABLE ticket_messages ADD COLUMN delivered_at TEXT"),
                ("read_at", "ALTER TABLE ticket_messages ADD COLUMN read_at TEXT"),
                ("edited_at", "ALTER TABLE ticket_messages ADD COLUMN edited_at TEXT"),
                ("is_deleted", "ALTER TABLE ticket_messages ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"),
            ],
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_msg_sender_client_id "
                "ON ticket_messages(sender_id, client_message_id) WHERE client_message_id IS NOT NULL"
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_msg_ticket_id ON ticket_messages(ticket_id, id)"))

        _add_missing_columns(
            conn,
            "kb_articles",
            [
                ("category_topic", "ALTER TABLE kb_articles ADD COLUMN category_topic TEXT NOT NULL DEFAULT 'General'"),
                (
                    "probable_cause",
                    "ALTER TABLE kb_articles ADD COLUMN probable_cause TEXT NOT NULL DEFAULT 'Por verificar en diagnóstico técnico [CONFIRMAR].'",
                ),
                (
                    "escalation_criteria",
                    "ALTER TABLE kb_articles ADD COLUMN escalation_criteria TEXT NOT NULL DEFAULT 'Escalar a soporte Nivel 2 del área técnica si persiste el incidente.'",
                ),
                ("review_notes", "ALTER TABLE kb_articles ADD COLUMN review_notes TEXT"),
                ("is_demo", "ALTER TABLE kb_articles ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 1"),
                ("created_at", "ALTER TABLE kb_articles ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"),
            ],
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_pwd_reset_user ON password_reset_tokens(user_id, consumed)")
        )
