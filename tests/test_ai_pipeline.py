"""Pruebas de integración sobre BD separada (tickets_pruebas.db), pipeline CRISP-DM e IA."""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import re
from pathlib import Path

from src.application.ai_use_cases import AIService, AIServiceUnavailableError
from src.application.auth_use_cases import AuthService
from src.application.ticket_use_cases import TicketService
from src.cleaning import clean_tickets_dataset
from src.domain.repositories import (
    IAuditRepository,
    ICatalogRepository,
    IKnowledgeRepository,
    ITicketRepository,
    IUserRepository,
)
from src.infrastructure.container import DependencyContainer, get_container
from src.infrastructure.database import get_connection, init_database
from src.infrastructure.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml_pipeline import (
    predict_all_models_side_by_side,
    train_and_evaluate_models,
)


@pytest.fixture()
def isolated_test_db(tmp_path, monkeypatch):
    """Configura base de datos aislada `tickets_pruebas.db` sin tocar operación."""
    test_db = tmp_path / "tickets_pruebas.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(test_db))
    init_database(db_path=test_db, seed=True)
    return str(test_db)


def test_data_generation_and_crispdm_cleaning(tmp_path):
    raw_file = tmp_path / "raw_sample.csv"
    clean_file = tmp_path / "clean_sample.csv"
    excl_file = tmp_path / "excl_sample.csv"

    df_raw = generate_synthetic_dataset(n_rows=1000, output_path=raw_file, seed=7)
    assert len(df_raw) == 1000

    df_clean, df_excl, summary = clean_tickets_dataset(raw_file, clean_file, excl_file)
    assert summary["total_raw"] == 1000
    assert len(df_clean) + len(df_excl) == 1000
    assert len(df_excl) > 0
    assert "exclusion_reason" in df_excl.columns
    assert int(df_clean["ubicacion"].isna().sum()) == 0
    assert (df_clean["tiempo_resolucion_horas"] >= 0).all()


def test_ml_pipeline_training_and_inference(tmp_path):
    raw_file = tmp_path / "raw_ml.csv"
    clean_file = tmp_path / "clean_ml.csv"
    excl_file = tmp_path / "excl_ml.csv"
    models_dir = tmp_path / "models"

    generate_synthetic_dataset(n_rows=1200, output_path=raw_file, seed=11)
    clean_tickets_dataset(raw_file, clean_file, excl_file)

    registry = train_and_evaluate_models(clean_csv_path=clean_file, models_dir=models_dir)
    assert len(registry["models"]) == 4
    assert registry["cv_folds"] == 5
    assert "top_keywords_per_service" in registry
    assert {m["model_id"] for m in registry["models"]} == {
        "keyword_baseline",
        "multinomial_nb",
        "logistic_regression",
        "linear_svc",
    }
    active_id = registry["active_model_id"]
    active_meta = next(m for m in registry["models"] if m["model_id"] == active_id)
    assert active_meta["f1_macro"] >= 0.80
    assert active_meta["cv_f1_mean"] >= 0.80
    assert "cv_f1_std" in active_meta

    side_by_side = predict_all_models_side_by_side(
        "El servidor de Moodle y Aula Virtual está caído para todo el campus Sabanas",
        registry_path=models_dir / "model_registry.json",
    )
    assert len(side_by_side) == 4
    assert all("predicted_service" in item and "confidence_pct" in item for item in side_by_side)

    ai_svc = AIService(registry_path=models_dir / "model_registry.json")
    pred = ai_svc.classify_ticket_text(
        "Sin conexión a red Wi-Fi Eduroam en Bloque B",
        "No asigna IP ni carga internet en los portátiles de clase.",
    )
    assert pred["predicted_service"] == "Conectividad y Redes Wi-Fi"
    assert pred["confidence_pct"] > 30.0

    # Verificar tolerancia a fallos RNF-06
    with pytest.raises(AIServiceUnavailableError):
        ai_svc.classify_ticket_text("Ayuda", "Sin wifi", simulate_failure=True)


