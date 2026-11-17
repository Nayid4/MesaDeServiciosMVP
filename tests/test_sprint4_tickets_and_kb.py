"""Pruebas obligatorias de Sprint 4: Gestión de Tickets UI/API y Base de Conocimiento (42 artículos, CRUD, versiones y RAG)."""

from __future__ import annotations

from datetime import timedelta
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cleaning import clean_tickets_dataset
from src.domain.rules import KB_CATEGORIES, now_bogota
from src.infrastructure.composition import reset_runtime_dependencies
from src.infrastructure.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml_pipeline import train_and_evaluate_models
from src.infrastructure.persistence.database import dispose_engines, get_engine, init_database
from src.main import create_app


@pytest.fixture(scope="module")
def sprint4_ml_registry(tmp_path_factory) -> Path:
    ml_dir = tmp_path_factory.mktemp("sprint4_ml")
    raw_file = ml_dir / "raw.csv"
    clean_file = ml_dir / "clean.csv"
    excl_file = ml_dir / "excl.csv"
    models_dir = ml_dir / "models"
    generate_synthetic_dataset(n_rows=600, output_path=raw_file, seed=19)
    clean_tickets_dataset(raw_file, clean_file, excl_file)
    train_and_evaluate_models(clean_csv_path=clean_file, models_dir=models_dir)
    return models_dir / "model_registry.json"


@pytest.fixture
def sprint4_client(tmp_path, monkeypatch, sprint4_ml_registry):
    db_file = tmp_path / "sprint4_tickets_kb.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setattr("src.infrastructure.composition.DEFAULT_REGISTRY_PATH", sprint4_ml_registry)
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
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_seed_contains_at_least_40_demo_kb_articles_across_all_categories(sprint4_client):
    """Verifica >= 40 artículos demostrativos marcados con is_demo y [CONFIRMAR] cubriendo las 9 categorías."""
    client, _ = sprint4_client
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")

    res = client.get("/api/v1/analytics/kb", headers=coord_headers)
    assert res.status_code == 200, res.text
    articles = res.json()["articles"]
    assert len(articles) >= 40

    found_categories = {a["category_topic"] for a in articles}
    assert set(KB_CATEGORIES).issubset(found_categories)

    for art in articles:
        assert bool(art.get("is_demo")) is True
        assert art.get("service_name")
        assert art.get("symptoms")
        assert art.get("probable_cause")
        assert art.get("solution_steps")
        assert art.get("escalation_criteria")
        assert art.get("keywords")
        assert art.get("visibility") in ("Pública", "Interna")
        assert int(art.get("version", 0)) >= 1
        assert art.get("author_email")
        assert art.get("reviewer_email")
        combined_text = f"{art['title']} {art['probable_cause']} {art['solution_steps']} {art['escalation_criteria']}"
        assert "[CONFIRMAR]" in combined_text or "[DEMO]" in combined_text


