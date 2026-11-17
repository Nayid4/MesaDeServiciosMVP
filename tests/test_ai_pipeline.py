"""Pruebas CRISP-DM, pipeline ML 4-estrategias, Agente IA y limpieza de frontend."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.ai_agent import (
    ConfirmAgentDraftCommand,
    ConfirmAgentDraftCommandHandler,
    ProcessAgentTurnCommand,
    ProcessAgentTurnCommandHandler,
)
from src.application.auth import RegisterInstitutionalUserCommand, RegisterInstitutionalUserCommandHandler
from src.application.tickets import CreateTicketCommand, CreateTicketCommandHandler
from src.cleaning import clean_tickets_dataset
from src.infrastructure.composition import reset_runtime_dependencies, uow_factory
from src.infrastructure.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml.ai_engine import LocalNLPEngine
from src.infrastructure.ml_pipeline import (
    predict_all_models_side_by_side,
    train_and_evaluate_models,
)
from src.infrastructure.persistence.database import dispose_engines, init_database


@pytest.fixture
def isolated_test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "tickets_pruebas.db"
    monkeypatch.setenv("CASAGBI_DB_PATH", str(db_file))
    reset_runtime_dependencies()
    dispose_engines()
    init_database(db_file, seed=True)
    yield str(db_file)
    dispose_engines()
    reset_runtime_dependencies()


def test_data_generation_and_crispdm_cleaning(tmp_path):
    raw_file = tmp_path / "raw_tickets.csv"
    clean_file = tmp_path / "clean_tickets.csv"
    excl_file = tmp_path / "excluded_tickets.csv"

    df_raw = generate_synthetic_dataset(n_rows=1000, output_path=raw_file, seed=7)
    assert len(df_raw) == 1000

    df_clean, df_excluded, summary = clean_tickets_dataset(raw_file, clean_file, excl_file)
    assert summary["total_raw"] == 1000
    assert summary["total_clean"] + summary["total_excluded"] == 1000
    assert summary["imputed_locations"] >= 1
    assert not df_excluded.empty
    assert df_clean["ubicacion"].isna().sum() == 0


def test_ml_pipeline_training_cv5_and_side_by_side(tmp_path):
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

    active_meta = next(m for m in registry["models"] if m["model_id"] == registry["active_model_id"])
    assert active_meta["f1_macro"] >= 0.80
    assert active_meta["cv_f1_mean"] >= 0.80

    side_by_side = predict_all_models_side_by_side(
        "El servidor de Moodle y Aula Web está caído para todo el campus Sabanas",
        registry_path=models_dir / "model_registry.json",
    )
    assert len(side_by_side) == 4
    assert all("predicted_service" in item and "confidence_pct" in item for item in side_by_side)


def test_agent_tools_rag_check_draft_and_confirm(isolated_test_db, tmp_path):
    raw_file = tmp_path / "raw_agent.csv"
    clean_file = tmp_path / "clean_agent.csv"
    excl_file = tmp_path / "excl_agent.csv"
    models_dir = tmp_path / "models_agent"

    generate_synthetic_dataset(n_rows=600, output_path=raw_file, seed=11)
    clean_tickets_dataset(raw_file, clean_file, excl_file)
    train_and_evaluate_models(clean_csv_path=clean_file, models_dir=models_dir)

    reg_handler = RegisterInstitutionalUserCommandHandler(uow_factory(isolated_test_db))
    auth = reg_handler.handle(
        RegisterInstitutionalUserCommand(
            email="agente.cqrs@unicesar.edu.co",
            full_name="Tester CQRS Agent",
            password="UpcPassword2026!",
            sede="Sede Sabanas (Valledupar)",
            privacy_accepted=True,
        )
    )
    user = auth["user"]

    create_handler = CreateTicketCommandHandler(uow_factory(isolated_test_db))
    ticket = create_handler.handle(
        CreateTicketCommand(
            actor=user,
            title="Fallo proyector aula Bloque B",
            description="El proyector HDMI del Bloque B no enciende antes de clase.",
            ticket_type="Incidencia",
            service_name="Aulas Inteligentes y Videoproyectores",
            sede="Sede Sabanas (Valledupar)",
            location="Bloque B",
            urgency="Alta",
        )
    )

    ai_engine = LocalNLPEngine(registry_path=models_dir / "model_registry.json")
    agent_handler = ProcessAgentTurnCommandHandler(uow_factory(isolated_test_db), ai_engine)

    res_hi = agent_handler.handle(ProcessAgentTurnCommand(user=user, message="Hola, qué sedes atiende CASAGBI?"))
    assert res_hi["status"] == "conversational"
    assert "Sabanas" in res_hi["reply"]

    res_kb = agent_handler.handle(ProcessAgentTurnCommand(user=user, message="Olvidé mi contraseña del correo @unicesar.edu.co"))
    assert res_kb["tool_invoked"] == "search_kb"
    assert len(res_kb["matched_articles"]) >= 1

    res_status = agent_handler.handle(ProcessAgentTurnCommand(user=user, message=f"Estado de radicado {ticket['ticket_number']}"))
    assert res_status["tool_invoked"] == "check_ticket"
    assert ticket["ticket_number"] in res_status["reply"]

    res_draft = agent_handler.handle(
        ProcessAgentTurnCommand(
            user=user,
            message="Por favor necesito abrir un ticket porque el switch del Bloque B de Sabanas no da red",
        )
    )
    assert res_draft["tool_invoked"] == "draft_ticket"
    assert res_draft["draft_card"]["sede"] == "Sede Sabanas (Valledupar)"
    assert res_draft["draft_card"]["location"] == "Bloque B"

    confirm_handler = ConfirmAgentDraftCommandHandler(uow_factory(isolated_test_db))
    confirmed = confirm_handler.handle(
        ConfirmAgentDraftCommand(
            actor=user,
            title=res_draft["draft_card"]["title"],
            description=res_draft["draft_card"]["description"],
            service_name=res_draft["draft_card"]["service_name"],
            sede=res_draft["draft_card"]["sede"],
            location=res_draft["draft_card"]["location"],
            urgency=res_draft["draft_card"]["urgency"],
            ai_suggested_service=res_draft["draft_card"]["service_name"],
            ai_confidence=res_draft["draft_card"]["confidence_pct"],
            transcript="USER: Switch Bloque B caido",
        )
    )
    assert confirmed["ticket_number"].startswith("MS-")
    assert confirmed["ticket_number"] != ticket["ticket_number"]


def test_zero_streamlit_traces_and_zero_ui_emojis():
    """Verifica eliminación total de Streamlit y cero emojis en src/presentation/web/."""
    assert not (ROOT_DIR / "dashboard").exists()
    assert not (ROOT_DIR / ".streamlit").exists()

    req_text = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "streamlit" not in req_text

    for py_file in (ROOT_DIR / "src").rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert not re.search(r"\bstreamlit\b", content), f"Referencia a streamlit en {py_file}"

    # Cero emojis en plantillas y scripts web
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    web_files = [
        *(ROOT_DIR / "src" / "presentation" / "web").rglob("*.html"),
        *(ROOT_DIR / "src" / "presentation" / "web").rglob("*.js"),
        *(ROOT_DIR / "src" / "presentation" / "web").rglob("*.css"),
    ]
    assert len(web_files) >= 6
    for web_file in web_files:
        text = web_file.read_text(encoding="utf-8")
        match = emoji_re.search(text)
        assert match is None, f"Emoji '{match.group(0)}' encontrado en {web_file}"
