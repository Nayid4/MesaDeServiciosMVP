"""Estrategias de clasificación NLP (Patrón Strategy) sobre pipelines TF-IDF."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Sequence

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.infrastructure.ml.ml_text_normalizer import (
    SPANISH_STOPWORDS,
    normalize_tic_synonyms_impl,
)


class KeywordRuleClassifier(BaseEstimator, ClassifierMixin):
    """Baseline determinístico por coincidencia de palabras clave y sinónimos TIC."""

    DEFAULT_RULES: Dict[str, tuple[str, ...]] = {
        "Conectividad y Redes Wi-Fi": (
            "wifi", "wi-fi", "eduroam", "internet", "lan", "dhcp", "switch", "vpn", "ethernet", "red_inalambrica",
        ),
        "Plataformas Académicas (Aula Web / Vortal)": (
            "vortal", "aula web", "aula_web", "moodle", "matricula", "calificaciones", "plataforma_academica",
        ),
        "Correo Institucional y Cuentas": (
            "@unicesar", "buzon", "mfa", "contrasena", "clave", "correo_institucional", "webmail",
        ),
        "Aulas Inteligentes y Videoproyectores": (
            "videoproyector", "proyector", "videobeam", "hdmi", "vga", "pantalla interactiva", "parlantes", "aula_inteligente",
        ),
        "Equipos de Cómputo e Impresoras": (
            "pc", "computador", "computadora", "torre", "cpu", "portatil", "no_prende", "no_enciende",
            "pantalla_negra", "sin_video", "impresora", "toner", "escaner", "equipo_computo", "pantallazo azul", "pitidos",
        ),
        "Software y Licenciamiento": (
            "spss", "matlab", "autocad", "rstudio", "licencia", "office", "ofimatico", "software", "antivirus",
        ),
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
        norm = normalize_tic_synonyms_impl(text)
        tokens = set(re.findall(r"[a-z0-9_@.-]+", norm))
        scores = np.zeros(len(self.classes_), dtype=float)
        for idx, cls in enumerate(self.classes_):
            kws = self.DEFAULT_RULES.get(str(cls), ())
            hits = sum(
                1.0
                for kw in kws
                if ((" " in kw and kw in norm) or (kw in tokens or kw in norm))
            )
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
    """Contrato Strategy (OCP) para arquitecturas candidatas de clasificación NLP."""

    model_id: str
    display_name: str
    is_baseline: bool
    rationale: str

    @abstractmethod
    def build_pipeline(self, random_state: int = 42, preprocessor: Any = None) -> Pipeline: ...


class KeywordBaselineStrategy(ClassificationModelStrategy):
    model_id = "keyword_baseline"
    display_name = "Dummy / Keyword Baseline (Reglas Simples)"
    is_baseline = True
    rationale = (
        "Clasificador determinístico basado únicamente en reglas manuales de coincidencia de palabras clave "
        "(sin vectorización TF-IDF ni aprendizaje de contexto)."
    )

    def build_pipeline(self, random_state: int = 42, preprocessor: Any = None) -> Pipeline:
        _ = (random_state, preprocessor)
        return Pipeline([("clf", KeywordRuleClassifier(alpha=0.5))])


class MultinomialNBStrategy(ClassificationModelStrategy):
    model_id = "multinomial_nb"
    display_name = "Multinomial Naive Bayes (Alpha=0.5 Tuned)"
    is_baseline = False
    rationale = (
        "Modelo probabilístico bayesiano sobre TF-IDF (1-2) con sinónimos TIC, stopwords y suavizado de Laplace (alpha=0.5)."
    )

    def build_pipeline(self, random_state: int = 42, preprocessor: Any = None) -> Pipeline:
        _ = random_state
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=6500,
                        min_df=2,
                        preprocessor=preprocessor or normalize_tic_synonyms_impl,
                        stop_words=SPANISH_STOPWORDS,
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
        "Clasificador lineal discriminativo con regularización L2 (C=2.0) sobre bigramas TF-IDF, sinónimos TIC y stopwords."
    )

    def build_pipeline(self, random_state: int = 42, preprocessor: Any = None) -> Pipeline:
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=7500,
                        min_df=2,
                        preprocessor=preprocessor or normalize_tic_synonyms_impl,
                        stop_words=SPANISH_STOPWORDS,
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
        "Máquina de Soporte Vectorial de alto margen lineal sobre TF-IDF (1-2) con sinónimos TIC y Platt Scaling."
    )

    def build_pipeline(self, random_state: int = 42, preprocessor: Any = None) -> Pipeline:
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=7500,
                        min_df=2,
                        preprocessor=preprocessor or normalize_tic_synonyms_impl,
                        stop_words=SPANISH_STOPWORDS,
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