def test_kb_crud_state_transitions_rbac_versions_and_html_sanitization(sprint4_client):
    """Prueba CRUD KB, saneado XSS de HTML, permisos técnico vs coordinador, observaciones y versiones."""
    client, _ = sprint4_client
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")

    # 1. Técnico crea artículo en Borrador con HTML malicioso -> saneado estricto en servidor
    create_res = client.post(
        "/api/v1/analytics/kb",
        headers=tech_headers,
        json={
            "code": "KB-099",
            "title": "[DEMO] Verificación de VLAN inalámbrica en laboratorio [CONFIRMAR]",
            "service_name": "Conectividad y Redes Wi-Fi",
            "category_topic": "Wi-Fi y Eduroam",
            "symptoms": "<script>alert('xss')</script>No obtiene IP en VLAN académica",
            "probable_cause": "<iframe src='https://evil.example'></iframe>Puerto truncado en switch",
            "solution_steps": "<img src=x onerror=alert(1)><strong>Paso 1 verificado</strong><p>Ejecutar ipconfig /renew</p>",
            "escalation_criteria": "Escalar a Redes si persiste más de 15 minutos [CONFIRMAR]",
            "keywords": "vlan wifi ipconfig switch laboratorio",
            "visibility": "Pública",
            "status": "Borrador",
        },
    )
    assert create_res.status_code == 201, create_res.text
    art = create_res.json()["article"]
    art_id = art["id"]
    assert art["status"] == "Borrador"
    assert art["version"] == 1
    assert "<script" not in art["symptoms"].lower()
    assert "alert(" not in art["symptoms"].lower()
    assert "<iframe" not in art["probable_cause"].lower()
    assert "onerror" not in art["solution_steps"].lower()
    assert "<img" not in art["solution_steps"].lower()
    assert "<strong>Paso 1 verificado</strong>" in art["solution_steps"]

    # Usuario final NO puede crear ni editar artículos KB (403)
    user_try = client.post(
        "/api/v1/analytics/kb",
        headers=student_headers,
        json={
            "title": "Intento estudiante",
            "service_name": "Conectividad y Redes Wi-Fi",
            "symptoms": "Síntoma de prueba",
            "solution_steps": "Pasos de prueba mayores a diez caracteres",
            "keywords": "test",
        },
    )
    assert user_try.status_code == 403
    assert user_try.headers["content-type"].startswith("application/problem+json")

    # 2. Técnico envía a revisión (v2)
    rev_res = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=tech_headers,
        json={"action": "enviar_revision"},
    )
    assert rev_res.status_code == 200, rev_res.text
    assert rev_res.json()["article"]["status"] == "En revisión"
    assert rev_res.json()["article"]["version"] == 2

    # 3. Técnico intenta publicar directamente -> 403 Forbidden RFC 7807
    tech_pub = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=tech_headers,
        json={"action": "publicar"},
    )
    assert tech_pub.status_code == 403
    assert tech_pub.headers["content-type"].startswith("application/problem+json")

    # 4. Coordinador intenta devolver sin observaciones -> 422 ProblemDetails
    bad_return = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=coord_headers,
        json={"action": "devolver", "review_notes": ""},
    )
    assert bad_return.status_code == 422
    assert bad_return.headers["content-type"].startswith("application/problem+json")

    # 5. Coordinador devuelve con observaciones obligatorias -> Borrador (v3) y notificación al técnico
    ok_return = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=coord_headers,
        json={"action": "devolver", "review_notes": "Completar comando de verificación de puerta de enlace"},
    )
    assert ok_return.status_code == 200, ok_return.text
    returned_art = ok_return.json()["article"]
    assert returned_art["status"] == "Borrador"
    assert returned_art["version"] == 3
    assert "puerta de enlace" in returned_art["review_notes"]

    me_tech = client.get("/api/v1/auth/me", headers=tech_headers).json()
    assert any("KB-099" in n["title"] and "devuelto" in n["title"].lower() for n in me_tech["notifications"])

    # 6. Técnico edita mediante PUT (pasa a En revisión, v4)
    edit_res = client.put(
        f"/api/v1/analytics/kb/{art_id}",
        headers=tech_headers,
        json={
            "code": "KB-099",
            "title": "[DEMO] Verificación de VLAN inalámbrica en laboratorio [CONFIRMAR]",
            "service_name": "Conectividad y Redes Wi-Fi",
            "category_topic": "Wi-Fi y Eduroam",
            "symptoms": "No obtiene IP en VLAN académica",
            "probable_cause": "Puerto truncado o rango DHCP agotado en switch [CONFIRMAR]",
            "solution_steps": "<strong>Paso 1 verificado</strong><p>Ejecutar ipconfig /release, ipconfig /renew y ping a puerta de enlace.</p>",
            "escalation_criteria": "Escalar a Redes si persiste más de 15 minutos [CONFIRMAR]",
            "keywords": "vlan wifi ipconfig switch laboratorio",
            "visibility": "Pública",
            "status": "Publicado",  # Aunque intente Publicado, el rol técnico fuerza En revisión
            "change_summary": "Agregado comando de puerta de enlace tras revisión",
        },
    )
    assert edit_res.status_code == 200, edit_res.text
    assert edit_res.json()["article"]["status"] == "En revisión"
    assert edit_res.json()["article"]["version"] == 4

    # 7. Coordinador publica (v5)
    pub_res = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=coord_headers,
        json={"action": "publicar"},
    )
    assert pub_res.status_code == 200, pub_res.text
    pub_art = pub_res.json()["article"]
    assert pub_art["status"] == "Publicado"
    assert pub_art["version"] == 5
    assert pub_art["reviewer_email"] == "coordinador@unicesar.edu.co"

    # 8. Historial de versiones, comparación v1 vs v4 y restauración v1 -> v6
    ver_res = client.get(f"/api/v1/analytics/kb/{art_id}/versions", headers=tech_headers)
    assert ver_res.status_code == 200
    versions = ver_res.json()["versions"]
    assert len(versions) == 5

    cmp_res = client.get(
        f"/api/v1/analytics/kb/{art_id}/versions/compare?from_version=1&to_version=4",
        headers=coord_headers,
    )
    assert cmp_res.status_code == 200, cmp_res.text
    diffs = cmp_res.json()["differences"]
    assert any(d["field"] == "solution_steps" for d in diffs)

    restore_res = client.post(
        f"/api/v1/analytics/kb/{art_id}/versions/1/restore",
        headers=coord_headers,
    )
    assert restore_res.status_code == 200, restore_res.text
    restored = restore_res.json()["article"]
    assert restored["version"] == 6
    assert "Ejecutar ipconfig /renew</p>" in restored["solution_steps"]


