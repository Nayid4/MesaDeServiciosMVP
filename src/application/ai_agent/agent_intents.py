"""Intenciones conversacionales, palabras clave y constructor de tarjetas del Agente IA."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.domain.rules import (
    UPC_SERVICE_CATALOG,
    calculate_priority_or03,
)
from src.infrastructure.ml.ai_engine import TICKET_ID_REGEX, strip_accents_lower

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

OUT_OF_SCOPE_KEYWORDS = (
    "receta", "cocina", "cocinar", "partido de futbol", "futbol", "horoscopo",
    "chiste", "clima de hoy", "pronostico del clima", "novela", "loteria",
    "apuesta", "pelicula", "cancion", "capital de francia", "netflix",
    "astrologia", "poema", "receta de arroz",
)

GREETING_TERMS = {
    "hola", "buenos dias", "buenas tardes", "buenas noches",
    "saludos", "que tal", "buen dia", "hey", "hi",
}

FAREWELL_TERMS = (
    "muchas gracias", "mil gracias", "gracias", "hasta luego",
    "nos vemos", "chao", "adios", "eso era todo", "todo claro", "feliz dia",
)

DRAFT_TICKET_TERMS = (
    "crear ticket", "crear un ticket", "abrir ticket", "abrir un ticket",
    "radicar ticket", "radicar un ticket", "registrar ticket", "generar ticket",
    "enviar tecnico", "necesito un tecnico", "mandar tecnico", "escalar caso",
)


def is_already_introduced(history: Optional[List[Dict[str, str]]]) -> bool:
    if not history:
        return False
    for item in history:
        if item.get("role") == "assistant" and "CASAGBI Agent" in str(item.get("content") or ""):
            return True
    return len([h for h in history if h.get("role") == "assistant"]) > 0


def is_pure_conversational_chatter(text: str) -> bool:
    norm = strip_accents_lower(text)
    if TICKET_ID_REGEX.search(text):
        return False
    if any(norm == g or norm.startswith(g + " ") or norm.startswith(g + ",") for g in GREETING_TERMS) and len(norm.split()) <= 4:
        return True
    if any(f in norm for f in FAREWELL_TERMS) and len(norm.split()) <= 7:
        return True
    return any(
        p in norm
        for p in (
            "que es casagbi", "quien eres", "como funciona casagbi", "horarios",
            "sedes de casagbi", "matriz or-03", "como funciona or-03",
        )
    )


def collect_incident_context(query: str, history: Optional[List[Dict[str, str]]]) -> str:
    chunks: List[str] = []
    if history:
        user_msgs = [
            str(m.get("content") or "").strip()
            for m in history[-8:]
            if m.get("role") == "user" and str(m.get("content") or "").strip()
        ]
        for prev in user_msgs:
            if prev != query.strip() and not is_pure_conversational_chatter(prev):
                chunks.append(prev)
    chunks.append(query.strip())
    return " | ".join(chunks)


def handle_conversational_domain(
    query: str, user: Dict[str, Any], already_introduced: bool
) -> Optional[Dict[str, Any]]:
    norm = strip_accents_lower(query)
    words = norm.split()
    if any(f in norm for f in FAREWELL_TERMS) and len(words) <= 8 and not TICKET_ID_REGEX.search(query):
        return {
            "status": "conversational",
            "tool_invoked": "conversational_domain",
            "reply": (
                "Con gusto. Si necesitas reportar otra falla más adelante o prefieres atención directa, "
                "puedes usar el botón **Hablar con una persona** en cualquier momento. Que tengas excelente jornada en la UPC."
            ),
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
        }

    asks_identity = any(
        p in norm for p in ("que es casagbi", "quien eres", "como funciona", "que haces", "ayuda general")
    )
    has_incident_terms = any(
        p in norm
        for p in (
            "falla", "no enciende", "no prende", "no conecta", "no da", "error",
            "sin conexion", "sin internet", "sin red", "caido", "danado", "proyector",
            "computador", "computadora", "pc", "wifi", "vpn", "vortal", "aula web",
            "correo", "impresora", "software", "licencia", "switch",
            "abrir ticket", "abrir un ticket", "crear ticket", "crear un ticket",
        )
    )
    asks_schedule_sedes = (
        any(
            p in norm
            for p in (
                "horario", "horarios", "que sedes", "cuales sedes",
                "sedes atiende", "sedes de casagbi", "donde atienden", "que campus",
            )
        )
        and not has_incident_terms
    )
    asks_sla_or03 = (
        any(p in norm for p in ("or-03", "matriz de prioridad", "tiempos sla", "prioridades", "cuanto demora", "tiempo de respuesta", "sla"))
        and not has_incident_terms
    )
    if asks_identity or asks_schedule_sedes or asks_sla_or03:
        parts = ["**Información Institucional — Mesa de Servicios TIC CASAGBI (ITIL v4)**"]
        if asks_identity or not (asks_schedule_sedes or asks_sla_or03):
            parts.append(
                "CASAGBI es el **Punto Único de Contacto (SPOC)** de la UPC para centralizar incidentes y solicitudes TIC bajo ITIL v4."
            )
        if asks_schedule_sedes or asks_identity:
            parts.append(
                "**Horarios hábiles (OR-04):** Lunes a Viernes de `7:00 a.m. a 7:00 p.m.` y Sábados de `8:00 a.m. a 12:00 m.`\n"
                "**Sedes:** Sabanas (Valledupar), Hurtado (Valledupar) y Seccional Aguachica."
            )
        if asks_sla_or03 or asks_identity:
            parts.append(
                "**Matriz OR-03 (Impacto × Urgencia) y SLA:** P1 Crítica (`0.5h` / `4h`), P2 Alta (`1h` / `8h`), P3 Media (`4h` / `24h`), P4 Baja (`8h` / `40h`). "
                "La prioridad siempre se calcula de forma determinista con la matriz OR-03."
            )
        return {
            "status": "conversational",
            "tool_invoked": "conversational_domain",
            "reply": "\n\n".join(parts),
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
        }

    is_greeting = any(norm == g or norm.startswith(g + " ") or norm.startswith(g + ",") for g in GREETING_TERMS)
    if (
        is_greeting
        and len(words) <= 6
        and not any(t in norm for t in ("error", "falla", "no ", "wifi", "vortal", "correo", "proyector", "ticket", "computador", "pc"))
    ):
        intro_line = (
            f"Hola, **{user.get('full_name', 'integrante UPC')}**. En qué falla o consulta TIC puedo apoyarte ahora?"
            if already_introduced
            else (
                f"Hola, **{user.get('full_name', 'integrante UPC')}**. Soy **CASAGBI Agent**, el asistente "
                "inteligente con IA (Nivel 0) de la Mesa de Servicios TIC de la Universidad Popular del Cesar.\n\n"
                "Puedo ayudarte con:\n"
                "- **Guías oficiales KB** (equipos de cómputo, Wi-Fi Eduroam, Vortal, Aula Web, correo `@unicesar.edu.co`, aulas y software).\n"
                "- **Consulta de radicados** (`MS-CAT-AAAA-NNNNNN` y alias `MS-AAAA-NNNNNN`) y semáforo SLA.\n"
                "- **Pre-radicación guiada editable** (confirmando sede, ubicación exacta y urgencia)."
            )
        )
        return {
            "status": "conversational",
            "tool_invoked": "conversational_domain",
            "reply": intro_line,
            "matched_articles": [],
            "prediction": None,
            "draft_card": None,
        }
    return None


def build_agent_draft_card(
    *,
    description_text: str,
    title_text: str,
    user: Dict[str, Any],
    service_name: str,
    confidence_pct: float,
    model_name: str,
    sede: str,
    location: str,
    urgency: str,
    sla_table: Dict[str, Dict[str, float]],
    cited_kb_code: Optional[str] = None,
    urgency_needs_confirmation: bool = False,
) -> Dict[str, Any]:
    svc = service_name if service_name in UPC_SERVICE_CATALOG else list(UPC_SERVICE_CATALOG.keys())[0]
    svc_meta = UPC_SERVICE_CATALOG[svc]
    prio = calculate_priority_or03(svc_meta["base_impact"], urgency, custom_sla_table=sla_table or None)
    clean_title = title_text.strip()
    if len(clean_title) < 5:
        clean_title = f"Soporte {svc}"
    clean_desc = description_text.strip()
    if len(clean_desc) < 15:
        clean_desc = f"{clean_desc} — Reportado vía Agente IA CASAGBI.".strip()
    return {
        "title": clean_title[:75] if len(clean_title) <= 75 else clean_title[:72] + "...",
        "description": clean_desc,
        "service_name": svc,
        "ticket_type": svc_meta.get("default_type", "Incidencia"),
        "area": svc_meta["area"],
        "impact": prio["impact"],
        "urgency": prio["urgency"],
        "priority": prio["priority"],
        "sla_resolution_hours": prio["sla_resolution_hours"],
        "sede": sede,
        "location": location,
        "confidence_pct": round(float(confidence_pct), 2),
        "model_name": model_name,
        "cited_kb_code": cited_kb_code,
        "editable": True,
        "urgency_needs_confirmation": urgency_needs_confirmation,
        "requires_auth": user.get("role") == "public",
    }
