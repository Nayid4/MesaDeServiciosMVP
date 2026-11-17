"""Re-exportación retrocompatible del pipeline CRISP-DM desde src.infrastructure.ml."""

from src.infrastructure.ml.cleaning_pipeline import (
    DEFAULT_CLEAN_PATH,
    DEFAULT_EXCLUDED_PATH,
    DEFAULT_RAW_PATH,
    clean_tickets_dataset,
)

__all__ = [
    "DEFAULT_RAW_PATH",
    "DEFAULT_CLEAN_PATH",
    "DEFAULT_EXCLUDED_PATH",
    "clean_tickets_dataset",
]
