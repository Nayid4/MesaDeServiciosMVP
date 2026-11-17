"""Bootstrap idempotente del sistema CASAGBI (Dataset 18k -> Limpieza -> Modelos ML -> SQLite)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.infrastructure.ml.cleaning_pipeline import (
    DEFAULT_CLEAN_PATH,
    DEFAULT_EXCLUDED_PATH,
    DEFAULT_RAW_PATH,
    clean_tickets_dataset,
)
from src.infrastructure.ml.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml.model_trainer import (
    DEFAULT_REGISTRY_PATH,
    load_model_registry,
    train_and_evaluate_models,
)
from src.infrastructure.persistence.database import init_database


def ensure_system_bootstrapped(
    db_path: Optional[str | Path] = None,
    n_rows: int = 18000,
) -> dict:
    """Garantiza datasets, artefactos .joblib del registro y base SQLite inicializada."""
    actions_executed = []

    raw_path = Path(DEFAULT_RAW_PATH)
    clean_path = Path(DEFAULT_CLEAN_PATH)
    excluded_path = Path(DEFAULT_EXCLUDED_PATH)
    registry_path = Path(DEFAULT_REGISTRY_PATH)

    if not raw_path.exists():
        generate_synthetic_dataset(n_rows=n_rows, output_path=raw_path)
        actions_executed.append("dataset_generated")

    if not clean_path.exists() or not excluded_path.exists():
        clean_tickets_dataset(
            raw_path=raw_path,
            clean_path=clean_path,
            excluded_path=excluded_path,
        )
        actions_executed.append("dataset_cleaned")

    needs_training = not registry_path.exists()
    if not needs_training:
        reg = load_model_registry(registry_path)
        if not reg:
            needs_training = True
        else:
            active_id = reg.get("active_model_id")
            active_meta = next((m for m in reg.get("models", []) if m["model_id"] == active_id), None)
            if not active_meta or not Path(active_meta["artifact_path"]).exists():
                needs_training = True

    if needs_training:
        train_and_evaluate_models(clean_csv_path=clean_path, models_dir=registry_path.parent)
        actions_executed.append("models_trained")

    resolved_db = init_database(db_path=db_path, seed=True)
    actions_executed.append(f"db_ready:{resolved_db}")

    return {"actions": actions_executed, "db_path": str(resolved_db)}


if __name__ == "__main__":
    result = ensure_system_bootstrapped()
    print("Bootstrap CASAGBI completado:", result)