def test_retired_kb_article_disappears_from_public_and_ai_assistant(sprint4_client):
    """Un artículo Publicado/Pública alimenta al asistente IA; al pasar a Retirado deja de aparecer."""
    client, _ = sprint4_client
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")

    unique_term = "kerberos forticlient upc99x"
    create_res = client.post(
        "/api/v1/analytics/kb",
        headers=coord_headers,
        json={
            "code": "KB-088",
            "title": f"[DEMO] Error de token {unique_term} [CONFIRMAR]",
            "service_name": "Conectividad y Redes Wi-Fi",
            "category_topic": "VPN",
            "symptoms": f"Falla de autenticación con token {unique_term} al abrir túnel",
            "probable_cause": "Desincronización de token horario [CONFIRMAR]",
            "solution_steps": f"1. Verificar reloj NTP y renovar token {unique_term} en portal [CONFIRMAR].",
            "escalation_criteria": "Escalar a Redes si persiste.",
            "keywords": f"token {unique_term} vpn",
            "visibility": "Pública",
            "status": "Publicado",
        },
    )
    assert create_res.status_code == 201
    art_id = create_res.json()["article"]["id"]

    # Estando Publicado y Pública, aparece en consulta pública y en el asistente IA
    pub_list_before = client.get(f"/api/v1/analytics/kb?q={unique_term}").json()["articles"]
    assert any(a["code"] == "KB-088" for a in pub_list_before)

    ai_before = client.post(
        "/api/v1/agent/chat",
        json={"message": f"Tengo error con token {unique_term}"},
    )
    assert ai_before.status_code == 200, ai_before.text
    assert ai_before.json()["tool_invoked"] == "search_kb"
    assert any(a["code"] == "KB-088" for a in ai_before.json()["matched_articles"])

    # Técnico NO puede retirar artículo (403)
    tech_headers = _auth_header(client, "tecnico1@unicesar.edu.co")
    tech_ret = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=tech_headers,
        json={"action": "retirar"},
    )
    assert tech_ret.status_code == 403

    # Coordinador retira el artículo -> desaparece del catálogo público y del asistente IA
    ret_res = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=coord_headers,
        json={"action": "retirar"},
    )
    assert ret_res.status_code == 200
    assert ret_res.json()["article"]["status"] == "Retirado"

    pub_list_after = client.get(f"/api/v1/analytics/kb?q={unique_term}").json()["articles"]
    assert all(a["code"] != "KB-088" for a in pub_list_after)

    ai_after = client.post(
        "/api/v1/agent/chat",
        json={"message": f"Tengo error con token {unique_term}"},
    )
    assert ai_after.status_code == 200
    assert all(a["code"] != "KB-088" for a in ai_after.json().get("matched_articles", []))

    # Coordinador restaura a Publicado -> vuelve al asistente
    rest_res = client.post(
        f"/api/v1/analytics/kb/{art_id}/transition",
        headers=coord_headers,
        json={"action": "restaurar"},
    )
    assert rest_res.status_code == 200
    assert rest_res.json()["article"]["status"] == "Publicado"

    ai_restored = client.post(
        "/api/v1/agent/chat",
        json={"message": f"Tengo error con token {unique_term}"},
    )
    assert ai_restored.status_code == 200
    assert any(a["code"] == "KB-088" for a in ai_restored.json()["matched_articles"])


