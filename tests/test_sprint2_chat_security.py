"""Pruebas obligatorias de Sprint 2: acceso externo seguro, WS sin JWT en URL, edición/borrado lógico y adjuntos."""

from __future__ import annotations

import io
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.websockets import WebSocketDisconnect

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.tickets import GUEST_OTP_OUTBOX
from src.infrastructure.composition import reset_runtime_dependencies
from src.infrastructure.persistence.database import dispose_engines, get_engine, init_database
from src.main import create_app


@pytest.fixture
def sprint2_client(tmp_path, monkeypatch):
    db_file = tmp_path / "sprint2_chat.db"
    att_dir = tmp_path / "private_attachments"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.setenv("CASAGBI_ATTACHMENTS_DIR", str(att_dir))
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("GUEST_OTP_ENABLED", raising=False)
    GUEST_OTP_OUTBOX.clear()
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)

    app = create_app()
    with TestClient(app) as client:
        yield client, str(db_file), att_dir

    dispose_engines()
    reset_runtime_dependencies()


def _recv_until(ws, expected_type: str, max_frames: int = 5) -> dict:
    for _ in range(max_frames):
        evt = ws.receive_json()
        if evt.get("type") == expected_type:
            return evt
    raise AssertionError(f"No se recibió evento WS '{expected_type}' en {max_frames} tramas")


def _auth_header(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "demo_mode": True})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _create_ticket(client: TestClient, headers: dict[str, str], title: str) -> dict:
    res = client.post(
        "/api/v1/tickets",
        json={
            "title": title,
            "description": "Caso de prueba Sprint 2 para chat multimedia y acceso externo seguro.",
            "service_name": "Conectividad y Redes Wi-Fi",
            "sede": "Sede Sabanas (Valledupar)",
            "location": "Bloque A",
            "urgency": "Media",
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), res.text
    return res.json()


def test_public_lookup_anti_enumeration_and_masked_email(sprint2_client, monkeypatch):
    """Radicado inexistente vs correo incorrecto son indistinguibles; válido emite guest token 2h con correo enmascarado."""
    client, _db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba anti enumeracion lookup")

    # 1. Radicado existente con correo equivocado
    r_wrong_email = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": ticket["ticket_number"], "email": "intruso@unicesar.edu.co"},
    )
    # 2. Radicado inexistente (con formato válido)
    r_missing_ticket = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": "MS-RED-2026-999999", "email": "intruso@unicesar.edu.co"},
    )
    # 3. Formato inválido
    r_bad_format = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": "NO-EXISTE", "email": "intruso@unicesar.edu.co"},
    )

    assert r_wrong_email.status_code == r_missing_ticket.status_code == r_bad_format.status_code == 401
    b1, b2, b3 = r_wrong_email.json(), r_missing_ticket.json(), r_bad_format.json()
    for field in ("type", "title", "status", "detail", "code"):
        assert b1[field] == b2[field] == b3[field]

    # 4. Lookup válido ignorando mayúsculas en correo
    r_ok = client.post(
        "/api/v1/tickets/public/lookup",
        json={
            "ticket_code": ticket["ticket_number"].lower(),
            "email": "ESTUDIANTE@UNICESAR.EDU.CO",
        },
    )
    assert r_ok.status_code == 200, r_ok.text
    ok_json = r_ok.json()
    assert ok_json["otp_required"] is False
    assert ok_json["role"] == "invitado"
    assert ok_json["expires_in"] == 7200
    assert ok_json["masked_email"] == "es***@unicesar.edu.co"
    assert "estudiante@unicesar.edu.co" not in r_ok.text.lower()
    assert ok_json["ticket_guest_token"]

    # 5. Bandera opcional GUEST_OTP_ENABLED=true exige segundo paso OTP (outbox demo)
    monkeypatch.setenv("GUEST_OTP_ENABLED", "true")
    r_otp_step1 = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": ticket["ticket_number"], "email": "estudiante@unicesar.edu.co"},
    )
    assert r_otp_step1.status_code == 200
    assert r_otp_step1.json()["otp_required"] is True
    otp_code = GUEST_OTP_OUTBOX[(ticket["ticket_number"], "estudiante@unicesar.edu.co")]
    r_otp_step2 = client.post(
        "/api/v1/tickets/public/lookup",
        json={
            "ticket_code": ticket["ticket_number"],
            "email": "estudiante@unicesar.edu.co",
            "otp_code": otp_code,
        },
    )
    assert r_otp_step2.status_code == 200
    assert r_otp_step2.json()["ticket_guest_token"]


