"""Comandos CQRS de entrenamiento MLOps y activación de modelo productivo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from src.application.common import Command
from src.domain.exceptions import ForbiddenError, NotFoundError
from src.domain.ports import IUnitOfWork
from src.infrastructure.ml.ai_engine import LocalNLPEngine
from src.infrastructure.ml.cleaning_pipeline import DEFAULT_CLEAN_PATH, clean_tickets_dataset
from src.infrastructure.ml.dataset_generator import DEFAULT_RAW_PATH, generate_synthetic_dataset
from src.infrastructure.ml.model_trainer import (
    DEFAULT_MODELS_DIR,
    set_active_model,
    train_and_evaluate_models,
)


@dataclass(frozen=True)
class TrainModelsCommand(Command):
    actor: Dict[str, Any]
    n_rows: int = 18000
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class ActivateModelCommand(Command):
    actor: Dict[str, Any]
    model_id: str
    ip_address: str = "127.0.0.1"


class TrainModelsCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork], ai_engine: LocalNLPEngine) -> None:
        self._uow_factory = uow_factory
        self._ai_engine = ai_engine

    def handle(self, cmd: TrainModelsCommand) -> Dict[str, Any]:
        if cmd.actor.get("role") not in ("coordinador", "admin"):
            raise ForbiddenError("Solo Coordinador o Administrador pueden reentrenar el pipeline ML.")

        raw_path = Path(DEFAULT_RAW_PATH)
        clean_path = Path(DEFAULT_CLEAN_PATH)
        excluded_path = Path("data/processed/upc_tickets_excluded.csv")
        models_dir = Path(DEFAULT_MODELS_DIR)

        generate_synthetic_dataset(n_rows=cmd.n_rows, output_path=raw_path)
        _, _, clean_summary = clean_tickets_dataset(raw_path, clean_path, excluded_path)
        registry = train_and_evaluate_models(clean_csv_path=clean_path, models_dir=models_dir)
        self._ai_engine.invalidate_cache()

        with self._uow_factory() as uow:
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "ML_PIPELINE_RETRAINED",
                    "entity": "ml_models",
                    "entity_id": registry["active_model_id"],
                    "new_value": (
                        f"Rows={clean_summary['total_clean']} | Active={registry['active_model_id']} | "
                        f"Gain=+{registry['f1_gain_vs_baseline_pct']}pp"
                    ),
                }
            )
            uow.commit()

        return {"clean_summary": clean_summary, "registry": registry}


class ActivateModelCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork], ai_engine: LocalNLPEngine) -> None:
        self._uow_factory = uow_factory
        self._ai_engine = ai_engine

    def handle(self, cmd: ActivateModelCommand) -> Dict[str, Any]:
        if cmd.actor.get("role") not in ("coordinador", "admin"):
            raise ForbiddenError("Solo Coordinador o Administrador pueden cambiar el modelo en producción.")
        try:
            updated = set_active_model(cmd.model_id, registry_path=self._ai_engine.registry_path)
        except (ValueError, FileNotFoundError) as exc:
            raise NotFoundError(str(exc)) from exc

        self._ai_engine.invalidate_cache()
        with self._uow_factory() as uow:
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "ML_MODEL_ACTIVATED",
                    "entity": "ml_models",
                    "entity_id": cmd.model_id,
                    "new_value": f"Modelo productivo activado: {cmd.model_id}",
                }
            )
            uow.commit()
        return updated