def test_end_to_end_auth_ticket_kb_and_immutable_audit(isolated_test_db):
    auth_svc = AuthService(db_path=isolated_test_db)
    ticket_svc = TicketService(db_path=isolated_test_db)
    ai_svc = AIService(db_path=isolated_test_db)

    # 1. Login institucional y rotación token
    session = auth_svc.login("estudiante@unicesar.edu.co", "User2026*")
    assert session["user"]["role"] == "usuario"
    assert session["access_token"]
    assert session["refresh_token"]

    # 2. Asistente IA Nivel 0 sobre KB pública
    res_kb = ai_svc.process_assistant_message(
        user=session["user"],
        message_text="Cómo conectarme a la red wifi eduroam con mi correo institucional",
        simulate_failure=False,
    )
    assert res_kb["status"] == "kb_matched"
    assert len(res_kb["matched_articles"]) >= 1

    # 3. Simulación caída RNF-06 en asistente
    res_fail = ai_svc.process_assistant_message(
        user=session["user"],
        message_text="El proyector no da señal",
        simulate_failure=True,
    )
    assert res_fail["status"] == "ai_unavailable"
    assert res_fail["should_offer_ticket"] is True

    # 4. Creación de ticket y asignación automática al técnico con menor carga
    created = ticket_svc.create_ticket(
        requester=session["user"],
        title="No conecta proyector HDMI en Bloque D",
        description="El cable HDMI del aula 102 muestra sin señal al conectar el portátil en clase.",
        ticket_type="Incidencia",
        service_name="Aulas Inteligentes y Videoproyectores",
        sede="Sede Sabanas (Valledupar)",
        location="Bloque D",
        urgency="Alta",
        ai_suggested_service="Aulas Inteligentes y Videoproyectores",
        ai_confidence=92.4,
        ai_human_validated=True,
    )
    assert created["ticket_number"].startswith("MS-2026-")
    assert created["priority"] == "P2 Alta"
    assert created["status"] == "Asignado"
    assert created["assigned_tech_email"] is not None

    # 5. Inmutabilidad estricta de audit_logs (RNF-09)
    with get_connection(isolated_test_db) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE audit_logs SET action = 'ALTERED' WHERE id = 1")
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM audit_logs WHERE id = 1")


def test_jwt_refresh_rotation_and_lazy_view_imports(isolated_test_db):
    import importlib
    from dashboard.app import LAZY_ROUTE_MODULES
    from src.infrastructure.security import create_access_token

    auth_svc = AuthService(db_path=isolated_test_db)
    session = auth_svc.login("admin@unicesar.edu.co", "Admin2026*")

    # Simular access token expirado (-1 minuto) manteniendo refresh_token válido
    expired_jwt = create_access_token(session["user"], expires_minutes=-1)
    rotated = auth_svc.verify_or_refresh_session(expired_jwt, session["refresh_token"])
    assert rotated["valid"] is True
    assert rotated["refreshed"] is True
    assert rotated["access_token"] != expired_jwt
    assert rotated["refresh_token"] != session["refresh_token"]

    # Verificar que el refresh token anterior fue revocado (rotación estricta)
    reuse = auth_svc.verify_or_refresh_session(expired_jwt, session["refresh_token"])
    assert reuse["valid"] is False

    # Verificar que todas las rutas lazy-loaded del frontend importan sin errores y exponen render()
    assert len(LAZY_ROUTE_MODULES) == 8
    for route_id, module_path in LAZY_ROUTE_MODULES.items():
        mod = importlib.import_module(module_path)
        assert callable(getattr(mod, "render", None)), f"La vista {route_id} ({module_path}) debe exponer render()"



def test_solid_di_container_zero_sqlite_leak_and_zero_emojis(isolated_test_db):
    """Verifica DIP (contenedor con interfaces), cero fuga de SQLite en vistas y cero emojis en UI."""
    from src.domain.repositories import (
        INotificationRepository,
        IRefreshTokenRepository,
    )

    container = get_container(db_path=isolated_test_db)
    assert isinstance(container, DependencyContainer)
    assert isinstance(container.user_repo, IUserRepository)
    assert isinstance(container.token_repo, IRefreshTokenRepository)
    assert isinstance(container.ticket_repo, ITicketRepository)
    assert isinstance(container.kb_repo, IKnowledgeRepository)
    assert isinstance(container.audit_repo, IAuditRepository)
    assert isinstance(container.notif_repo, INotificationRepository)
    assert isinstance(container.catalog_repo, ICatalogRepository)

    project_root = Path(__file__).resolve().parent.parent
    dashboard_dir = project_root / "dashboard"

    # Cero referencias directas a sqlite3 o sqlite_repositories en la capa de presentación
    ui_view_files = [dashboard_dir / "app.py", *(dashboard_dir / "features").rglob("*.py")]
    for py_file in ui_view_files:
        text = py_file.read_text(encoding="utf-8")
        assert not re.search(r"\b(sqlite3|sqlite_repositories)\b", text), (
            f"Fuga de infraestructura detectada en {py_file}"
        )

    # Cero emojis Unicode en todo dashboard/**/*.py (reemplazados por dashboard/shared/icons.py)
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    for py_file in dashboard_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        match = emoji_re.search(text)
        assert match is None, f"Emoji '{match.group(0)}' prohibido en {py_file}"