def test_public_lookup_rate_limit_lockout_and_audit_log(sprint2_client):
    """Múltiples intentos fallidos bloquean temporalmente (HTTP 429) y dejan trazabilidad en audit_logs."""
    client, db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba bloqueo lookup fuerza bruta")

    for _ in range(5):
        resp = client.post(
            "/api/v1/tickets/public/lookup",
            json={"ticket_code": ticket["ticket_number"], "email": "atacante@unicesar.edu.co"},
        )
        assert resp.status_code == 401

    # Intento 6 -> bloqueado incluso enviando correo válido antes de vencer bloqueo
    blocked = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": ticket["ticket_number"], "email": "estudiante@unicesar.edu.co"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["content-type"].startswith("application/problem+json")
    assert blocked.json()["code"] == "TOO_MANY_ATTEMPTS"

    engine = get_engine(db_file)
    with engine.connect() as conn:
        actions = [
            row[0]
            for row in conn.execute(text("SELECT action FROM audit_logs ORDER BY id DESC LIMIT 20")).fetchall()
        ]
    assert "PUBLIC_LOOKUP_FAILED" in actions
    assert "PUBLIC_LOOKUP_BLOCKED" in actions


def test_guest_token_scope_isolation(sprint2_client):
    """El ticket_guest_token solo accede al ticket consultado; otro ticket y endpoints staff devuelven 403."""
    client, _db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    docente_headers = _auth_header(client, "docente@unicesar.edu.co")

    ticket_a = _create_ticket(client, student_headers, "Ticket A de invitado aislado")
    ticket_b = _create_ticket(client, docente_headers, "Ticket B de otro usuario")

    lookup = client.post(
        "/api/v1/tickets/public/lookup",
        json={"ticket_code": ticket_a["ticket_number"], "email": "estudiante@unicesar.edu.co"},
    )
    assert lookup.status_code == 200
    guest_headers = {"Authorization": f"Bearer {lookup.json()['ticket_guest_token']}"}

    # Permitido sobre Ticket A
    detail_a = client.get(f"/api/v1/tickets/{ticket_a['id']}", headers=guest_headers)
    assert detail_a.status_code == 200
    assert "estudiante@unicesar.edu.co" not in detail_a.text.lower()

    send_a = client.post(
        f"/api/v1/tickets/{ticket_a['id']}/messages",
        json={"content": "Mensaje enviado como invitado externo"},
        headers=guest_headers,
    )
    assert send_a.status_code == 201
    assert send_a.json()["message"]["sender_email"] == "es***@unicesar.edu.co"

    # Bloqueado sobre Ticket B
    assert client.get(f"/api/v1/tickets/{ticket_b['id']}", headers=guest_headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_b['id']}/messages",
            json={"content": "Intento no autorizado"},
            headers=guest_headers,
        ).status_code
        == 403
    )

    # Bloqueado sobre endpoints de cuenta/staff
    assert client.get("/api/v1/tickets", headers=guest_headers).status_code == 403
    assert client.get("/api/v1/auth/me", headers=guest_headers).status_code == 403
    assert client.get("/api/v1/analytics/kpis", headers=guest_headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_a['id']}/transition",
            json={"new_status": "En atención"},
            headers=guest_headers,
        ).status_code
        == 403
    )


def test_websocket_one_time_ticket_and_first_message_auth(sprint2_client):
    """Ticket WS es de un solo uso y también funciona la autenticación en el primer mensaje sin token en URL."""
    client, _db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba WS ticket un solo uso")

    ws_ticket_res = client.post(f"/api/v1/tickets/{ticket['id']}/ws-ticket", headers=student_headers)
    assert ws_ticket_res.status_code == 200
    ws_ticket = ws_ticket_res.json()["ws_ticket"]

    # 1. Primer uso válido de ws_ticket
    with client.websocket_connect(f"/api/v1/ws/tickets/{ticket['id']}?ws_ticket={ws_ticket}") as ws:
        ready = _recv_until(ws, "ready")
        assert ready["type"] == "ready"

    # 2. Segundo uso del mismo ws_ticket -> debe rechazarse
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/tickets/{ticket['id']}?ws_ticket={ws_ticket}") as ws_reused:
            ws_reused.receive_json()

    # 3. Autenticación por primer mensaje sin ningún secreto en querystring
    tech_jwt = tech_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/api/v1/ws/tickets/{ticket['id']}?auth=first_message") as ws_first:
        ws_first.send_json({"type": "auth", "token": tech_jwt})
        ready = _recv_until(ws_first, "ready")
        assert ready["type"] == "ready"
        ws_first.send_json({"type": "typing", "is_typing": True})
        typing_evt = _recv_until(ws_first, "typing")
        assert typing_evt["type"] == "typing"


