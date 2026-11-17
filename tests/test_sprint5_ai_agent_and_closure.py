"""Pruebas obligatorias de Sprint 5: Agente IA (regresión Sprint 0, umbral 0.60, multiturno, 105 frases y cierre)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cleaning import clean_tickets_dataset
from src.infrastructure.composition import get_ai_engine, reset_runtime_dependencies, uow_factory
from src.infrastructure.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml.agent_evaluator import EVALUATION_DATASET_105, run_agent_evaluation
from src.infrastructure.ml.ai_engine import (
    extract_explicit_ticket_entities,
    scrub_pii_for_model,
)
from src.infrastructure.ml.model_trainer import DEFAULT_REGISTRY_PATH, train_and_evaluate_models
from src.infrastructure.persistence.database import dispose_engines, init_database
from src.main import create_app


@pytest.fixture(scope="module")
def sprint5_ml_registry(tmp_path_factory) -> Path:
    if DEFAULT_REGISTRY_PATH.is_file():
        return DEFAULT_REGISTRY_PATH
    ml_dir = tmp_path_factory.mktemp("sprint5_ml")
    raw_file = ml_dir / "raw.csv"
    clean_file = ml_dir / "clean.csv"
    excl_file = ml_dir / "excl.csv"
    models_dir = ml_dir / "models"
    generate_synthetic_dataset(n_rows=800, output_path=raw_file, seed=42)
    clean_tickets_dataset(raw_file, clean_file, excl_file)
    train_and_evaluate_models(clean_csv_path=clean_file, models_dir=models_dir)
    return models_dir / "model_registry.json"


@pytest.fixture
def sprint5_client(tmp_path, monkeypatch, sprint5_ml_registry):
    db_file = tmp_path / "sprint5_closure.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setattr("src.infrastructure.composition.DEFAULT_REGISTRY_PATH", sprint5_ml_registry)
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)

    app = create_app()
    with TestClient(app) as client:
        yield client, str(db_file)

    dispose_engines()
    reset_runtime_dependencies()


def test_sprint0_regression_case_no_assumptions_and_correct_classification(sprint5_client):
    """La frase observada en Sprint 0 debe clasificar en Equipos de Cómputo sin asumir sede/lugar/urgencia."""
    client, _ = sprint5_client
    phrase = "tengo un problema con una computadora que no prende"

    entities = extract_explicit_ticket_entities(phrase)
    assert entities == {"sede": None, "location": None, "urgency": None}

    res = client.post(
        "/api/v1/agent/chat",
        json={"message": phrase, "failed_attempts": 1},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["prediction"]["predicted_service"] == "Equipos de Cómputo e Impresoras"
    assert data["prediction"]["confidence"] >= 0.60
    assert data["status"] == "needs_missing_fields"
    assert data["draft_card"] is None
    assert data["missing_fields"] == ["sede", "location", "urgency"]


def test_multiturn_conversation_single_intro_missing_fields_and_or03_draft(sprint5_client):
    """Verifica presentación única como IA, memoria multiturno, preguntas y prioridad determinista OR-03."""
    client, _ = sprint5_client
    history = []

    # Turno 1: saludo -> presentación única como IA
    r1 = client.post("/api/v1/agent/chat", json={"message": "Hola"}).json()
    assert r1["status"] == "conversational"
    assert "CASAGBI Agent" in r1["reply"]
    history.append({"role": "user", "content": "Hola"})
    history.append({"role": "assistant", "content": r1["reply"]})

    # Turno 2: falla sin ubicación ni urgencia -> no repite presentación y pregunta faltantes
    msg2 = "mi pc no prende y tiene pantalla negra"
    r2 = client.post(
        "/api/v1/agent/chat",
        json={"message": msg2, "history": history, "failed_attempts": 1},
    ).json()
    assert "CASAGBI Agent" not in r2["reply"]
    assert r2["status"] == "needs_missing_fields"
    assert r2["missing_fields"] == ["sede", "location", "urgency"]
    assert r2["draft_card"] is None
    history.append({"role": "user", "content": msg2})
    history.append({"role": "assistant", "content": r2["reply"]})

    # Turno 3: aporta sede, ubicación exacta y urgencia -> borrador editable con OR-03 (Bajo x Alta = P3 Media)
    msg3 = "estoy en Sede Hurtado, Laboratorios de Cómputo, y no puedo seguir trabajando"
    r3 = client.post(
        "/api/v1/agent/chat",
        json={"message": msg3, "history": history, "failed_attempts": 1},
    ).json()
    assert r3["status"] == "draft_ready"
    card = r3["draft_card"]
    assert card is not None
    assert card["editable"] is True
    assert card["service_name"] == "Equipos de Cómputo e Impresoras"
    assert card["sede"] == "Sede Hurtado (Valledupar)"
    assert card["location"] == "Laboratorios de Cómputo"
    assert card["impact"] == "Bajo"
    assert card["urgency"] == "Alta"
    assert card["priority"] == "P3 Media"
    assert card["sla_resolution_hours"] == 24.0

    # Turno 4: pregunta OR-03 / SLA y despedida natural
    r4 = client.post(
        "/api/v1/agent/chat",
        json={"message": "Cómo funciona la matriz OR-03?", "history": history},
    ).json()
    assert r4["status"] == "conversational"
    assert "OR-03" in r4["reply"]

    r5 = client.post(
        "/api/v1/agent/chat",
        json={"message": "Muchas gracias, hasta luego", "history": history},
    ).json()
    assert r5["status"] == "conversational"
    assert "Hablar con una persona" in r5["reply"]


def test_low_confidence_threshold_060_asks_clarification_and_lists_services(sprint5_client):
    """Frases ambiguas (< 0.60) deben pedir aclaración y ofrecer lista de servicios para elegir."""
    client, _ = sprint5_client
    res = client.post(
        "/api/v1/agent/chat",
        json={"message": "tengo un problema urgente ayúdenme", "failed_attempts": 1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"]["confidence"] < 0.60
    assert data["status"] == "needs_clarification"
    assert len(data["service_options"]) == 6
    assert data["draft_card"] is None


def test_public_agent_lookup_enforces_sprint2_security_rules(sprint5_client):
    """Consulta en agente sin sesión pide radicado y correo aplicando reglas anti-enumeración del Sprint 2."""
    client, _ = sprint5_client

    step1 = client.post(
        "/api/v1/agent/chat",
        json={"message": "Quiero consultar el radicado MS-RED-2026-000001"},
    ).json()
    assert step1["tool_invoked"] == "check_ticket"
    assert step1["status"] == "lookup_needs_email"
    assert "ticket_snapshot" not in step1

    # Correo incorrecto -> falla sin filtrar existencia
    wrong = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "MS-RED-2026-000001",
            "email": "otro@unicesar.edu.co",
        },
    ).json()
    assert wrong["status"] == "lookup_failed"
    assert "ticket_snapshot" not in wrong

    # Correo correcto del titular (docente@unicesar.edu.co) -> valida y enmascara correo
    ok = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "MS-RED-2026-000001",
            "email": "docente@unicesar.edu.co",
        },
    ).json()
    assert ok["status"] == "lookup_verified"
    assert ok["masked_email"] == "do***@unicesar.edu.co"
    assert ok["ticket_snapshot"]["ticket_number"] == "MS-RED-2026-000001"
    assert ok.get("ticket_guest_token")


def test_pii_scrubbed_and_ui_has_human_handoff_and_15s_timeout(sprint5_client):
    """Verifica redacción de PII antes del modelo y controles UI de 15 s / Hablar con una persona."""
    client, _ = sprint5_client

    cleaned, scrubbed = scrub_pii_for_model(
        "Me llamo Nayid Castellar, cédula 1065123456, correo nayid@gmail.com, mi pc no prende"
    )
    assert scrubbed is True
    assert "1065123456" not in cleaned
    assert "nayid@gmail.com" not in cleaned
    assert "Nayid Castellar" not in cleaned

    landing_html = client.get("/").text
    assert 'id="floating-ai-human-btn"' in landing_html
    assert "Hablar con una persona" in landing_html

    container_js = (
        ROOT_DIR / "src/presentation/web/static/js/features/ai_agent/ai_agent_container.js"
    ).read_text(encoding="utf-8")
    assert "AGENT_TIMEOUT_MS = 15000" in container_js
    assert "history: historySnapshot" in container_js


def test_evaluation_105_phrases_accuracy_and_abstention(sprint5_client):
    """Evalúa >= 100 frases (105) verificando alta precisión en dominio y correcta tasa de abstención."""
    _client, db_path = sprint5_client
    assert len(EVALUATION_DATASET_105) >= 100

    report = run_agent_evaluation(uow_factory(db_path), get_ai_engine())
    assert report["total_phrases"] >= 100
    assert report["in_domain_accuracy_pct"] >= 85.0, report["failures"]
    assert report["abstention_accuracy_pct"] >= 90.0, report["failures"]
    s0 = report["sprint0_regression_case"]
    assert s0["predicted_service"] == "Equipos de Cómputo e Impresoras"
    assert s0["confidence"] >= 0.60
    assert s0["assumed_sede"] is None
    assert s0["assumed_location"] is None
    assert s0["assumed_urgency"] is None


def test_no_demo_credentials_exposed_when_demo_mode_disabled(sprint5_client):
    """Con DEMO_MODE apagado no se exponen contraseñas ni usuarios demo en /login o /api/v1/auth/demo-users."""
    client, _ = sprint5_client

    demo_res = client.get("/api/v1/auth/demo-users")
    assert demo_res.status_code == 200
    assert demo_res.json() == {"demo_mode": False, "users": []}

    login_html = client.get("/login").text
    for secret in ("Admin2026*", "Coord2026*", "Director2026*", "Tecnico2026*", "User2026*"):
        assert secret not in login_html

    denied = client.post(
        "/api/v1/auth/login",
        json={"email": "coordinador@unicesar.edu.co", "demo_mode": True},
    )
    assert denied.status_code == 403