def test_full_ticket_lifecycle_priority_adjust_reopen_3_days_and_csat_rules(sprint4_client):
    """Prueba flujo completo: pre-sugerencia KB, paginación/carga, ajuste prioridad, ciclo ITIL, reapertura 3 días hábiles y CSAT."""
    client, db_path = sprint4_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")
    coord_headers = _auth_header(client, "coordinador@unicesar.edu.co")

    # 1. Pre-clasificación devuelve sugerencias de KB antes de radicar
    preview_res = client.post(
        "/api/v1/tickets/classify-preview",
        headers=student_headers,
        json={
            "title": "No conecta Wi-Fi Eduroam en portátil Windows 11",
            "description": "Aparece no se puede conectar a esta red al intentar usar Eduroam en bloque B.",
        },
    )
    assert preview_res.status_code == 200, preview_res.text
    assert len(preview_res.json().get("suggested_articles", [])) >= 1

    # 2. Registro por usuario
    create_res = client.post(
        "/api/v1/tickets",
        headers=student_headers,
        json={
            "title": "Sin conectividad Eduroam Windows 11 aula 202",
            "description": "El equipo muestra error de certificado EAP-PEAP en Eduroam durante clase.",
            "service_name": "Conectividad y Redes Wi-Fi",
            "sede": "Sede Sabanas (Valledupar)",
            "location": "Bloque B",
            "urgency": "Baja",
        },
    )
    assert create_res.status_code == 201, create_res.text
    ticket = create_res.json()
    tid = ticket["id"]
    assert ticket["status"] == "Asignado"

    # 3. Bandeja paginada, ordenada y carga de técnicos para coordinador
    list_res = client.get(
        "/api/v1/tickets?page=1&page_size=5&sort_by=priority_asc_deadline_asc",
        headers=coord_headers,
    )
    assert list_res.status_code == 200
    list_json = list_res.json()
    assert len(list_json["tickets"]) <= 5
    assert list_json["total"] >= 1
    assert len(list_json["technician_loads"]) >= 1

    # 4. Coordinador ajusta prioridad con justificación OR-03 (Alto x Alta -> P1 Crítica)
    bad_prio = client.post(
        f"/api/v1/tickets/{tid}/priority",
        headers=coord_headers,
        json={"impact": "Alto", "urgency": "Alta", "justification": "corta"},
    )
    assert bad_prio.status_code == 422

    prio_res = client.post(
        f"/api/v1/tickets/{tid}/priority",
        headers=coord_headers,
        json={
            "impact": "Alto",
            "urgency": "Alta",
            "justification": "Afecta laboratorio completo durante evaluación institucional.",
            "version": ticket["version"],
        },
    )
    assert prio_res.status_code == 200, prio_res.text
    ticket = prio_res.json()
    assert ticket["priority"] == "P1 Crítica"
    assert "evaluación institucional" in ticket["priority_justification"]

    # 5. Coordinador reasigna con motivo
    detail_before = client.get(f"/api/v1/tickets/{tid}", headers=coord_headers).json()
    techs = detail_before["available_technicians"]
    assert all("open_tickets_count" in th for th in techs)
    alt_tech = next(th for th in techs if th["email"] != ticket["assigned_tech_email"])
    reassign_res = client.post(
        f"/api/v1/tickets/{tid}/reassign",
        headers=coord_headers,
        json={
            "new_tech_id": alt_tech["id"],
            "reason": "Balanceo de carga hacia técnico especialista disponible.",
            "version": ticket["version"],
        },
    )
    assert reassign_res.status_code == 200, reassign_res.text
    ticket = reassign_res.json()
    assert ticket["assigned_tech_email"] == alt_tech["email"]

    # 6. Técnico inicia atención -> En espera -> En atención -> Resuelto
    tech_headers = _auth_header(client, alt_tech["email"])
    t1 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={"new_status": "En atención", "version": ticket["version"]},
    )
    assert t1.status_code == 200

    t2 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={
            "new_status": "En espera",
            "comment": "A la espera de verificación presencial del docente en salón 202.",
            "version": t1.json()["version"],
        },
    )
    assert t2.status_code == 200

    t3 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={"new_status": "En atención", "version": t2.json()["version"]},
    )
    assert t3.status_code == 200

    t4 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={
            "new_status": "Resuelto",
            "diagnosis": "Perfil inalámbrico heredado sin validación de servidor RADIUS vigente.",
            "solution": "Se eliminó perfil previo y se reconfiguró EAP-PEAP con certificado institucional.",
            "closing_category": "Solución remota / configuración",
            "version": t3.json()["version"],
        },
    )
    assert t4.status_code == 200
    resolved_ticket = t4.json()
    assert resolved_ticket["status"] == "Resuelto"

    # Técnico propone artículo KB vinculando el ticket resuelto
    kb_from_ticket = client.post(
        "/api/v1/analytics/kb",
        headers=tech_headers,
        json={
            "code": "KB-095",
            "title": "[DEMO] Solución EAP-PEAP desde ticket resuelto [CONFIRMAR]",
            "service_name": resolved_ticket["service_name"],
            "category_topic": "Wi-Fi y Eduroam",
            "symptoms": resolved_ticket["description"],
            "probable_cause": resolved_ticket["diagnosis"],
            "solution_steps": resolved_ticket["solution"],
            "escalation_criteria": "Escalar a Redes si persiste [CONFIRMAR].",
            "keywords": "eduroam eap peap radius",
            "visibility": "Pública",
            "status": "En revisión",
            "source_ticket_id": tid,
        },
    )
    assert kb_from_ticket.status_code == 201

    # 7. Usuario reabre dentro de los 3 días hábiles -> permitido; luego técnico vuelve a resolver
    reopen_ok = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=student_headers,
        json={
            "new_status": "Reabierto",
            "comment": "Al reiniciar el portátil volvió a solicitar credenciales erróneas.",
            "version": resolved_ticket["version"],
        },
    )
    assert reopen_ok.status_code == 200, reopen_ok.text
    assert reopen_ok.json()["status"] == "Reabierto"

    t5 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={"new_status": "En atención", "version": reopen_ok.json()["version"]},
    )
    assert t5.status_code == 200
    t6 = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=tech_headers,
        json={
            "new_status": "Resuelto",
            "diagnosis": "Credencial almacenada en Administrador de credenciales de Windows.",
            "solution": "Se depuraron credenciales cacheadas en Windows y se validó persistencia tras reinicio.",
            "closing_category": "Solución remota / configuración",
            "version": t5.json()["version"],
        },
    )
    assert t6.status_code == 200

    # Simular que vencieron los 3 días hábiles (10 días atrás) -> reapertura rechazada (409 ProblemDetails)
    engine = get_engine(db_path)
    expired_iso = (now_bogota() - timedelta(days=10)).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE tickets SET resolved_at = :ts WHERE id = :tid"),
            {"ts": expired_iso, "tid": tid},
        )
    reopen_expired = client.post(
        f"/api/v1/tickets/{tid}/transition",
        headers=student_headers,
        json={
            "new_status": "Reabierto",
            "comment": "Intento fuera de plazo de 3 días hábiles.",
        },
    )
    assert reopen_expired.status_code == 409
    assert reopen_expired.headers["content-type"].startswith("application/problem+json")
    assert "3 días hábiles" in reopen_expired.json()["detail"]

    # 8. Calificación 1 o 2 estrellas exige comentario obligatorio
    low_csat_no_comment = client.post(
        f"/api/v1/tickets/{tid}/rate",
        headers=student_headers,
        json={"csat_score": 2, "csat_comment": "", "confirm_close": True},
    )
    assert low_csat_no_comment.status_code == 422
    assert low_csat_no_comment.headers["content-type"].startswith("application/problem+json")

    low_csat_ok = client.post(
        f"/api/v1/tickets/{tid}/rate",
        headers=student_headers,
        json={
            "csat_score": 2,
            "csat_comment": "Tomó dos visitas completar el ajuste en el equipo.",
            "confirm_close": True,
        },
    )
    assert low_csat_ok.status_code == 200, low_csat_ok.text
    closed = low_csat_ok.json()
    assert closed["status"] == "Cerrado"
    assert closed["csat_score"] == 2
    assert closed["closed_at"] is not None


