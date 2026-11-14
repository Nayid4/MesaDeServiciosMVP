"""Bootstrap idempotente del sistema CASAGBI (Dataset -> Limpieza -> Modelos ML -> SQLite)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.cleaning import DEFAULT_CLEAN_PATH, DEFAULT_EXCLUDED_PATH, clean_tickets_dataset
from src.infrastructure.database import init_database
from src.infrastructure.dataset_generator import DEFAULT_RAW_PATH, generate_synthetic_dataset
from src.infrastructure.ml_pipeline import DEFAULT_REGISTRY_PATH, train_and_evaluate_models


def ensure_system_bootstrapped(
    db_path: Optional[str | Path] = None,
    n_rows: int = 18000,
) -> dict:
    """
    Asegura que existan el dataset sintético crudo, los datasets procesados,
    los modelos entrenados (.joblib + model_registry.json) y la base de datos SQLite
    con su seeder inicial. Idempotente para entorno local y contenedores Docker.
    """
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

    if not registry_path.exists():
        train_and_evaluate_models(clean_csv_path=clean_path, models_dir=registry_path.parent)
        actions_executed.append("models_trained")

    resolved_db = init_database(db_path=db_path, seed=True)
    actions_executed.append(f"db_ready:{resolved_db}")

    return {"actions": actions_executed, "db_path": str(resolved_db)}


if __name__ == "__main__":
    result = ensure_system_bootstrapped()
    print("Bootstrap CASAGBI completado:", result)
