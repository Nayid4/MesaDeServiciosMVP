"""Pruebas de arquitectura FastAPI: Clean Architecture, UoW, JWT, RFC 7807 y WebSockets."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.websockets import WebSocketDisconnect

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.composition import reset_runtime_dependencies
from src.infrastructure.persistence.database import dispose_engines, get_engine, init_database
from src.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.main import create_app


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_file = tmp_path / "tickets_pruebas_fastapi.db"
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


def test_clean_architecture_dependency_boundaries():
    """Domain y Application no deben importar fastapi, sqlalchemy ni starlette."""
    forbidden = re.compile(r"^\s*(from|import)\s+(fastapi|sqlalchemy|starlette|streamlit)\b", re.MULTILINE)
    for layer in ("domain", "application"):
        for py_file in (ROOT_DIR / "src" / layer).rglob("*.py"):
            txt = py_file.read_text(encoding="utf-8")
            assert not forbidden.search(txt), f"Violación de regla de dependencia en {py_file}"


def test_unit_of_work_atomicity_and_immutable_audit_log(api_client):
    _client, db_path = api_client

    # Simular fallo dentro de UoW -> debe hacer rollback atómico sin persistir registro
    with pytest.raises(RuntimeError, match="rollback_test"):
        with SqlAlchemyUnitOfWork(db_path=db_path) as uow:
            uow.audit_logs.append(
                {
                    "user_email": "rollback@unicesar.edu.co",
                    "action": "SHOULD_NOT_EXIST",
                    "entity": "test",
                    "entity_id": "tx-rollback",
                }
            )
            raise RuntimeError("rollback_test")

    with SqlAlchemyUnitOfWork(db_path=db_path) as uow:
        rows = uow.audit_logs.list_logs(action="SHOULD_NOT_EXIST")
    assert rows == []

    # Trigger inmutable append-only en SQLite impide UPDATE y DELETE sobre audit_logs
    engine = get_engine(db_path)
    with pytest.raises(Exception, match="inmutable"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE audit_logs SET action = 'ALTERED'"))


def test_jwt_login_refresh_rotation_and_logout_flow(api_client):
    client, _ = api_client

    # Login con cuenta real sembrada
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "estudiante@unicesar.edu.co", "password": "User2026*"},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    access_1 = data["access_token"]
    refresh_1 = data["refresh_token"]
    assert data["user"]["role"] == "usuario"

    # GET /me autenticado
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_1}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == "estudiante@unicesar.edu.co"

    # Refresh token con rotación estricta
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_1})
    assert ref_res.status_code == 200
    refresh_2 = ref_res.json()["refresh_token"]
    access_2 = ref_res.json()["access_token"]
    assert refresh_2 != refresh_1

    # Reutilizar refresh_1 revocado debe responder 401 RFC 7807
    reuse_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_1})
    assert reuse_res.status_code == 401
    assert reuse_res.headers["content-type"].startswith("application/problem+json")
    prob = reuse_res.json()
    for field in ("type", "title", "status", "detail", "instance", "trace_id"):
        assert field in prob

    # Logout revoca refresh_2
    logout_res = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_2},
        headers={"Authorization": f"Bearer {access_2}"},
    )
    assert logout_res.status_code == 200

    post_logout_ref = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_2})
    assert post_logout_ref.status_code == 401


def test_rfc7807_problem_details_and_rbac_guards(api_client):
    client, _ = api_client

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "estudiante@unicesar.edu.co", "demo_mode": True},
    ).json()
    student_headers = {"Authorization": f"Bearer {student_login['access_token']}"}

    # 1. Error de validación de dominio (< 15 chars) -> 422 ProblemDetails
    short_res = client.post(
        "/api/v1/tickets",
        headers=student_headers,
        json={
            "title": "Falla en aula",
            "description": "Muy corto",
            "service_name": "Conectividad y Redes Wi-Fi",
            "sede": "Sede Sabanas (Valledupar)",
            "location": "Bloque B",
            "urgency": "Alta",
        },
    )
    assert short_res.status_code == 422
    assert short_res.headers["content-type"].startswith("application/problem+json")
    assert "trace_id" in short_res.json()

    # 2. RBAC 403: usuario no puede reasignar tickets ni activar modelos ML
    rbac_res = client.post(
        "/api/v1/tickets/1/reassign",
        headers=student_headers,
        json={"new_tech_id": 4, "reason": "Intento no autorizado"},
    )
    assert rbac_res.status_code == 403
    assert rbac_res.headers["content-type"].startswith("application/problem+json")

    ml_rbac = client.post(
        "/api/v1/analytics/ml/activate",
        headers=student_headers,
        json={"model_id": "linear_svc"},
    )
    assert ml_rbac.status_code == 403

    # 3. Simulación RNF-06 -> 503 ProblemDetails controlado
    rnf06_res = client.post(
        "/api/v1/tickets/classify-preview",
        headers=student_headers,
        json={"title": "Sin internet", "description": "Sin red en Bloque B", "simulate_failure": True},
    )
    assert rnf06_res.status_code == 503
    assert rnf06_res.headers["content-type"].startswith("application/problem+json")

    # 4. Transición ITIL inválida -> 409 ProblemDetails
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@unicesar.edu.co", "demo_mode": True},
    ).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    bad_trans = client.post(
        "/api/v1/tickets/2/transition",  # ticket 2 está en 'Asignado'
        headers=admin_headers,
        json={"new_status": "Cerrado"},
    )
    assert bad_trans.status_code == 409
    assert bad_trans.headers["content-type"].startswith("application/problem+json")


def test_realtime_websocket_chat_and_readonly_on_closed(api_client):
    client, _ = api_client

    student_auth = client.post(
        "/api/v1/auth/login",
        json={"email": "estudiante@unicesar.edu.co", "demo_mode": True},
    ).json()
    student_headers = {"Authorization": f"Bearer {student_auth['access_token']}"}

    # Crear ticket real para probar sala WebSocket entre estudiante y técnico asignado
    created = client.post(
        "/api/v1/tickets",
        headers=student_headers,
        json={
            "title": "Falla en acceso Eduroam laboratorio",
            "description": "No autentica en la red inalámbrica Eduroam del laboratorio B.",
            "service_name": "Conectividad y Redes Wi-Fi",
            "sede": "Sede Sabanas (Valledupar)",
            "location": "Bloque B",
            "urgency": "Alta",
        },
    ).json()
    ticket_id = created["id"]
    tech_email = created["assigned_tech_email"]

    tech_auth = client.post(
        "/api/v1/auth/login",
        json={"email": tech_email, "demo_mode": True},
    ).json()

    # Conexión WebSocket sin token debe ser rechazada
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/tickets/{ticket_id}"):
            pass

    # Sala en vivo con 2 clientes conectados simultáneamente (estudiante + técnico)
    with client.websocket_connect(
        f"/api/v1/ws/tickets/{ticket_id}?token={student_auth['access_token']}"
    ) as ws_student:
        ready_student = ws_student.receive_json()
        assert ready_student["type"] in ("ready", "presence")

        with client.websocket_connect(
            f"/api/v1/ws/tickets/{ticket_id}?token={tech_auth['access_token']}"
        ) as ws_tech:
            # Consumir notificaciones iniciales de conexión/presencia en tech
            for _ in range(3):
                frame = ws_tech.receive_json()
                if frame["type"] == "ready":
                    assert frame["read_only"] is False
                    break

            ws_student.send_json({"content": "Hola ingeniero, sigo sin conexión en el bloque B."})

            # Técnico recibe el mensaje en tiempo real vía WebSocket
            received_by_tech = None
            for _ in range(4):
                frame = ws_tech.receive_json()
                if frame["type"] == "message":
                    received_by_tech = frame["message"]
                    break
            assert received_by_tech is not None
            assert "sigo sin conexión" in received_by_tech["message"]

    # Transicionar ticket a En atención -> Resuelto -> Cerrado con CSAT
    tech_headers = {"Authorization": f"Bearer {tech_auth['access_token']}"}
    assert client.post(
        f"/api/v1/tickets/{ticket_id}/transition",
        headers=tech_headers,
        json={"new_status": "En atención"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/tickets/{ticket_id}/transition",
        headers=tech_headers,
        json={
            "new_status": "Resuelto",
            "diagnosis": "Credencial bloqueada en servidor RADIUS Eduroam",
            "solution": "Se sincronizó el usuario institucional con el controlador RADIUS y validó conexión.",
            "closing_category": "Solución remota / configuración",
        },
    ).status_code == 200
    assert client.post(
        f"/api/v1/tickets/{ticket_id}/rate",
        headers=student_headers,
        json={"csat_score": 5, "csat_comment": "Excelente soporte en vivo", "confirm_close": True},
    ).status_code == 200

    # Con el ticket Cerrado, el WebSocket debe bloquear envío de mensajes (modo solo lectura)
    with client.websocket_connect(
        f"/api/v1/ws/tickets/{ticket_id}?token={student_auth['access_token']}"
    ) as ws_closed:
        for _ in range(3):
            f = ws_closed.receive_json()
            if f["type"] == "ready":
                assert f["read_only"] is True
                break
        ws_closed.send_json({"content": "Intento de escritura tras cierre"})
        err_frame = ws_closed.receive_json()
        assert err_frame["type"] == "error"
        assert err_frame["status"] == 409


def test_web_views_public_lookup_and_floating_ai_endpoints(api_client):
    client, _ = api_client

    # Vistas HTML Tailwind v4 + Widget Flotante
    for route in ("/", "/login", "/dashboard"):
        res = client.get(route)
        assert res.status_code == 200
        assert "@tailwindcss/browser@4" in res.text
        assert "floating-ai-root" in res.text

    # Consulta pública sin PII ni correos de terceros
    pub = client.get("/api/v1/tickets/public/MS-2026-000001")
    assert pub.status_code == 200
    pub_json = pub.json()
    assert "requester_email" not in pub_json
    assert isinstance(pub_json["timeline"], list)
    for ev in pub_json["timeline"]:
        assert "@" not in (ev.get("comment") or "")

    # Agente IA flotante (público + autenticado + simulación RNF-06)
    chat_pub = client.post("/api/v1/agent/chat", json={"message": "Consultar MS-2026-000001"})
    assert chat_pub.status_code == 200
    assert chat_pub.json()["tool_invoked"] == "check_ticket"

    chat_rnf06 = client.post(
        "/api/v1/agent/chat",
        json={"message": "No funciona el wifi", "simulate_failure": True},
    )
    assert chat_rnf06.status_code == 200
    assert chat_rnf06.json()["status"] == "ai_unavailable"


def test_demo_mode_disabled_by_default_blocks_quick_login(api_client, monkeypatch):
    """Cuando DEMO_MODE está apagado (por defecto en producción), bloquea accesos demo."""
    client, _ = api_client
    monkeypatch.delenv("DEMO_MODE", raising=False)

    demo_list = client.get("/api/v1/auth/demo-users")
    assert demo_list.status_code == 200
    assert demo_list.json() == {"demo_mode": False, "users": []}

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@unicesar.edu.co", "demo_mode": True},
    )
    assert blocked.status_code == 403
    assert blocked.headers["content-type"].startswith("application/problem+json")
