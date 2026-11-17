"""Entrenamiento y evaluación NLP multi-modelo con Patrón Strategy y Stratified 5-Fold CV."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

from src.domain.rules import UPC_SERVICE_CATALOG
from src.infrastructure.ml.ml_inference import (
    DEFAULT_MODELS_DIR,
    DEFAULT_REGISTRY_PATH,
    MIN_CONFIDENCE_THRESHOLD,
    load_active_classifiers,
    load_model_registry,
    predict_all_models_side_by_side,
    predict_ticket_classification,
    set_active_model,
)
from src.infrastructure.ml.ml_strategies import (
    DEFAULT_MODEL_STRATEGIES,
    CalibratedLinearSVCStrategy,
    ClassificationModelStrategy,
    KeywordBaselineStrategy,
    KeywordRuleClassifier,
    LogisticRegressionStrategy,
    MultinomialNBStrategy,
)
from src.infrastructure.ml.ml_text_normalizer import (
    DOMAIN_SIGNAL_TERMS,
    SPANISH_STOPWORDS,
    _SYNONYM_PATTERNS,
    count_domain_signals,
    normalize_tic_synonyms_impl,
)
from src.metrics import compute_classification_metrics

DEFAULT_CLEAN_PATH = Path("data/processed/upc_tickets_clean.csv")


def normalize_tic_synonyms(text: str) -> str:
    """Normaliza tildes, typos comunes y sinónimos TIC (serializable bajo model_trainer)."""
    return normalize_tic_synonyms_impl(text)


def _extract_top_keywords_per_service(
    fitted_linear_pipe: Optional[Pipeline], top_n: int = 15
) -> Dict[str, List[Dict[str, Any]]]:
    if fitted_linear_pipe is None or "tfidf" not in fitted_linear_pipe.named_steps or "clf" not in fitted_linear_pipe.named_steps:
        return {}
    tfidf: TfidfVectorizer = fitted_linear_pipe.named_steps["tfidf"]
    clf = fitted_linear_pipe.named_steps["clf"]
    if not hasattr(clf, "coef_") or not hasattr(clf, "classes_"):
        return {}
    feature_names = tfidf.get_feature_names_out()
    coefs = clf.coef_
    classes = list(clf.classes_)
    coef_matrix = np.vstack([-coefs[0], coefs[0]]) if (coefs.shape[0] == 1 and len(classes) == 2) else coefs
    return {
        str(cls): [
            {"term": str(feature_names[i]), "weight": round(float(coef_matrix[idx][i]), 4)}
            for i in np.argsort(coef_matrix[idx])[::-1][:top_n]
        ]
        for idx, cls in enumerate(classes)
    }


def train_and_evaluate_models(
    clean_csv_path: Path | str = DEFAULT_CLEAN_PATH,
    models_dir: Path | str = DEFAULT_MODELS_DIR,
    test_size: float = 0.2,
    random_state: int = 42,
    max_samples: Optional[int] = None,
    strategies: Optional[List[ClassificationModelStrategy]] = None,
    cv_folds: int = 5,
) -> Dict[str, Any]:
    """Entrena y evalúa las 4 arquitecturas con split 80/20 + Stratified 5-Fold CV."""
    out_dir = Path(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(Path(clean_csv_path), encoding="utf-8")
    if max_samples and len(df) > max_samples:
        df = (
            df.groupby("servicio_real", group_keys=False)
            .apply(lambda g: g.sample(n=max(1, int(round(max_samples * len(g) / len(df)))), random_state=random_state))
            .reset_index(drop=True)
        )

    X = df["texto_completo"].fillna("").astype(str)
    y_service = df["servicio_real"].astype(str)
    y_urgency = df["urgencia"].astype(str)
    labels = sorted(list(UPC_SERVICE_CATALOG.keys()))

    X_train, X_test, y_train, y_test, y_urg_train, y_urg_test = train_test_split(
        X, y_service, y_urgency, test_size=test_size, random_state=random_state, stratify=y_service
    )

    active_strategies = strategies or DEFAULT_MODEL_STRATEGIES
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    model_records: List[Dict[str, Any]] = []
    explainability_pipe: Optional[Pipeline] = None

    for strat in active_strategies:
        cv_scores = cross_val_score(
            strat.build_pipeline(random_state=random_state, preprocessor=normalize_tic_synonyms),
            X_train,
            y_train,
            cv=skf,
            scoring="f1_macro",
            n_jobs=1,
        )
        pipe = strat.build_pipeline(random_state=random_state, preprocessor=normalize_tic_synonyms)
        t0 = time.perf_counter()
        pipe.fit(X_train, y_train)
        train_seconds = round(time.perf_counter() - t0, 3)
        if strat.model_id == "logistic_regression":
            explainability_pipe = pipe

        t_inf = time.perf_counter()
        y_pred = pipe.predict(X_test)
        latency_ms = round(((time.perf_counter() - t_inf) * 1000.0) / max(1, len(X_test)), 4)
        metrics = compute_classification_metrics(y_test, y_pred, labels=labels)
        artifact_path = out_dir / f"{strat.model_id}.joblib"
        joblib.dump(pipe, artifact_path)
        model_records.append(
            {
                "model_id": strat.model_id,
                "display_name": strat.display_name,
                "is_baseline": strat.is_baseline,
                "rationale": strat.rationale,
                "artifact_path": str(artifact_path).replace("\\", "/"),
                "train_seconds": train_seconds,
                "latency_ms": latency_ms,
                "cv_folds": cv_folds,
                "cv_f1_mean": round(float(np.mean(cv_scores)), 4),
                "cv_f1_std": round(float(np.std(cv_scores)), 4),
                **metrics,
            }
        )

    urgency_pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3500, min_df=2, strip_accents="unicode")),
            ("clf", LogisticRegression(C=1.5, max_iter=500, class_weight="balanced", random_state=random_state)),
        ]
    )
    urgency_pipe.fit(X_train, y_urg_train)
    urgency_metrics = compute_classification_metrics(y_urg_test, urgency_pipe.predict(X_test), labels=["Alta", "Baja", "Media"])
    urgency_artifact = out_dir / "urgency_classifier.joblib"
    joblib.dump(urgency_pipe, urgency_artifact)

    best_model = max(
        model_records,
        key=lambda m: (m["f1_macro"], not m["is_baseline"], m["cv_f1_mean"], m["accuracy"], -m["latency_ms"]),
    )
    baseline_rec = next((m for m in model_records if m["is_baseline"]), model_records[0])
    registry = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "cv_folds": cv_folds,
        "active_model_id": best_model["model_id"],
        "urgency_model_path": str(urgency_artifact).replace("\\", "/"),
        "urgency_f1_macro": urgency_metrics["f1_macro"],
        "f1_gain_vs_baseline_pct": round((best_model["f1_macro"] - baseline_rec["f1_macro"]) * 100.0, 2),
        "labels": labels,
        "top_keywords_per_service": _extract_top_keywords_per_service(explainability_pipe, top_n=15),
        "models": model_records,
    }
    (out_dir / "model_registry.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


__all__ = [
    "CalibratedLinearSVCStrategy",
    "ClassificationModelStrategy",
    "DEFAULT_CLEAN_PATH",
    "DEFAULT_MODELS_DIR",
    "DEFAULT_MODEL_STRATEGIES",
    "DEFAULT_REGISTRY_PATH",
    "DOMAIN_SIGNAL_TERMS",
    "KeywordBaselineStrategy",
    "KeywordRuleClassifier",
    "LogisticRegressionStrategy",
    "MIN_CONFIDENCE_THRESHOLD",
    "MultinomialNBStrategy",
    "SPANISH_STOPWORDS",
    "_SYNONYM_PATTERNS",
    "count_domain_signals",
    "load_active_classifiers",
    "load_model_registry",
    "normalize_tic_synonyms",
    "predict_all_models_side_by_side",
    "predict_ticket_classification",
    "set_active_model",
    "train_and_evaluate_models",
]
