"""Implementación concreta en SQLite de los repositorios definidos en el dominio."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.domain.repositories import (
    IAuditRepository,
    ICatalogRepository,
    IKnowledgeRepository,
    INotificationRepository,
    IRefreshTokenRepository,
    ITicketRepository,
    IUserRepository,
)
from src.domain.rules import ASSIGNED_LOAD_STATUSES, format_ticket_number, now_bogota
from src.infrastructure.database import get_connection


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    d = dict(row)
    for bool_col in ("is_active", "privacy_accepted", "revoked", "is_read", "ai_human_validated", "sla_breached", "sla_alert_75_sent"):
        if bool_col in d and d[bool_col] is not None:
            d[bool_col] = bool(d[bool_col])
    return d


class SQLiteUserRepository(IUserRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return _row_to_dict(row)

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)
            ).fetchone()
            return _row_to_dict(row)

    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO users
                (email, full_name, password_hash, role, area, sede, is_active, privacy_accepted, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_data["email"].strip().lower(),
                    user_data["full_name"].strip(),
                    user_data["password_hash"],
                    user_data.get("role", "usuario"),
                    user_data.get("area"),
                    user_data.get("sede", "Sede Sabanas (Valledupar)"),
                    int(bool(user_data.get("is_active", True))),
                    int(bool(user_data.get("privacy_accepted", True))),
                    now_iso,
                ),
            )
            conn.commit()
            return self.get_by_id(cur.lastrowid)  # type: ignore[return-value]

    def update(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not updates:
            return self.get_by_id(user_id)
        allowed = {"full_name", "role", "area", "sede", "is_active", "privacy_accepted", "last_assigned_at"}
        fields = []
        values = []
        for k, v in updates.items():
            if k in allowed:
                fields.append(f"{k} = ?")
                values.append(int(v) if isinstance(v, bool) else v)
        if not fields:
            return self.get_by_id(user_id)
        values.append(user_id)
        with get_connection(self.db_path) as conn:
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        return self.get_by_id(user_id)

    def list_users(
        self,
        role: Optional[str] = None,
        area: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM users WHERE 1=1"
        params: List[Any] = []
        if role:
            query += " AND role = ?"
            params.append(role)
        if area:
            query += " AND area = ?"
            params.append(area)
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(int(is_active))
        if search:
            query += " AND (lower(full_name) LIKE ? OR lower(email) LIKE ?)"
            like_val = f"%{search.strip().lower()}%"
            params.extend([like_val, like_val])
        query += " ORDER BY id ASC"
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def list_active_technicians_with_load(self, area: str) -> List[Dict[str, Any]]:
        placeholders = ",".join("?" for _ in ASSIGNED_LOAD_STATUSES)
        sql = f"""
            SELECT u.*,
                (
                    SELECT COUNT(*) FROM tickets t
                    WHERE t.assigned_tech_id = u.id
                    AND t.status IN ({placeholders})
                ) AS open_tickets_count
            FROM users u
            WHERE u.role = 'tecnico' AND u.is_active = 1 AND u.area = ?
            ORDER BY open_tickets_count ASC, COALESCE(u.last_assigned_at, '0000-01-01T00:00:00') ASC, u.id ASC
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(sql, (*ASSIGNED_LOAD_STATUSES, area)).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def count_active_admins(self) -> int:
        with get_connection(self.db_path) as conn:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
                ).fetchone()[0]
            )


class SQLiteRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def create(self, user_id: int, token_hash: str, expires_at: str) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at, revoked, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (user_id, token_hash, expires_at, now_iso),
            )
            conn.commit()

    def get_valid(self, token_hash: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM refresh_tokens WHERE token_hash = ? AND revoked = 0",
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            record = _row_to_dict(row)
            if record and datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
                return None
            return record

    def revoke(self, token_hash: str) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?",
                (token_hash,),
            )
            conn.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()


