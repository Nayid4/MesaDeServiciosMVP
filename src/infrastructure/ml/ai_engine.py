"""Adaptador NLP local (clasificación activa .joblib + búsqueda semántica TF-IDF en KB)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.domain.exceptions import AIServiceUnavailableError
from src.domain.ports import IAIService
from src.domain.rules import UPC_LOCATIONS, UPC_SEDES
from src.infrastructure.ml.model_trainer import (
    DEFAULT_REGISTRY_PATH,
    MIN_CONFIDENCE_THRESHOLD,
    SPANISH_STOPWORDS,
    load_active_classifiers,
    normalize_tic_synonyms,
    predict_all_models_side_by_side,
    predict_ticket_classification,
)

TICKET_ID_REGEX = re.compile(
    r"MS-(?:(?:RED|SIS|ACC|AUL|SOP|SWL|GEN)-)?\d{4}-\d{6}",
    re.IGNORECASE,
)
_EMAIL_PII_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", re.IGNORECASE)
_DIGITS_PII_RE = re.compile(r"\b\d{7,12}\b")
_NAME_INTRO_PII_RE = re.compile(
    r"\b((?i:me\s+llamo|mi\s+nombre\s+es|soy))\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})"
)


def strip_accents_lower(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def scrub_pii_for_model(text: str) -> Tuple[str, bool]:
    """Redacta correos personales, teléfonos/cédulas y nombres propios antes de enviar al modelo NLP."""
    raw = str(text or "")
    scrubbed = False

    def _replace_email(match: re.Match[str]) -> str:
        nonlocal scrubbed
        scrubbed = True
        domain = match.group(1).lower()
        return " dominio_unicesar " if domain == "unicesar.edu.co" else " [correo_redactado] "

    cleaned = _EMAIL_PII_RE.sub(_replace_email, raw)
    cleaned, n_digits = _DIGITS_PII_RE.subn(" [documento_redactado] ", cleaned)
    if n_digits > 0:
        scrubbed = True
    cleaned, n_names = _NAME_INTRO_PII_RE.subn(r"\1 [nombre_redactado]", cleaned)
    if n_names > 0:
        scrubbed = True
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, scrubbed


def extract_explicit_ticket_entities(text: str) -> Dict[str, Optional[str]]:
    """Extrae sede, ubicación y urgencia únicamente cuando el texto los indica explícitamente (cero suposiciones)."""
    norm = strip_accents_lower(text)

    sede: Optional[str] = None
    if "aguachica" in norm:
        sede = "Seccional Aguachica"
    elif "hurtado" in norm:
        sede = "Sede Hurtado (Valledupar)"
    elif "sabana" in norm:
        sede = "Sede Sabanas (Valledupar)"

    location: Optional[str] = None
    location_rules = [
        ("bloque a", "Bloque A"),
        ("bloque b", "Bloque B"),
        ("bloque c", "Bloque C"),
        ("bloque d", "Bloque D"),
        ("laboratorio", "Laboratorios de Cómputo"),
        ("sala de computo", "Laboratorios de Cómputo"),
        ("biblioteca", "Biblioteca"),
        ("edificio administrativo", "Edificio Administrativo"),
        ("administrativo", "Edificio Administrativo"),
        ("rectoria", "Edificio Administrativo"),
        ("admisiones", "Edificio Administrativo"),
    ]
    for pattern, canonical in location_rules:
        if pattern in norm:
            location = canonical
            break

    urgency: Optional[str] = None
    low_urgency_cues = (
        "puedo seguir trabajando",
        "si puedo trabajar",
        "si puedo seguir trabajando",
        "no me impide",
        "sin afan",
        "programable",
        "preventivo",
        "urgencia baja",
    )
    med_urgency_cues = (
        "parcialmente",
        "con dificultad",
        "tengo alternativa",
        "hay alternativa",
        "otro equipo",
        "temporalmente",
        "urgencia media",
        "moderado",
    )
    high_urgency_cues = (
        "no puedo seguir trabajando",
        "no podemos seguir",
        "no puedo trabajar",
        "sin poder trabajar",
        "impide trabajar",
        "actividad detenida",
        "clase detenida",
        "sin alternativa",
        "urgencia alta",
        "bloquea la clase",
        "en examen",
        "urgente",
    )
    if any(cue in norm for cue in high_urgency_cues):
        urgency = "Alta"
    elif any(cue in norm for cue in med_urgency_cues):
        urgency = "Media"
    elif any(cue in norm for cue in low_urgency_cues):
        urgency = "Baja"

    return {"sede": sede, "location": location, "urgency": urgency}


def extract_campus_entities(text: str, user_default_sede: Optional[str] = None) -> Dict[str, str]:
    """Helper heredado para formularios manuales de contingencia."""
    explicit = extract_explicit_ticket_entities(text)
    sede = explicit["sede"] or (user_default_sede if user_default_sede in UPC_SEDES else UPC_SEDES[0])
    location = explicit["location"] or UPC_LOCATIONS[0]
    return {"sede": sede, "location": location}


class LocalNLPEngine(IAIService):
    """Implementación local del puerto IAIService usando scikit-learn y TF-IDF."""

    def __init__(self, registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> None:
        self.registry_path = Path(registry_path)
        self._cached_bundle: Optional[Dict[str, Any]] = None

    def invalidate_cache(self) -> None:
        self._cached_bundle = None

    def _get_bundle(self) -> Dict[str, Any]:
        if self._cached_bundle is None:
            self._cached_bundle = load_active_classifiers(self.registry_path)
        return self._cached_bundle

    def classify_text(self, text: str, simulate_failure: bool = False) -> Dict[str, Any]:
        if simulate_failure:
            raise AIServiceUnavailableError(
                "El motor de Inteligencia Artificial no está disponible en este momento (Simulación RNF-06). "
                "Puede continuar registrando su ticket manualmente sin pérdida de datos."
            )
        try:
            scrubbed_text, pii_scrubbed = scrub_pii_for_model(text)
            bundle = self._get_bundle()
            result = predict_ticket_classification(scrubbed_text or text, bundle)
            result["pii_scrubbed"] = pii_scrubbed
            return result
        except FileNotFoundError as exc:
            raise AIServiceUnavailableError(str(exc)) from exc

    def predict_side_by_side(self, text: str) -> List[Dict[str, Any]]:
        scrubbed_text, _ = scrub_pii_for_model(text)
        return predict_all_models_side_by_side(scrubbed_text or text, registry_path=self.registry_path)

    def search_knowledge_base(
        self,
        query: str,
        articles: List[Dict[str, Any]],
        top_k: int = 3,
        min_similarity: float = 0.25,
    ) -> List[Dict[str, Any]]:
        if not articles or not query or not query.strip():
            return []

        scrubbed_query, _ = scrub_pii_for_model(query.strip())
        corpus = [
            normalize_tic_synonyms(
                f"{a['title']} {a['title']} {a['keywords']} {a['keywords']} {a['symptoms']} {a['service_name']}"
            )
            for a in articles
        ]
        norm_query = normalize_tic_synonyms(scrubbed_query or query.strip())
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 1),
            lowercase=True,
            strip_accents="unicode",
            stop_words=SPANISH_STOPWORDS,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(corpus + [norm_query])
        doc_vecs = matrix[:-1]
        query_vec = matrix[-1]
        sims = cosine_similarity(query_vec, doc_vecs).flatten()

        ranked_indices = np.argsort(sims)[::-1]
        results: List[Dict[str, Any]] = []
        for idx in ranked_indices[:top_k]:
            score = float(sims[idx])
            if score >= min_similarity:
                art = dict(articles[int(idx)])
                art["similarity_score"] = round(score, 3)
                results.append(art)
        return results

    def process_turn(
        self,
        user: Optional[Dict[str, Any]],
        message: str,
        *,
        simulate_failure: bool = False,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        _ = history
        return self.classify_text(message, simulate_failure=simulate_failure)
