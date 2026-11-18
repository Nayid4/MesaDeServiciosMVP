"""Pruebas de arquitectura modular estricta (<=300 líneas), CQRSBus, paginación SQL, perfil y recuperación."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.users import PASSWORD_RESET_OUTBOX
from src.infrastructure.composition import get_cqrs_bus, reset_runtime_dependencies
from src.infrastructure.persistence.database import dispose_engines, init_database
from src.main import create_app


@pytest.fixture
def modular_client(tmp_path, monkeypatch):
    db_file = tmp_path / "modular_cqrs.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.setenv("DEMO_MODE", "true")
    PASSWORD_RESET_OUTBOX.clear()
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)

    app = create_app()
    with TestClient(app) as client:
        yield client

    PASSWORD_RESET_OUTBOX.clear()
    dispose_engines()
    reset_runtime_dependencies()


def _login_demo(client: TestClient, email: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "demo_mode": True})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_strict_modular_line_ceiling_across_src():
    """Ningún archivo de código fuente en src/ (.py, .js, .html, .css) puede superar 300 líneas."""
    src_root = ROOT_DIR / "src"
    oversized: list[tuple[int, str]] = []
    for path in sorted(src_root.rglob("*")):
        if "__pycache__" in path.parts or not path.is_file():
            continue
        if path.suffix in {".py", ".js", ".html", ".css"}:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > 300:
                oversized.append((line_count, str(path.relative_to(ROOT_DIR))))
    assert not oversized, f"Archivos > 300 líneas detectados: {oversized}"


def test_cqrs_bus_and_sql_pagination_endpoints(modular_client: TestClient):
    """Verifica bus CQRS y paginación SQL real (LIMIT/OFFSET + COUNT) en usuarios, tickets y KB."""
    bus = get_cqrs_bus()
    assert bus is get_cqrs_bus()

    admin_hdrs = _login_demo(modular_client, "admin@unicesar.edu.co")

    # Paginación SQL de usuarios
    p1 = modular_client.get("/api/v1/users?page=1&page_size=2", headers=admin_hdrs)
    p2 = modular_client.get("/api/v1/users?page=2&page_size=2", headers=admin_hdrs)
    assert p1.status_code == 200 and p2.status_code == 200
    d1, d2 = p1.json(), p2.json()
    assert d1["page"] == 1 and d1["page_size"] == 2
    assert d1["total"] >= 4 and d1["has_next"] is True and d1["has_prev"] is False
    assert d2["page"] == 2 and d2["has_prev"] is True
    ids1 = {u["id"] for u in d1["items"]}
    ids2 = {u["id"] for u in d2["items"]}
    assert len(ids1) == 2 and ids1.isdisjoint(ids2)

    # Paginación SQL de tickets
    tp1 = modular_client.get("/api/v1/tickets?page=1&page_size=2", headers=admin_hdrs)
    tp2 = modular_client.get("/api/v1/tickets?page=2&page_size=2", headers=admin_hdrs)
    assert tp1.status_code == 200 and tp2.status_code == 200
    td1, td2 = tp1.json(), tp2.json()
    assert td1["total"] >= 3 and td1["has_next"] is True
    tids1 = {t["id"] for t in td1["tickets"]}
    tids2 = {t["id"] for t in td2["tickets"]}
    assert tids1 and tids1.isdisjoint(tids2)

    # Paginación SQL de Base de Conocimiento
    kb1 = modular_client.get("/api/v1/analytics/kb?page=1&page_size=3", headers=admin_hdrs)
    kb2 = modular_client.get("/api/v1/analytics/kb?page=2&page_size=3", headers=admin_hdrs)
    assert kb1.status_code == 200 and kb2.status_code == 200
    kd1, kd2 = kb1.json(), kb2.json()
    assert kd1["total"] >= 4 and kd1["pages"] >= 2
    kids1 = {a["id"] for a in kd1["articles"]}
    kids2 = {a["id"] for a in kd2["articles"]}
    assert len(kids1) == 3 and kids1.isdisjoint(kids2)


def test_profile_update_password_change_and_reset_flow(modular_client: TestClient):
    """Valida actualización de perfil, cambio de contraseña y flujo de reset con token de 1 solo uso."""
    reg = modular_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Laura Pérez",
            "email": "laura.perez@unicesar.edu.co",
            "password": "Password1!",
            "sede": "Sede Sabanas (Valledupar)",
            "privacy_accepted": True,
        },
    )
    assert reg.status_code == 201, reg.text
    hdrs = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    me = modular_client.get("/api/v1/users/me", headers=hdrs)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "laura.perez@unicesar.edu.co"

    upd = modular_client.patch(
        "/api/v1/users/me/profile",
        json={"full_name": "Laura P. Morales", "sede": "Sede Hurtado (Valledupar)"},
        headers=hdrs,
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["user"]["full_name"] == "Laura P. Morales"
    assert upd.json()["user"]["sede"] == "Sede Hurtado (Valledupar)"

    bad_pw = modular_client.post(
        "/api/v1/users/me/password",
        json={"current_password": "WrongPassword9!", "new_password": "NewPassword2!"},
        headers=hdrs,
    )
    assert bad_pw.status_code == 401

    good_pw = modular_client.post(
        "/api/v1/users/me/password",
        json={"current_password": "Password1!", "new_password": "NewPassword2!"},
        headers=hdrs,
    )
    assert good_pw.status_code == 200
    assert modular_client.post(
        "/api/v1/auth/login",
        json={"email": "laura.perez@unicesar.edu.co", "password": "NewPassword2!"},
    ).status_code == 200

    # Solicitud y confirmación de restablecimiento de contraseña
    req_reset = modular_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "laura.perez@unicesar.edu.co"},
    )
    assert req_reset.status_code == 200
    assert "laura.perez@unicesar.edu.co" in PASSWORD_RESET_OUTBOX
    token = PASSWORD_RESET_OUTBOX["laura.perez@unicesar.edu.co"]["token"]

    conf_reset = modular_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "RecoveredPass3!"},
    )
    assert conf_reset.status_code == 200, conf_reset.text

    # El token es de un solo uso
    replay = modular_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "AnotherPass4!"},
    )
    assert replay.status_code == 401

    assert modular_client.post(
        "/api/v1/auth/login",
        json={"email": "laura.perez@unicesar.edu.co", "password": "RecoveredPass3!"},
    ).status_code == 200


def test_admin_user_management_and_modular_html_routes(modular_client: TestClient):
    """Valida RBAC de gestión de usuarios, protección de último admin y vistas HTML parciales."""
    user_hdrs = _login_demo(modular_client, "estudiante@unicesar.edu.co")
    admin_hdrs = _login_demo(modular_client, "admin@unicesar.edu.co")

    users_data = modular_client.get("/api/v1/users?page=1&page_size=20", headers=admin_hdrs).json()["items"]
    admin_user = next(u for u in users_data if u["email"] == "admin@unicesar.edu.co")
    target_user = next(u for u in users_data if u["email"] == "estudiante@unicesar.edu.co")

    assert modular_client.patch(
        f"/api/v1/users/{target_user['id']}", json={"sede": "Seccional Aguachica"}, headers=user_hdrs
    ).status_code == 403

    # Protección del último Administrador activo
    assert modular_client.patch(
        f"/api/v1/users/{admin_user['id']}", json={"is_active": False}, headers=admin_hdrs
    ).status_code == 409

    patched = modular_client.patch(
        f"/api/v1/users/{target_user['id']}", json={"sede": "Seccional Aguachica"}, headers=admin_hdrs
    )
    assert patched.status_code == 200
    assert patched.json()["user"]["sede"] == "Seccional Aguachica"

    # Todas las rutas HTML renderizan sin errores de Jinja2
    for route in ("/", "/login", "/dashboard", "/ticket-track/MS-RED-2026-000001", "/reset-password?token=demo123"):
        resp = modular_client.get(route)
        assert resp.status_code == 200, f"Falló ruta {route}: {resp.status_code}"

    login_html = modular_client.get("/login").text
    for expected in (
        "Servicios de apoyo para toda la comunidad universitaria.",
        'id="auth-view-login"',
        'id="auth-view-forgot"',
        'id="auth-view-register"',
        'id="login-password-toggle"',
        'id="login-remember-email"',
        'id="reg-password-toggle"',
        'id="reg-strength-fill"',
    ):
        assert expected in login_html

    reset_html = modular_client.get("/reset-password?token=demo123").text
    for expected in ('id="reset-new-toggle"', 'id="reset-confirm-toggle"', 'id="reset-strength-fill"'):
        assert expected in reset_html


def test_prod_mode_seeds_missing_base_users_and_allows_password_login(tmp_path, monkeypatch):
    """Con DEMO_MODE apagado (prod), se precargan cuentas base por correo y acceden con contraseña."""
    from src.infrastructure.persistence.database import get_session_factory
    from src.infrastructure.persistence.models import UserORM
    from src.infrastructure.security.password_hasher import hash_password

    db_file = tmp_path / "prod_seed.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.delenv("DEMO_MODE", raising=False)
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=False)

    # Simula una BD donde ya existía un usuario registrado antes de precargar cuentas base
    with get_session_factory(db_file)() as session:
        session.add(
            UserORM(
                email="previo@unicesar.edu.co",
                full_name="Usuario Previo",
                password_hash=hash_password("Password1!"),
                role="usuario",
                sede="Sede Sabanas (Valledupar)",
                is_active=True,
                privacy_accepted=True,
                created_at="2026-11-17T10:00:00-05:00",
            )
        )
        session.commit()

    app = create_app()
    with TestClient(app) as client:
        for email, pwd in (
            ("previo@unicesar.edu.co", "Password1!"),
            ("admin@unicesar.edu.co", "Admin2026*"),
            ("coordinador@unicesar.edu.co", "Coord2026*"),
            ("director@unicesar.edu.co", "Director2026*"),
            ("tecnico1@unicesar.edu.co", "Tecnico2026*"),
            ("estudiante@unicesar.edu.co", "User2026*"),
        ):
            ok = client.post("/api/v1/auth/login", json={"email": email, "password": pwd, "demo_mode": False})
            assert ok.status_code == 200, f"Falló login prod para {email}: {ok.text}"

        assert (
            client.post("/api/v1/auth/login", json={"email": "admin@unicesar.edu.co", "demo_mode": True}).status_code
            == 403
        )

    dispose_engines()
    reset_runtime_dependencies()