def test_notification_preferences_and_dashboard_sprint4_ui_elements(sprint4_client):
    """Verifica preferencias de notificaciones en backend y secciones Sprint 4 en dashboard.html."""
    client, _ = sprint4_client
    student_headers = _auth_header(client, "estudiante@unicesar.edu.co")

    prefs_res = client.get("/api/v1/auth/notifications/preferences", headers=student_headers)
    assert prefs_res.status_code == 200
    assert prefs_res.json()["preferences"]["notify_in_app"] is True

    upd = client.put(
        "/api/v1/auth/notifications/preferences",
        headers=student_headers,
        json={
            "notify_in_app": False,
            "notify_email_sim": True,
            "notify_ticket_updates": False,
            "notify_chat_messages": False,
            "notify_sla_alerts": True,
        },
    )
    assert upd.status_code == 200
    assert upd.json()["preferences"]["notify_in_app"] is False

    dash_html = client.get("/dashboard").text
    for expected in (
        'id="tickets-saved-views"',
        'id="coordinator-workload-panel"',
        'id="tickets-pagination"',
        'id="detail-mobile-tabs"',
        'id="ct-kb-suggestions"',
        'id="ct-attachments-input"',
        'id="ct-upload-progress-wrap"',
        'id="kb-inspector-panel"',
        'id="notif-prefs-panel"',
    ):
        assert expected in dash_html
