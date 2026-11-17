"""Re-exportación retrocompatible del entrenador NLP desde src.infrastructure.ml."""

from src.infrastructure.ml.model_trainer import (
    DEFAULT_CLEAN_PATH,
    DEFAULT_MODELS_DIR,
    DEFAULT_MODEL_STRATEGIES,
    DEFAULT_REGISTRY_PATH,
    CalibratedLinearSVCStrategy,
    ClassificationModelStrategy,
    KeywordBaselineStrategy,
    KeywordRuleClassifier,
    LogisticRegressionStrategy,
    MultinomialNBStrategy,
    load_active_classifiers,
    load_model_registry,
    predict_all_models_side_by_side,
    predict_ticket_classification,
    set_active_model,
    train_and_evaluate_models,
)

__all__ = [
    "DEFAULT_CLEAN_PATH",
    "DEFAULT_MODELS_DIR",
    "DEFAULT_REGISTRY_PATH",
    "DEFAULT_MODEL_STRATEGIES",
    "KeywordRuleClassifier",
    "ClassificationModelStrategy",
    "KeywordBaselineStrategy",
    "MultinomialNBStrategy",
    "LogisticRegressionStrategy",
    "CalibratedLinearSVCStrategy",
    "train_and_evaluate_models",
    "load_model_registry",
    "set_active_model",
    "load_active_classifiers",
    "predict_ticket_classification",
    "predict_all_models_side_by_side",
]
