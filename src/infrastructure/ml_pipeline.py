"""Pipeline MLOps con Patrón Strategy (OCP), Validación Cruzada 5-Fold y Explicabilidad."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.domain.rules import UPC_SERVICE_CATALOG
from src.metrics import compute_classification_metrics

DEFAULT_CLEAN_PATH = Path("data/processed/upc_tickets_clean.csv")
DEFAULT_MODELS_DIR = Path("models")
DEFAULT_REGISTRY_PATH = DEFAULT_MODELS_DIR / "model_registry.json"


def _strip_accents_lower(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


class KeywordRuleClassifier(BaseEstimator, ClassifierMixin):
    """
    Baseline sencillo basado en reglas fijas de palabras clave (sin aprendizaje estadístico).
    Representa la 'alternativa sencilla' exigida por la rúbrica para demostrar la pertinencia de la IA.
    """

    DEFAULT_RULES: Dict[str, tuple[str, ...]] = {
        "Conectividad y Redes Wi-Fi": ("wifi", "wi-fi", "eduroam", "lan", "dhcp", "switch"),
        "Plataformas Académicas (Aula Web / Vortal)": ("vortal", "aula web", "matricula", "calificaciones"),
        "Correo Institucional y Cuentas": ("@unicesar", "buzon", "mfa", "contrasena", "clave"),
        "Aulas Inteligentes y Videoproyectores": ("videoproyector", "proyector", "hdmi", "pantalla interactiva", "parlantes"),
        "Equipos de Cómputo e Impresoras": ("impresora", "toner", "escaner", "pantallazo azul", "pitidos"),
        "Software y Licenciamiento": ("spss", "matlab", "autocad", "rstudio", "licencia", "ofimatico"),
    }

    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha

    def fit(self, X: Sequence[str], y: Sequence[str]) -> "KeywordRuleClassifier":
        y_arr = np.asarray(list(y), dtype=object)
        classes, counts = np.unique(y_arr, return_counts=True)
        self.classes_ = classes
        self.majority_class_ = str(classes[int(np.argmax(counts))])
        self._class_priors = {str(c): float(cnt / len(y_arr)) for c, cnt in zip(classes, counts)}
        return self

    def _score_text(self, text: str) -> np.ndarray:
        norm = _strip_accents_lower(text)
        tokens = set(re.findall(r"[a-z0-9@._-]+", norm))
        scores = np.zeros(len(self.classes_), dtype=float)
        for idx, cls in enumerate(self.classes_):
            kws = self.DEFAULT_RULES.get(str(cls), ())
            hits = 0.0
            for kw in kws:
                if " " in kw:
                    if kw in norm:
                        hits += 1.0
                elif kw in tokens or kw in norm:
                    hits += 1.0
            scores[idx] = hits + self.alpha * self._class_priors.get(str(cls), 0.1)
        return scores

    def predict_proba(self, X: Sequence[str]) -> np.ndarray:
        probs_list = []
        for text in X:
            scores = self._score_text(text)
            total = float(np.sum(scores))
            probs_list.append(scores / total if total > 0 else np.full_like(scores, 1.0 / len(scores)))
        return np.vstack(probs_list)

    def predict(self, X: Sequence[str]) -> np.ndarray:
        probs = self.predict_proba(X)
        indices = np.argmax(probs, axis=1)
        return np.asarray([self.classes_[i] for i in indices], dtype=object)


class ClassificationModelStrategy(ABC):
    """Contrato Strategy (OCP) para conectar modelos candidatos de clasificación NLP."""

    model_id: str
    display_name: str
    is_baseline: bool
    rationale: str

    @abstractmethod
    def build_pipeline(self, random_state: int = 42) -> Pipeline:
        ...


class KeywordBaselineStrategy(ClassificationModelStrategy):
    model_id = "keyword_baseline"
    display_name = "Dummy / Keyword Baseline (Reglas Simples)"
    is_baseline = True
    rationale = (
        "Clasificador determinístico basado únicamente en reglas manuales de coincidencia de palabras clave "
        "(sin vectorización TF-IDF ni aprendizaje de contexto). Sirve como punto de comparación base."
    )

    def build_pipeline(self, random_state: int = 42) -> Pipeline:
        _ = random_state
        return Pipeline([("clf", KeywordRuleClassifier(alpha=0.5))])


class MultinomialNBStrategy(ClassificationModelStrategy):
    model_id = "multinomial_nb"
    display_name = "Multinomial Naive Bayes (Alpha=0.5 Tuned)"
    is_baseline = False
    rationale = (
        "Modelo probabilístico bayesiano sobre TF-IDF (unigramas y bigramas) con suavizado de Laplace ajustado (alpha=0.5); "
        "muy rápido para inferencia pero asume independencia condicional entre términos."
    )

    def build_pipeline(self, random_state: int = 42) -> Pipeline:
        _ = random_state
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=5000,
                        min_df=2,
                        strip_accents="unicode",
                        sublinear_tf=True,
                    ),
                ),
                ("clf", MultinomialNB(alpha=0.5)),
            ]
        )


class LogisticRegressionStrategy(ClassificationModelStrategy):
    model_id = "logistic_regression"
    display_name = "Logistic Regression (TF-IDF 1-2, C=2.0)"
    is_baseline = False
    rationale = (
        "Clasificador lineal discriminativo con regularización L2 (C=2.0) sobre bigramas TF-IDF y balanceo de clases; "
        "entrega probabilidades calibradas ideales para flujos Human-in-the-Loop y explicabilidad de coeficientes."
    )

    def build_pipeline(self, random_state: int = 42) -> Pipeline:
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=6500,
                        min_df=2,
                        strip_accents="unicode",
                        sublinear_tf=True,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        C=2.0,
                        max_iter=600,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        )


class CalibratedLinearSVCStrategy(ClassificationModelStrategy):
    model_id = "linear_svc"
    display_name = "LinearSVC Calibrado (CalibratedClassifierCV)"
    is_baseline = False
    rationale = (
        "Máquina de Soporte Vectorial de alto margen lineal sobre espacio disperso TF-IDF (unigramas+bigramas), "
        "calibrada mediante Platt Scaling (CalibratedClassifierCV) para emitir probabilidades reales de confianza."
    )

    def build_pipeline(self, random_state: int = 42) -> Pipeline:
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=6500,
                        min_df=2,
                        strip_accents="unicode",
                        sublinear_tf=True,
                    ),
                ),
                (
                    "clf",
                    CalibratedClassifierCV(
                        LinearSVC(C=1.0, class_weight="balanced", dual="auto", random_state=random_state),
                        cv=3,
                    ),
                ),
            ]
        )


DEFAULT_MODEL_STRATEGIES: List[ClassificationModelStrategy] = [
    KeywordBaselineStrategy(),
    MultinomialNBStrategy(),
    LogisticRegressionStrategy(),
    CalibratedLinearSVCStrategy(),
]


def _extract_top_keywords_per_service(
    fitted_linear_pipe: Optional[Pipeline],
    top_n: int = 15,
) -> Dict[str, List[Dict[str, Any]]]:
    """Extrae las `top_n` palabras clave más predictivas por categoría desde TF-IDF + LogisticRegression."""
    if fitted_linear_pipe is None:
        return {}
    if "tfidf" not in fitted_linear_pipe.named_steps or "clf" not in fitted_linear_pipe.named_steps:
        return {}
    tfidf: TfidfVectorizer = fitted_linear_pipe.named_steps["tfidf"]
    clf = fitted_linear_pipe.named_steps["clf"]
    if not hasattr(clf, "coef_") or not hasattr(clf, "classes_"):
        return {}

    feature_names = tfidf.get_feature_names_out()
    coefs = clf.coef_
    classes = list(clf.classes_)
    result: Dict[str, List[Dict[str, Any]]] = {}

    if coefs.shape[0] == 1 and len(classes) == 2:
        coef_matrix = np.vstack([-coefs[0], coefs[0]])
    else:
        coef_matrix = coefs

    for idx, cls in enumerate(classes):
        top_indices = np.argsort(coef_matrix[idx])[::-1][:top_n]
        result[str(cls)] = [
            {"term": str(feature_names[i]), "weight": round(float(coef_matrix[idx][i]), 4)}
            for i in top_indices
        ]
    return result


def train_and_evaluate_models(
    clean_csv_path: Path | str = DEFAULT_CLEAN_PATH,
    models_dir: Path | str = DEFAULT_MODELS_DIR,
    test_size: float = 0.2,
    random_state: int = 42,
    max_samples: Optional[int] = None,
    strategies: Optional[List[ClassificationModelStrategy]] = None,
    cv_folds: int = 5,
) -> Dict[str, Any]:
    """
    Ejecuta split estratificado ANTES de vectorizar TF-IDF, evalúa con Stratified 5-Fold CV
    y Hold-out Test (80/20) las 4 estrategias registradas, extrae Top 15 palabras predictivas
    por servicio, serializa `.joblib` y guarda `models/model_registry.json`.
    """
    clean_file = Path(clean_csv_path)
    out_dir = Path(models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(clean_file, encoding="utf-8")
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

    # Split estratificado estricto ANTES de cualquier vectorización (previene data leakage)
    X_train, X_test, y_train, y_test, y_urg_train, y_urg_test = train_test_split(
        X,
        y_service,
        y_urgency,
        test_size=test_size,
        random_state=random_state,
        stratify=y_service,
    )

    active_strategies = strategies or DEFAULT_MODEL_STRATEGIES
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    model_records: List[Dict[str, Any]] = []
    explainability_pipe: Optional[Pipeline] = None

    for strat in active_strategies:
        pipe_cv = strat.build_pipeline(random_state=random_state)
        cv_scores = cross_val_score(pipe_cv, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=1)

        pipe = strat.build_pipeline(random_state=random_state)
        t_train_start = time.perf_counter()
        pipe.fit(X_train, y_train)
        train_seconds = round(time.perf_counter() - t_train_start, 3)

        if strat.model_id == "logistic_regression":
            explainability_pipe = pipe

        t_inf_start = time.perf_counter()
        y_pred = pipe.predict(X_test)
        total_inf_ms = (time.perf_counter() - t_inf_start) * 1000.0
        latency_ms_per_ticket = round(total_inf_ms / max(1, len(X_test)), 4)

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
                "latency_ms": latency_ms_per_ticket,
                "cv_folds": cv_folds,
                "cv_f1_mean": round(float(np.mean(cv_scores)), 4),
                "cv_f1_std": round(float(np.std(cv_scores)), 4),
                **metrics,
            }
        )

    # Entrenar modelo auxiliar de detección de urgencia
    urgency_pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3500, min_df=2, strip_accents="unicode")),
            ("clf", LogisticRegression(C=1.5, max_iter=500, class_weight="balanced", random_state=random_state)),
        ]
    )
    urgency_pipe.fit(X_train, y_urg_train)
    urg_pred = urgency_pipe.predict(X_test)
    urgency_metrics = compute_classification_metrics(
        y_urg_test, urg_pred, labels=["Alta", "Baja", "Media"]
    )
    urgency_artifact = out_dir / "urgency_classifier.joblib"
    joblib.dump(urgency_pipe, urgency_artifact)

    # Seleccionar automáticamente el mejor modelo por F1-Score Macro (priorizando modelos IA sobre baseline)
    best_model = max(
        model_records,
        key=lambda m: (m["f1_macro"], not m["is_baseline"], m["cv_f1_mean"], m["accuracy"], -m["latency_ms"]),
    )
    baseline_rec = next((m for m in model_records if m["is_baseline"]), model_records[0])
    f1_gain_vs_baseline = round((best_model["f1_macro"] - baseline_rec["f1_macro"]) * 100.0, 2)

    top_keywords = _extract_top_keywords_per_service(explainability_pipe, top_n=15)

    registry = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": int(len(df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "cv_folds": cv_folds,
        "active_model_id": best_model["model_id"],
        "urgency_model_path": str(urgency_artifact).replace("\\", "/"),
        "urgency_f1_macro": urgency_metrics["f1_macro"],
        "f1_gain_vs_baseline_pct": f1_gain_vs_baseline,
        "labels": labels,
        "top_keywords_per_service": top_keywords,
        "models": model_records,
    }

    registry_path = out_dir / "model_registry.json"
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


def load_model_registry(registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> Optional[Dict[str, Any]]:
    """Carga el registro de modelos entrenados si existe."""
    path = Path(registry_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_active_model(
    model_id: str,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> Dict[str, Any]:
    """Marca un modelo entrenado como el modelo activo en producción."""
    registry = load_model_registry(registry_path)
    if not registry:
        raise FileNotFoundError("No existe registro de modelos entrenados.")
    valid_ids = {m["model_id"] for m in registry["models"]}
    if model_id not in valid_ids:
        raise ValueError(f"Modelo '{model_id}' no encontrado en el registro.")
    registry["active_model_id"] = model_id
    Path(registry_path).write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


def load_active_classifiers(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> Dict[str, Any]:
    """Carga los pipelines serializados del clasificador de servicio activo y de urgencia."""
    registry = load_model_registry(registry_path)
    if not registry:
        raise FileNotFoundError("El registro de modelos no existe. Ejecuta el entrenamiento primero.")
    active_id = registry["active_model_id"]
    model_meta = next(m for m in registry["models"] if m["model_id"] == active_id)
    service_model = joblib.load(model_meta["artifact_path"])
    urgency_model = None
    urg_path = registry.get("urgency_model_path")
    if urg_path and Path(urg_path).exists():
        urgency_model = joblib.load(urg_path)
    return {
        "registry": registry,
        "model_meta": model_meta,
        "service_model": service_model,
        "urgency_model": urgency_model,
    }


def predict_ticket_classification(
    text: str,
    loaded_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """Realiza inferencia de servicio y urgencia con nivel de confianza (%)."""
    cleaned_text = (text or "").strip()
    if len(cleaned_text) < 3:
        raise ValueError("El texto para clasificación debe contener al menos 3 caracteres.")

    service_model = loaded_bundle["service_model"]
    urgency_model = loaded_bundle.get("urgency_model")
    meta = loaded_bundle["model_meta"]

    pred_service = str(service_model.predict([cleaned_text])[0])
    confidence_pct = 75.0
    top_probabilities: Dict[str, float] = {}

    if hasattr(service_model, "predict_proba"):
        probs = service_model.predict_proba([cleaned_text])[0]
        classes = list(service_model.classes_)
        top_probabilities = {
            str(cls): round(float(prob) * 100.0, 2)
            for cls, prob in sorted(zip(classes, probs), key=lambda x: -x[1])
        }
        confidence_pct = round(float(np.max(probs)) * 100.0, 2)

    pred_urgency = "Media"
    if urgency_model is not None:
        pred_urgency = str(urgency_model.predict([cleaned_text])[0])

    return {
        "predicted_service": pred_service,
        "predicted_urgency": pred_urgency,
        "confidence_pct": confidence_pct,
        "probabilities": top_probabilities,
        "model_id": meta["model_id"],
        "model_name": meta["display_name"],
    }


def predict_all_models_side_by_side(
    text: str,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> List[Dict[str, Any]]:
    """
    Evalúa un mismo texto de soporte simultáneamente contra las 4 arquitecturas registradas
    (Dummy/Keyword Baseline, MultinomialNB, Logistic Regression y LinearSVC Calibrado).
    """
    cleaned_text = (text or "").strip()
    if len(cleaned_text) < 3:
        raise ValueError("El texto de prueba debe contener al menos 3 caracteres.")

    registry = load_model_registry(registry_path)
    if not registry:
        raise FileNotFoundError("El registro de modelos no existe. Ejecuta el entrenamiento primero.")

    active_id = registry["active_model_id"]
    results: List[Dict[str, Any]] = []

    for meta in registry["models"]:
        model_path = Path(meta["artifact_path"])
        if not model_path.exists():
            continue
        pipe = joblib.load(model_path)
        t0 = time.perf_counter()
        pred_service = str(pipe.predict([cleaned_text])[0])
        probs_dict: Dict[str, float] = {}
        conf_pct = 75.0
        if hasattr(pipe, "predict_proba"):
            probs = pipe.predict_proba([cleaned_text])[0]
            classes = list(pipe.classes_)
            ordered = sorted(zip(classes, probs), key=lambda x: -x[1])
            probs_dict = {str(c): round(float(p) * 100.0, 2) for c, p in ordered}
            conf_pct = round(float(np.max(probs)) * 100.0, 2)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        top_3 = [
            {"service": svc, "probability_pct": prob}
            for svc, prob in list(probs_dict.items())[:3]
        ]
        results.append(
            {
                "model_id": meta["model_id"],
                "display_name": meta["display_name"],
                "is_baseline": meta.get("is_baseline", False),
                "is_active": meta["model_id"] == active_id,
                "predicted_service": pred_service,
                "confidence_pct": conf_pct,
                "latency_ms": latency_ms,
                "probabilities": probs_dict,
                "top_3_probabilities": top_3,
            }
        )

    return results


if __name__ == "__main__":
    reg = train_and_evaluate_models()
    print(f"Entrenamiento completado. Modelo activo: {reg['active_model_id']}")