def test_message_edit_at_299s_succeeds_and_301s_fails_with_edit_window_expired(sprint2_client):
    """Edición válida hasta 300 s (299 s pasa); fuera de plazo (301 s) responde 403 EDIT_WINDOW_EXPIRED."""
    client, db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba ventana edicion 5 minutos")

    m_ok = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"content": "Texto original 299s"},
        headers=student_headers,
    ).json()["message"]

    m_late = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"content": "Texto original 301s"},
        headers=student_headers,
    ).json()["message"]

    now_utc = datetime.now(timezone.utc)
    engine = get_engine(db_file)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE ticket_messages SET created_at = :ts WHERE id = :mid"),
            {"ts": (now_utc - timedelta(seconds=299)).isoformat(), "mid": m_ok["id"]},
        )
        conn.execute(
            text("UPDATE ticket_messages SET created_at = :ts WHERE id = :mid"),
            {"ts": (now_utc - timedelta(seconds=301)).isoformat(), "mid": m_late["id"]},
        )

    # Edición a los 299 s -> Éxito
    res_299 = client.patch(
        f"/api/v1/tickets/{ticket['id']}/messages/{m_ok['id']}",
        json={"content": "Texto corregido dentro de ventana"},
        headers=student_headers,
    )
    assert res_299.status_code == 200, res_299.text
    edited_msg = res_299.json()["message"]
    assert edited_msg["message"] == "Texto corregido dentro de ventana"
    assert edited_msg["edited_at"] is not None

    # Edición por otro usuario dentro de ventana -> 403
    res_other = client.patch(
        f"/api/v1/tickets/{ticket['id']}/messages/{m_ok['id']}",
        json={"content": "Intento de técnico"},
        headers=tech_headers,
    )
    assert res_other.status_code == 403

    # Edición a los 301 s -> 403 EDIT_WINDOW_EXPIRED (RFC 7807)
    res_301 = client.patch(
        f"/api/v1/tickets/{ticket['id']}/messages/{m_late['id']}",
        json={"content": "Intento fuera de plazo"},
        headers=student_headers,
    )
    assert res_301.status_code == 403
    assert res_301.headers["content-type"].startswith("application/problem+json")
    assert res_301.json()["code"] == "EDIT_WINDOW_EXPIRED"

    with engine.connect() as conn:
        versions = conn.execute(
            text("SELECT previous_content, action FROM message_versions WHERE message_id = :mid"),
            {"mid": m_ok["id"]},
        ).fetchall()
    assert versions == [("Texto original 299s", "edit")]


def test_logical_delete_shows_placeholder_and_preserves_original_in_versions(sprint2_client):
    """Eliminación lógica muestra placeholder a participantes, emite message_deleted y guarda original."""
    client, db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba borrado logico chat")

    secret_text = "Contraseña temporal errónea: Abc#2026"
    created = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"content": secret_text},
        headers=student_headers,
    ).json()["message"]

    ws_tkt = client.post(f"/api/v1/tickets/{ticket['id']}/ws-ticket", headers=tech_headers).json()["ws_ticket"]
    with client.websocket_connect(f"/api/v1/ws/tickets/{ticket['id']}?ws_ticket={ws_tkt}") as tech_ws:
        assert _recv_until(tech_ws, "ready")["type"] == "ready"

        del_res = client.delete(
            f"/api/v1/tickets/{ticket['id']}/messages/{created['id']}",
            headers=student_headers,
        )
        assert del_res.status_code == 200
        assert del_res.json()["message"]["is_deleted"] is True
        assert del_res.json()["message"]["message"] == "Este mensaje fue eliminado"

        ws_evt = _recv_until(tech_ws, "message_deleted")
        assert ws_evt["type"] == "message_deleted"
        assert ws_evt["message"]["message"] == "Este mensaje fue eliminado"

    # Consulta de participantes muestra el mensaje retirado
    listed = client.get(f"/api/v1/tickets/{ticket['id']}/messages", headers=tech_headers).json()["messages"]
    target = next(m for m in listed if m["id"] == created["id"])
    assert target["is_deleted"] is True
    assert target["message"] == "Este mensaje fue eliminado"

    # El contenido original permanece inmutable en message_versions y audit_logs
    engine = get_engine(db_file)
    with engine.connect() as conn:
        vers = conn.execute(
            text("SELECT previous_content, action FROM message_versions WHERE message_id = :mid"),
            {"mid": created["id"]},
        ).fetchall()
        audit = conn.execute(
            text("SELECT old_value FROM audit_logs WHERE action = 'MESSAGE_DELETED' AND entity_id = :eid"),
            {"eid": str(created["id"])},
        ).fetchall()
    assert vers == [(secret_text, "delete")]
    assert audit == [(secret_text,)]