class SQLiteTicketRepository(ITicketRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def next_ticket_number(self, year: int = 2026) -> str:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM tickets").fetchone()
            next_seq = int(row["max_id"]) + 1
            return format_ticket_number(next_seq, year=year)

    def create(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        cols = [
            "ticket_number", "title", "description", "ticket_type", "service_name", "area",
            "sede", "location", "impact", "urgency", "priority", "status",
            "requester_id", "requester_email", "requester_role",
            "assigned_tech_id", "assigned_tech_email",
            "sla_response_hours", "sla_resolution_hours",
            "response_deadline", "resolution_deadline",
            "ai_suggested_service", "ai_confidence", "ai_human_validated",
            "created_at", "updated_at",
        ]
        vals = [
            int(ticket_data[c]) if isinstance(ticket_data.get(c), bool) else ticket_data.get(c)
            for c in cols
        ]
        placeholders = ",".join("?" for _ in cols)
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                f"INSERT INTO tickets ({', '.join(cols)}) VALUES ({placeholders})",
                vals,
            )
            conn.commit()
            return self.get_by_id(cur.lastrowid)  # type: ignore[return-value]

    def get_by_id(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            return _row_to_dict(row)

    def get_by_number(self, ticket_number: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE upper(ticket_number) = upper(?)",
                (ticket_number.strip(),),
            ).fetchone()
            return _row_to_dict(row)

    def update(self, ticket_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not updates:
            return self.get_by_id(ticket_id)
        fields = []
        values = []
        for k, v in updates.items():
            fields.append(f"{k} = ?")
            values.append(int(v) if isinstance(v, bool) else v)
        values.append(ticket_id)
        with get_connection(self.db_path) as conn:
            conn.execute(f"UPDATE tickets SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
        return self.get_by_id(ticket_id)

    def list_tickets(
        self,
        requester_id: Optional[int] = None,
        assigned_tech_id: Optional[int] = None,
        area: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        sede: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tickets WHERE 1=1"
        params: List[Any] = []
        if requester_id is not None:
            query += " AND requester_id = ?"
            params.append(requester_id)
        if assigned_tech_id is not None:
            query += " AND assigned_tech_id = ?"
            params.append(assigned_tech_id)
        if area:
            query += " AND area = ?"
            params.append(area)
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if sede:
            query += " AND sede = ?"
            params.append(sede)
        if search:
            query += " AND (upper(ticket_number) LIKE ? OR lower(title) LIKE ? OR lower(description) LIKE ?)"
            s = search.strip()
            params.extend([f"%{s.upper()}%", f"%{s.lower()}%", f"%{s.lower()}%"])
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def add_history(self, entry: Dict[str, Any]) -> None:
        now_iso = entry.get("created_at") or now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ticket_history
                (ticket_id, actor_email, action, old_status, new_status, comment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["ticket_id"],
                    entry["actor_email"],
                    entry["action"],
                    entry.get("old_status"),
                    entry.get("new_status"),
                    entry.get("comment"),
                    now_iso,
                ),
            )
            conn.commit()

    def get_history(self, ticket_id: int) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM ticket_history WHERE ticket_id = ? ORDER BY id ASC",
                (ticket_id,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def add_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = message_data.get("created_at") or now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO ticket_messages
                (ticket_id, sender_id, sender_email, sender_role, message, attachment_name, attachment_path, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    message_data["ticket_id"],
                    message_data["sender_id"],
                    message_data["sender_email"],
                    message_data["sender_role"],
                    message_data["message"],
                    message_data.get("attachment_name"),
                    message_data.get("attachment_path"),
                    now_iso,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM ticket_messages WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return _row_to_dict(row)  # type: ignore[return-value]

    def get_messages(self, ticket_id: int) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM ticket_messages WHERE ticket_id = ? ORDER BY id ASC",
                (ticket_id,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def mark_messages_read(self, ticket_id: int, reader_email: str) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE ticket_messages SET is_read = 1 WHERE ticket_id = ? AND lower(sender_email) != lower(?)",
                (ticket_id, reader_email.strip()),
            )
            conn.commit()


class SQLiteKnowledgeBaseRepository(IKnowledgeRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def list_articles(
        self,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM kb_articles WHERE 1=1"
        params: List[Any] = []
        if visibility:
            query += " AND visibility = ?"
            params.append(visibility)
        if status:
            query += " AND status = ?"
            params.append(status)
        if service_name:
            query += " AND service_name = ?"
            params.append(service_name)
        query += " ORDER BY id ASC"
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def get_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM kb_articles WHERE id = ?", (article_id,)).fetchone()
            return _row_to_dict(row)

    def upsert(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            if article_data.get("id"):
                existing = self.get_by_id(int(article_data["id"]))
                new_ver = (existing["version"] + 1) if existing else 1
                conn.execute(
                    """
                    UPDATE kb_articles
                    SET title = ?, service_name = ?, symptoms = ?, solution_steps = ?,
                        keywords = ?, visibility = ?, status = ?, version = ?,
                        reviewer_email = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        article_data["title"],
                        article_data["service_name"],
                        article_data["symptoms"],
                        article_data["solution_steps"],
                        article_data.get("keywords", ""),
                        article_data.get("visibility", "Pública"),
                        article_data.get("status", "En revisión"),
                        new_ver,
                        article_data.get("reviewer_email"),
                        now_iso,
                        int(article_data["id"]),
                    ),
                )
                conn.commit()
                return self.get_by_id(int(article_data["id"]))  # type: ignore[return-value]

            max_id = int(conn.execute("SELECT COALESCE(MAX(id), 0) FROM kb_articles").fetchone()[0]) + 1
            code = article_data.get("code") or f"KB-{max_id:03d}"
            cur = conn.execute(
                """
                INSERT INTO kb_articles
                (code, title, service_name, symptoms, solution_steps, keywords, visibility, status, version, author_email, reviewer_email, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    code,
                    article_data["title"],
                    article_data["service_name"],
                    article_data["symptoms"],
                    article_data["solution_steps"],
                    article_data.get("keywords", ""),
                    article_data.get("visibility", "Pública"),
                    article_data.get("status", "En revisión"),
                    article_data.get("author_email", "tecnico1@unicesar.edu.co"),
                    article_data.get("reviewer_email"),
                    now_iso,
                ),
            )
            conn.commit()
            return self.get_by_id(cur.lastrowid)  # type: ignore[return-value]


class SQLiteAuditLogRepository(IAuditRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def append(self, log_data: Dict[str, Any]) -> None:
        now_iso = log_data.get("timestamp") or now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                (timestamp, user_email, ip_address, action, entity, entity_id, old_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso,
                    log_data["user_email"],
                    log_data.get("ip_address", "127.0.0.1"),
                    log_data["action"],
                    log_data["entity"],
                    str(log_data["entity_id"]),
                    log_data.get("old_value"),
                    log_data.get("new_value"),
                ),
            )
            conn.commit()

    def list_logs(
        self,
        user_email: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params: List[Any] = []
        if user_email:
            query += " AND lower(user_email) LIKE ?"
            params.append(f"%{user_email.strip().lower()}%")
        if action:
            query += " AND upper(action) LIKE ?"
            params.append(f"%{action.strip().upper()}%")
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]


class SQLiteNotificationRepository(INotificationRepository):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def create(self, notification_data: Dict[str, Any]) -> None:
        now_iso = notification_data.get("created_at") or now_bogota().isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO notifications (user_email, ticket_number, title, message, is_read, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    notification_data["user_email"],
                    notification_data.get("ticket_number"),
                    notification_data["title"],
                    notification_data["message"],
                    now_iso,
                ),
            )
            conn.commit()

    def list_for_user(self, user_email: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        query = "SELECT * FROM notifications WHERE lower(user_email) = lower(?)"
        params: List[Any] = [user_email.strip()]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY id DESC LIMIT 100"
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def mark_all_read(self, user_email: str) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE lower(user_email) = lower(?)",
                (user_email.strip(),),
            )
            conn.commit()


class SQLiteCatalogRepository(ICatalogRepository):
    """Repositorio auxiliar para administrar catálogo de servicios y SLA (RF-24)."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def list_services(self, active_only: bool = False) -> List[Dict[str, Any]]:
        query = "SELECT * FROM service_catalog"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY id ASC"
        with get_connection(self.db_path) as conn:
            rows = conn.execute(query).fetchall()
            return [_row_to_dict(r) for r in rows if r is not None]

    def upsert_service(self, data: Dict[str, Any]) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO service_catalog (service_name, area, base_impact, default_type, description, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(service_name) DO UPDATE SET
                    area = excluded.area,
                    base_impact = excluded.base_impact,
                    default_type = excluded.default_type,
                    description = excluded.description,
                    is_active = excluded.is_active
                """,
                (
                    data["service_name"].strip(),
                    data["area"],
                    data["base_impact"],
                    data.get("default_type", "Incidencia"),
                    data.get("description", ""),
                    int(bool(data.get("is_active", True))),
                ),
            )
            conn.commit()

    def get_sla_table(self) -> Dict[str, Dict[str, float]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM sla_config").fetchall()
            return {
                r["priority"]: {
                    "sla_response_hours": float(r["sla_response_hours"]),
                    "sla_resolution_hours": float(r["sla_resolution_hours"]),
                }
                for r in rows
            }

    def update_sla(self, priority: str, response_hours: float, resolution_hours: float) -> None:
        if resolution_hours < response_hours:
            raise ValueError("El tiempo de resolución no puede ser menor al tiempo de respuesta.")
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sla_config (priority, sla_response_hours, sla_resolution_hours, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(priority) DO UPDATE SET
                    sla_response_hours = excluded.sla_response_hours,
                    sla_resolution_hours = excluded.sla_resolution_hours,
                    updated_at = excluded.updated_at
                """,
                (priority, float(response_hours), float(resolution_hours), now_bogota().isoformat()),
            )
            conn.commit()