def test_casagbi_agent_tools_entity_extraction_and_escalation(isolated_test_db, tmp_path):
    """Valida comprensión conversacional, 4 AgentTool, extracción de sede/bloque y escalamiento."""
    raw_file = tmp_path / "raw_agent.csv"
    clean_file = tmp_path / "clean_agent.csv"
    excl_file = tmp_path / "excl_agent.csv"
    models_dir = tmp_path / "models_agent"

    generate_synthetic_dataset(n_rows=600, output_path=raw_file, seed=11)
    clean_tickets_dataset(raw_file, clean_file, excl_file)
    train_and_evaluate_models(clean_csv_path=clean_file, models_dir=models_dir)

    container = get_container(
        db_path=isolated_test_db,
        registry_path=models_dir / "model_registry.json",
    )
    auth = container.auth_service.register_institutional_user(
        email="agente.test@unicesar.edu.co",
        full_name="Tester Agente UPC",
        password="UpcPassword2026!",
        sede="Sede Sabanas (Valledupar)",
        privacy_accepted=True,
    )
    user = auth["user"]

    ticket = container.ticket_service.create_ticket(
        requester=user,
        title="Fallo proyector aula Bloque B",
        description="El proyector HDMI del Bloque B no enciende antes de clase.",
        ticket_type="Incidente",
        service_name="Aulas Inteligentes y Videoproyectores",
        sede="Sede Sabanas (Valledupar)",
        location="Bloque B",
        urgency="Alta",
    )

    # 1. Comprensión conversacional UPC (saludo / sedes / horarios)
    res_chat = container.ai_service.process_assistant_message(
        user, "Hola, qué sedes y horarios atiende CASAGBI?"
    )
    assert res_chat["status"] == "conversational"
    assert "Sabanas" in res_chat["reply"]

    # 2. Herramienta search_knowledge_base
    res_kb = container.ai_service.process_assistant_message(
        user, "Olvidé mi contraseña del correo institucional @unicesar.edu.co"
    )
    assert res_kb["tool_invoked"] == "search_knowledge_base"
    assert len(res_kb["matched_articles"]) >= 1

    # 3. Herramienta check_ticket_status
    res_status = container.ai_service.process_assistant_message(
        user, f"Por favor revisa el estado de mi radicado {ticket['ticket_number']}"
    )
    assert res_status["tool_invoked"] == "check_ticket_status"
    assert ticket["ticket_number"] in res_status["reply"]

    # 4. Herramienta classify_and_draft_ticket + extracción de entidades (sede, bloque)
    res_draft = container.ai_service.process_assistant_message(
        user,
        "No tengo internet ni wifi eduroam en el Bloque B de Sabanas para la clase de hoy",
        failed_attempts=1,
    )
    assert res_draft["tool_invoked"] == "classify_and_draft_ticket"
    assert res_draft["draft_card"] is not None
    assert res_draft["draft_card"]["sede"] == "Sede Sabanas (Valledupar)"
    assert res_draft["draft_card"]["location"] == "Bloque B"

    # 5. Herramienta escalate_to_human creando ticket con transcript
    res_esc = container.ai_service.escalate_to_human(
        user=user,
        conversation_history=[
            {"role": "user", "content": "No tengo wifi en el Bloque B de Sabanas"},
            {"role": "assistant", "content": res_draft["reply"]},
        ],
        draft_card=res_draft["draft_card"],
        ticket_service=container.ticket_service,
    )
    assert res_esc["tool_name"] == "escalate_to_human"
    assert res_esc["ticket"]["ticket_number"].startswith("MS-")
    assert res_esc["ticket"]["ticket_number"] != ticket["ticket_number"]


def test_public_tracking_hides_pii_and_description_min_length(isolated_test_db):
    """Valida seguimiento público sin fuga de PII, métricas públicas y mínimo de 15 caracteres."""
    import pytest

    container = get_container(db_path=isolated_test_db)
    auth = container.auth_service.register_institutional_user(
        email="ciudadano.upc@unicesar.edu.co",
        full_name="Docente Consulta Pública",
        password="UpcPassword2026!",
        sede="Sede Hurtado (Valledupar)",
        privacy_accepted=True,
    )
    user = auth["user"]

    with pytest.raises(ValueError, match="15"):
        container.ticket_service.create_ticket(
            requester=user,
            title="Falla corta",
            description="Muy corto",
            ticket_type="Incidente",
            service_name="Conectividad y Redes Wi-Fi",
            sede="Sede Hurtado (Valledupar)",
            location="Bloque D",
            urgency="Media",
        )

    created = container.ticket_service.create_ticket(
        requester=user,
        title="Sin conexión en laboratorio de Hurtado",
        description="Los equipos de red cableada en Hurtado no obtienen dirección IP.",
        ticket_type="Incidente",
        service_name="Conectividad y Redes Wi-Fi",
        sede="Sede Hurtado (Valledupar)",
        location="Salón 204",
        urgency="Alta",
    )

    public_info = container.ticket_service.get_public_ticket_tracking(created["ticket_number"])
    assert public_info is not None
    assert public_info["ticket_number"] == created["ticket_number"]
    assert "requester_email" not in public_info
    assert isinstance(public_info["timeline"], list)

    impact = container.ticket_service.get_public_impact_metrics()
    assert "total_tickets" in impact

    workload = container.ticket_service.get_technician_workload()
    assert isinstance(workload, list)
    assert len(workload) >= 1