def test_client_message_id_idempotency_avoids_duplicate_messages(sprint2_client):
    """Reintentos con el mismo client_message_id del autor no crean mensajes duplicados."""
    client, _db_file, _att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba client_message_id idempotente")

    r1 = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"content": "Reintento seguro #1", "client_message_id": "cli-msg-uuid-001"},
        headers=student_headers,
    )
    r2 = client.post(
        f"/api/v1/tickets/{ticket['id']}/messages",
        json={"content": "Reintento seguro #1", "client_message_id": "cli-msg-uuid-001"},
        headers=student_headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["message"]["id"] == r2.json()["message"]["id"]

    msgs = client.get(f"/api/v1/tickets/{ticket['id']}/messages", headers=student_headers).json()["messages"]
    matching = [m for m in msgs if m.get("client_message_id") == "cli-msg-uuid-001"]
    assert len(matching) == 1


def test_attachment_rejects_renamed_executable_and_enforces_signed_download_url(sprint2_client):
    """Rechaza ejecutable renombrado a .pdf y exige enlace firmado de 10 min o autorización para descargar."""
    client, _db_file, att_dir = sprint2_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    ticket = _create_ticket(client, student_headers, "Prueba adjuntos magic bytes y enlace firmado")

    # 1. Ejecutable PE (MZ...) disfrazado como .pdf -> 422 INVALID_FILE_SIGNATURE
    fake_exe_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00payload-malicioso"
    bad_pdf = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files=[("files", ("factura_sospechosa.pdf", fake_exe_pdf, "application/pdf"))],
        headers=student_headers,
    )
    assert bad_pdf.status_code == 422, bad_pdf.text
    assert bad_pdf.json()["code"] == "INVALID_FILE_SIGNATURE"

    # 2. SVG prohibido y ZIP genérico renombrado a .docx -> rechazados
    bad_svg = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files=[("files", ("icono.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml"))],
        headers=student_headers,
    )
    assert bad_svg.status_code == 422

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("random.txt", "solo zip")
    bad_zip_docx = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files=[("files", ("falso.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        headers=student_headers,
    )
    assert bad_zip_docx.status_code == 422

    # 3. PDF real + nota de voz WAV real -> éxito, guardado fuera de static/
    real_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
    real_wav = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    ok_upload = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files=[
            ("files", ("../../evil/../evidencia.pdf", real_pdf, "application/pdf")),
            ("files", ("nota_voz.wav", real_wav, "audio/wav")),
        ],
        data={"audio_duration_seconds": "12", "content": "Adjunto evidencia y audio"},
        headers=student_headers,
    )
    assert ok_upload.status_code == 201, ok_upload.text
    msg = ok_upload.json()["message"]
    assert len(msg["attachments"]) == 2
    pdf_att = msg["attachments"][0]
    assert pdf_att["original_name"] == "evidencia.pdf"  # nombre saneado sin path traversal

    # Almacenado en att_dir privado, jamás en static/
    saved_files = list(att_dir.rglob("*"))
    assert any(p.is_file() for p in saved_files)
    assert "static" not in str(att_dir).lower()

    signed_url = pdf_att["signed_download_url"]
    base_download_url = signed_url.split("?", 1)[0]

    # 4. Descarga sin enlace válido ni token -> 403
    no_auth = client.get(base_download_url)
    assert no_auth.status_code == 403

    # Descarga con firma adulterada o expirada -> 403
    tampered = client.get(f"{base_download_url}?expires=9999999999&sig=firmafalsa")
    assert tampered.status_code == 403
    expired = client.get(f"{base_download_url}?expires=1000000&sig=0000")
    assert expired.status_code == 403

    # 5. Descarga con enlace firmado válido de 10 minutos -> 200 con cabeceras de seguridad
    valid_dl = client.get(signed_url)
    assert valid_dl.status_code == 200
    assert valid_dl.content == real_pdf
    assert valid_dl.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in valid_dl.headers["content-disposition"]
    assert "evidencia.pdf" in valid_dl.headers["content-disposition"]
