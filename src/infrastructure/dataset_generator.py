"""Re-exportación retrocompatible del generador sintético desde src.infrastructure.ml."""

from src.infrastructure.ml.dataset_generator import (
    DEFAULT_RAW_PATH,
    generate_synthetic_dataset,
)

__all__ = ["DEFAULT_RAW_PATH", "generate_synthetic_dataset"]
