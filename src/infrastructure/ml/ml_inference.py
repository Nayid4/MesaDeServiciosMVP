"""Carga del registro de modelos, selección activa e inferencia calibrada."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

from src.infrastructure.ml.ml_text_normalizer import count_domain_signals

DEFAULT_MODELS_DIR = Path("models")
DEFAULT_REGISTRY_PATH = DEFAULT_MODELS_DIR / "model_registry.json"
MIN_CONFIDENCE_THRESHOLD = 0.60


def load_model_registry(registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> Optional[Dict[str, Any]]:
    path = Path(registry_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_active_model(model_id: str, registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> Dict[str, Any]:
    registry = load_model_registry(registry_path)
    if not registry:
        raise FileNotFoundError("No existe registro de modelos entrenados.")
    valid_ids = {m["model_id"] for m in registry["models"]}
    if model_id not in valid_ids:
        raise ValueError(f"Modelo '{model_id}' no encontrado en el registro.")
    registry["active_model_id"] = model_id
    Path(registry_path).write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return registry


def load_active_classifiers(registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> Dict[str, Any]:
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


def predict_ticket_classification(text: str, loaded_bundle: Dict[str, Any]) -> Dict[str, Any]:
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
        sorted_pairs = sorted(zip(list(service_model.classes_), probs), key=lambda x: -x[1])
        top_probabilities = {str(cls): round(float(prob) * 100.0, 2) for cls, prob in sorted_pairs}
        confidence_pct = round(float(sorted_pairs[0][1]) * 100.0, 2)
        second_pct = round(float(sorted_pairs[1][1]) * 100.0, 2) if len(sorted_pairs) > 1 else 0.0
    else:
        second_pct = 0.0

    signal_count = count_domain_signals(cleaned_text)
    if signal_count == 0:
        confidence_pct = round(min(confidence_pct * 0.45, 55.0), 2)
    elif signal_count == 1 and (confidence_pct - second_pct) < 12.0 and confidence_pct < 65.0:
        confidence_pct = round(min(confidence_pct, 58.0), 2)

    pred_urgency = str(urgency_model.predict([cleaned_text])[0]) if urgency_model is not None else "Media"
    threshold_pct = MIN_CONFIDENCE_THRESHOLD * 100.0
    return {
        "predicted_service": pred_service,
        "predicted_urgency": pred_urgency,
        "confidence": round(confidence_pct / 100.0, 4),
        "confidence_pct": confidence_pct,
        "is_low_confidence": bool(confidence_pct < threshold_pct),
        "min_confidence_threshold": MIN_CONFIDENCE_THRESHOLD,
        "domain_signal_count": signal_count,
        "probabilities": top_probabilities,
        "model_id": meta["model_id"],
        "model_name": meta["display_name"],
    }


def predict_all_models_side_by_side(
    text: str, registry_path: Path | str = DEFAULT_REGISTRY_PATH
) -> List[Dict[str, Any]]:
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
            ordered = sorted(zip(list(pipe.classes_), probs), key=lambda x: -x[1])
            probs_dict = {str(c): round(float(p) * 100.0, 2) for c, p in ordered}
            conf_pct = round(float(np.max(probs)) * 100.0, 2)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
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
                "top_3_probabilities": [
                    {"service": svc, "probability_pct": prob}
                    for svc, prob in list(probs_dict.items())[:3]
                ],
            }
        )
    return results
