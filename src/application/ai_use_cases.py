"""Casos de uso de Inteligencia Artificial y Agente Conversacional con Herramientas (OCP Strategy)."""

from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.cleaning import clean_tickets_dataset
from src.domain.repositories import (
    IAuditRepository,
    ICatalogRepository,
    IKnowledgeRepository,
    ITicketRepository,
)
from src.domain.rules import (
    UPC_LOCATIONS,
    UPC_SEDES,
    UPC_SERVICE_CATALOG,
    calculate_priority_or03,
    calculate_sla_status,
)
from src.infrastructure.dataset_generator import generate_synthetic_dataset
from src.infrastructure.ml_pipeline import (
    DEFAULT_REGISTRY_PATH,
    load_active_classifiers,
    load_model_registry,
    predict_all_models_side_by_side,
    predict_ticket_classification,
    set_active_model,
    train_and_evaluate_models,
)
from src.infrastructure.sqlite_repositories import (
    SQLiteAuditLogRepository,
    SQLiteCatalogRepository,
    SQLiteKnowledgeBaseRepository,
    SQLiteTicketRepository,
)

TICKET_ID_REGEX = re.compile(r"MS-\d{4}-\d{6}", re.IGNORECASE)

OUT_OF_SCOPE_KEYWORDS = (
    "receta",
    "cocina",
    "partido de futbol",
    "horoscopo",
    "chiste",
    "clima de hoy",
    "novela",
    "loteria",
    "apuesta",
)

SPANISH_STOPWORDS = [
    "a", "al", "algo", "como", "con", "cual", "de", "del", "el", "en", "es", "esta",
    "este", "esto", "la", "las", "lo", "los", "me", "mi", "mis", "no", "o", "para",
    "pero", "por", "que", "se", "si", "sin", "su", "sus", "te", "tengo", "tu", "un",
    "una", "uno", "y", "ya",
]

GREETING_TERMS = {
    "hola",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "saludos",
    "que tal",
    "buen dia",
    "hey",
    "hi",
}

ESCALATE_TERMS = (
    "hablar con un humano",
    "hablar con una persona",
    "transferir a un tecnico",
    "transferir a tecnico",
    "asesor humano",
    "agente humano",
    "escalar caso",
    "atencion humana",
)

DRAFT_TICKET_TERMS = (
    "crear ticket",
    "crear un ticket",
    "abrir ticket",
    "abrir un ticket",
    "radicar ticket",
    "radicar un ticket",
    "registrar ticket",
    "generar ticket",
    "enviar tecnico",
    "necesito un tecnico",
    "mandar tecnico",
)


def _norm_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def extract_campus_entities(text: str, user_default_sede: Optional[str] = None) -> Dict[str, str]:
    """Extrae sede y ubicación física UPC mediante reglas determinísticas sobre lenguaje natural."""
    norm = _norm_text(text)

    sede = user_default_sede if user_default_sede in UPC_SEDES else UPC_SEDES[0]
    if "aguachica" in norm:
        sede = "Seccional Aguachica"
    elif "hurtado" in norm:
        sede = "Sede Hurtado (Valledupar)"
    elif "sabana" in norm:
        sede = "Sede Sabanas (Valledupar)"

    location = UPC_LOCATIONS[0]
    location_rules = [
        ("bloque a", "Bloque A"),
        ("bloque b", "Bloque B"),
        ("bloque c", "Bloque C"),
        ("bloque d", "Bloque D"),
        ("laboratorio", "Laboratorios de Cómputo"),
        ("sala de computo", "Laboratorios de Cómputo"),
        ("biblioteca", "Biblioteca"),
        ("administrativo", "Edificio Administrativo"),
        ("rectoria", "Edificio Administrativo"),
        ("admisiones", "Edificio Administrativo"),
    ]
    for pattern, canonical in location_rules:
        if pattern in norm:
            location = canonical
            break

    return {"sede": sede, "location": location}


class AIServiceUnavailableError(RuntimeError):
    """Error controlado cuando el motor de IA está apagado o en simulación de falla (RNF-06)."""


class AgentTool(ABC):
    """Contrato OCP para herramientas ejecutables por el CASAGBI Agent."""

    name: str
    description: str

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


class SearchKnowledgeBaseTool(AgentTool):
    """Herramienta 1: Recuperación semántica local TF-IDF sobre artículos públicos aprobados."""

    name = "search_knowledge_base"
    description = "Busca soluciones oficiales en kb_articles usando TF-IDF y similitud coseno."

    def __init__(self, kb_repo: IKnowledgeRepository):
        self.kb_repo = kb_repo

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.25,
        service_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        articles = self.kb_repo.list_articles(
            visibility="Pública",
            status="Publicado",
            service_name=service_filter,
        )
        if not articles or not query or not query.strip():
            return []

        corpus = [
            f"{a['title']} {a['title']} {a['keywords']} {a['keywords']} {a['symptoms']} {a['service_name']}"
            for a in articles
        ]
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 1),
            lowercase=True,
            strip_accents="unicode",
            stop_words=SPANISH_STOPWORDS,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(corpus + [query.strip()])
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

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context["query"]
        top_k = int(context.get("top_k", 2))
        min_similarity = float(context.get("min_similarity", 0.25))
        matches = self.search(query=query, top_k=top_k, min_similarity=min_similarity)
        return {"tool_name": self.name, "matches": matches}


class CheckTicketStatusTool(AgentTool):
    """Herramienta 2: Consulta en tiempo real del estado, prioridad y SLA de un ticket."""

    name = "check_ticket_status"
    description = "Consulta en SQLite el estado de un radicado MS-AAAA-NNNNNN o lista tickets recientes."

    def __init__(self, ticket_repo: ITicketRepository):
        self.ticket_repo = ticket_repo

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context["query"]
        user = context["user"]
        ticket_match = TICKET_ID_REGEX.search(query)

        if user.get("role") == "public":
            return {
                "status": "ok",
                "tool_invoked": self.name,
                "reply": (
                    "Para consultar el detalle y técnico asignado de tus tickets debes iniciar sesión con tu "
                    "cuenta `@unicesar.edu.co`. Si deseas una vista rápida pública, usa el buscador de radicado a la izquierda."
                ),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": False,
                "prefill": None,
                "draft_card": None,
            }

        if ticket_match:
            num = ticket_match.group(0).upper()
            t = self.ticket_repo.get_by_number(num)
            if not t or (user["role"] == "usuario" and t["requester_id"] != user["id"]):
                return {
                    "status": "ok",
                    "tool_invoked": self.name,
                    "reply": (
                        f"No encontré un ticket autorizado con el radicado **{num}**. "
                        "Por control RBAC solo puedo consultar tus propios radicados o los asignados a tu rol."
                    ),
                    "matched_articles": [],
                    "prediction": None,
                    "should_offer_ticket": False,
                    "prefill": None,
                    "draft_card": None,
                }
            sla = calculate_sla_status(t)
            return {
                "status": "ok",
                "tool_invoked": self.name,
                "reply": (
                    f"**Estado del ticket {t['ticket_number']}**\n\n"
                    f"- **Asunto:** {t['title']}\n"
                    f"- **Servicio / Área:** {t['service_name']} ({t['area']})\n"
                    f"- **Estado actual:** `{t['status']}`\n"
                    f"- **Prioridad OR-03:** `{t['priority']}`\n"
                    f"- **Técnico asignado:** {t.get('assigned_tech_email') or 'En cola de coordinación'}\n"
                    f"- **Semáforo SLA:** **{sla['semaphore']}** — {sla['label']}\n"
                    f"- **Fecha límite resolución:** {str(t.get('resolution_deadline', ''))[:16].replace('T', ' ')}"
                ),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": False,
                "prefill": None,
                "draft_card": None,
            }

        if user["role"] == "tecnico":
            own = self.ticket_repo.list_tickets(assigned_tech_id=user["id"], limit=5)
        elif user["role"] in ("coordinador", "admin", "director"):
            own = self.ticket_repo.list_tickets(limit=5)
        else:
            own = self.ticket_repo.list_tickets(requester_id=user["id"], limit=5)

        if not own:
            return {
                "status": "ok",
                "tool_invoked": self.name,
                "reply": "Aún no tienes tickets registrados en CASAGBI. Describe tu caso si deseas crear uno nuevo.",
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": True,
                "prefill": None,
                "draft_card": None,
            }

        lines = "\n".join(
            f"- **{t['ticket_number']}** | {t['title']} — Estado: `{t['status']}` | {t['priority']} | SLA: {calculate_sla_status(t)['label']}"
            for t in own
        )
        return {
            "status": "ok",
            "tool_invoked": self.name,
            "reply": f"Estos son los tickets más recientes asociados a tu perfil:\n\n{lines}",
            "matched_articles": [],
            "prediction": None,
            "should_offer_ticket": False,
            "prefill": None,
            "draft_card": None,
        }


class ClassifyAndDraftTicketTool(AgentTool):
    """Herramienta 3: Clasificación ML + extracción de entidades UPC + borrador interactivo."""

    name = "classify_and_draft_ticket"
    description = "Predice servicio, área, impacto, urgencia y prioridad OR-03 y extrae sede/bloque."

    def __init__(self, classifier_fn: Any, sla_provider: Any):
        self._classifier_fn = classifier_fn
        self._sla_provider = sla_provider

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context["query"]
        user = context["user"]
        prediction: Optional[Dict[str, Any]] = None
        try:
            prediction = self._classifier_fn(query, query, simulate_failure=False)
        except Exception:
            prediction = None

        fallback_service = context.get("fallback_service") or list(UPC_SERVICE_CATALOG.keys())[0]
        svc = prediction["predicted_service"] if prediction else fallback_service
        if svc not in UPC_SERVICE_CATALOG:
            svc = list(UPC_SERVICE_CATALOG.keys())[0]

        svc_meta = UPC_SERVICE_CATALOG[svc]
        urgency = prediction["predicted_urgency"] if prediction else "Media"
        sla_table = self._sla_provider() or None
        prio = calculate_priority_or03(svc_meta["base_impact"], urgency, custom_sla_table=sla_table)
        entities = extract_campus_entities(query, user_default_sede=user.get("sede"))

        prefill = {
            "title": query[:75] if len(query) <= 75 else query[:72] + "...",
            "description": query,
            "service_name": svc,
            "urgency": prio["urgency"],
            "sede": entities["sede"],
            "location": entities["location"],
            "ai_confidence": prediction["confidence_pct"] if prediction else 0.0,
        }
        draft_card = {
            "title": prefill["title"],
            "description": query,
            "service_name": svc,
            "ticket_type": svc_meta.get("default_type", "Incidencia"),
            "area": svc_meta["area"],
            "impact": prio["impact"],
            "urgency": prio["urgency"],
            "priority": prio["priority"],
            "sla_resolution_hours": prio["sla_resolution_hours"],
            "sede": entities["sede"],
            "location": entities["location"],
            "confidence_pct": prediction["confidence_pct"] if prediction else 0.0,
            "model_name": prediction["model_name"] if prediction else "Catálogo base",
        }
        return {
            "tool_name": self.name,
            "prediction": prediction,
            "prefill": prefill,
            "draft_card": draft_card,
        }


class EscalateToHumanTool(AgentTool):
    """Herramienta 4: Escalado directo a técnico humano con historial de conversación."""

    name = "escalate_to_human"
    description = "Convierte la sesión activa del agente en un ticket asignado a un técnico humano."

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user = context["user"]
        messages: List[Dict[str, Any]] = context.get("conversation_history") or []
        draft: Dict[str, Any] = context.get("draft_card") or {}
        ticket_service = context["ticket_service"]

        user_turns = [m["content"] for m in messages if m.get("role") == "user"]
        combined_desc = "\n".join(user_turns).strip()
        if not combined_desc or len(combined_desc) < 15:
            combined_desc = (
                f"Solicitud escalada desde CASAGBI Agent por {user.get('full_name', user['email'])}. "
                "El usuario solicita atención directa con un técnico de soporte."
            )

        transcript = "\n".join(
            f"{str(m.get('role', 'user')).upper()}: {m.get('content', '')}" for m in messages
        )
        title = draft.get("title") or (user_turns[-1][:72] if user_turns else "Escalado desde Agente IA CASAGBI")
        if len(title.strip()) < 5:
            title = "Atención escalada desde Agente IA"

        service_name = draft.get("service_name") or list(UPC_SERVICE_CATALOG.keys())[0]
        if service_name not in UPC_SERVICE_CATALOG:
            service_name = list(UPC_SERVICE_CATALOG.keys())[0]

        urgency = draft.get("urgency") or "Alta"
        sede = draft.get("sede") or user.get("sede") or UPC_SEDES[0]
        location = draft.get("location") or UPC_LOCATIONS[0]

        created = ticket_service.create_ticket(
            requester=user,
            title=title,
            description=combined_desc,
            ticket_type=UPC_SERVICE_CATALOG[service_name]["default_type"],
            service_name=service_name,
            sede=sede,
            location=location,
            urgency=urgency,
            ai_suggested_service=draft.get("service_name"),
            ai_confidence=draft.get("confidence_pct"),
            ai_human_validated=True,
            initial_transcript=transcript or None,
        )
        return {
            "tool_name": self.name,
            "ticket": created,
        }


class AIService:
    """Orquesta CASAGBI Agent (enrutador híbrido + 4 herramientas), inferencia NLP y MLOps."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
        kb_repo: Optional[IKnowledgeRepository] = None,
        ticket_repo: Optional[ITicketRepository] = None,
        audit_repo: Optional[IAuditRepository] = None,
        catalog_repo: Optional[ICatalogRepository] = None,
    ):
        self.db_path = db_path
        self.registry_path = Path(registry_path)
        self.kb_repo: IKnowledgeRepository = kb_repo or SQLiteKnowledgeBaseRepository(db_path)
        self.ticket_repo: ITicketRepository = ticket_repo or SQLiteTicketRepository(db_path)
        self.audit_repo: IAuditRepository = audit_repo or SQLiteAuditLogRepository(db_path)
        self.catalog_repo: ICatalogRepository = catalog_repo or SQLiteCatalogRepository(db_path)
        self._cached_bundle: Optional[Dict[str, Any]] = None

        self.kb_tool = SearchKnowledgeBaseTool(self.kb_repo)
        self.ticket_status_tool = CheckTicketStatusTool(self.ticket_repo)
        self.classify_draft_tool = ClassifyAndDraftTicketTool(
            classifier_fn=self.classify_ticket_text,
            sla_provider=self.catalog_repo.get_sla_table,
        )
        self.escalate_tool = EscalateToHumanTool()
        self.tools: Dict[str, AgentTool] = {
            self.kb_tool.name: self.kb_tool,
            self.ticket_status_tool.name: self.ticket_status_tool,
            self.classify_draft_tool.name: self.classify_draft_tool,
            self.escalate_tool.name: self.escalate_tool,
        }

    def _get_bundle(self) -> Dict[str, Any]:
        if self._cached_bundle is None:
            self._cached_bundle = load_active_classifiers(self.registry_path)
        return self._cached_bundle

    def invalidate_model_cache(self) -> None:
        self._cached_bundle = None

    def classify_ticket_text(
        self,
        subject: str,
        description: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        if simulate_failure:
            raise AIServiceUnavailableError(
                "El motor de Inteligencia Artificial no está disponible en este momento (Simulación RNF-06). "
                "Puede continuar registrando su ticket manualmente sin pérdida de datos."
            )
        text = f"{subject or ''} | {description or ''}".strip()
        bundle = self._get_bundle()
        return predict_ticket_classification(text, bundle)

    def predict_side_by_side(self, text: str) -> List[Dict[str, Any]]:
        """Ejecuta inferencia simultánea en los 4 modelos registrados para el simulador MLOps."""
        return predict_all_models_side_by_side(text, registry_path=self.registry_path)

    def search_knowledge_base(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.25,
        service_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.kb_tool.search(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
            service_filter=service_filter,
        )

    def _handle_conversational_domain(self, query: str, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        norm = _norm_text(query)
        words = norm.split()

        # Saludo puro o corto sin descripción de falla técnica
        is_greeting = any(norm == g or norm.startswith(g + " ") or norm.startswith(g + ",") for g in GREETING_TERMS)
        if is_greeting and len(words) <= 6 and not any(t in norm for t in ("error", "falla", "no ", "wifi", "vortal", "correo", "proyector", "ticket")):
            return {
                "status": "conversational",
                "tool_invoked": "conversational_domain",
                "reply": (
                    f"Hola, **{user.get('full_name', 'integrante UPC')}**. Soy **CASAGBI Agent**, el asistente conversacional "
                    "de la Mesa de Servicios TIC de la Universidad Popular del Cesar.\n\n"
                    "Puedo ayudarte con:\n"
                    "- **Guías oficiales Nivel 0** (Wi-Fi Eduroam, Vortal, Aula Web, correo `@unicesar.edu.co`).\n"
                    "- **Consulta de radicados** (`MS-2026-NNNNNN`) y semáforo SLA en vivo.\n"
                    "- **Diagnóstico y pre-radicación guiada** de incidentes mediante clasificación IA.\n\n"
                    "Cuéntame qué necesitas hoy."
                ),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": False,
                "prefill": None,
                "draft_card": None,
            }

        # Preguntas sobre CASAGBI, horarios, sedes y matriz OR-03
        asks_identity = any(p in norm for p in ("que es casagbi", "quien eres", "como funciona", "que haces", "ayuda general"))
        asks_schedule_sedes = any(p in norm for p in ("horario", "horarios", "atencion", "sedes", "campus", "aguachica", "hurtado", "sabanas")) and not any(
            p in norm for p in ("falla", "no enciende", "no conecta", "error", "sin conexion", "caido", "danado", "proyector", "wifi")
        )
        asks_sla_or03 = any(p in norm for p in ("or-03", "matriz de prioridad", "tiempos sla", "prioridades", "cuanto demora", "tiempo de respuesta"))

        if asks_identity or asks_schedule_sedes or asks_sla_or03:
            reply_parts = [
                "**Información Institucional — Mesa de Servicios TIC CASAGBI (ITIL v4)**"
            ]
            if asks_identity or not (asks_schedule_sedes or asks_sla_or03):
                reply_parts.append(
                    "CASAGBI es el **Punto Único de Contacto (SPOC)** de la Universidad Popular del Cesar para "
                    "centralizar incidentes y solicitudes TIC bajo buenas prácticas ITIL v4 e Inteligencia Artificial propia."
                )
            if asks_schedule_sedes or asks_identity:
                reply_parts.append(
                    "**Horarios hábiles de atención (Regla OR-04):** Lunes a Viernes de `7:00 a.m. a 7:00 p.m.` "
                    "y Sábados de `8:00 a.m. a 12:00 m.` (zona América/Bogotá).\n"
                    "**Cobertura institucional:** Sede Sabanas (Valledupar), Sede Hurtado (Valledupar) y Seccional Aguachica."
                )
            if asks_sla_or03 or asks_identity:
                reply_parts.append(
                    "**Matriz de Priorización OR-03 (Impacto x Urgencia) y SLA de Resolución:**\n"
                    "- **P1 Crítica:** Respuesta `0.5 h` | Resolución `4 h` hábiles\n"
                    "- **P2 Alta:** Respuesta `1 h` | Resolución `8 h` hábiles\n"
                    "- **P3 Media:** Respuesta `4 h` | Resolución `24 h` hábiles\n"
                    "- **P4 Baja:** Respuesta `8 h` | Resolución `40 h` hábiles"
                )
            return {
                "status": "conversational",
                "tool_invoked": "conversational_domain",
                "reply": "\n\n".join(reply_parts),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": False,
                "prefill": None,
                "draft_card": None,
            }

        return None

    def process_assistant_message(
        self,
        user: Dict[str, Any],
        message_text: str,
        failed_attempts: int = 0,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        """
        Enrutador Híbrido del CASAGBI Agent (TF-IDF + Similitud Coseno + Extracción Regex/Reglas):
        Orquesta las 4 herramientas del dominio UPC respetando RNF-06 y RNF-13.
        """
        query = (message_text or "").strip()
        if not query:
            raise ValueError("Escriba una consulta para el asistente virtual.")

        # 0. Simulación de indisponibilidad controlada (RNF-06)
        if simulate_failure:
            entities = extract_campus_entities(query, user_default_sede=user.get("sede"))
            return {
                "status": "ai_unavailable",
                "tool_invoked": "fallback_contingency",
                "reply": (
                    "**Servicio de IA temporalmente no disponible (RNF-06).**\n\n"
                    "No se preocupe: su descripción ha sido conservada íntegramente. "
                    "Puede usar la tarjeta inferior o ir al formulario manual para radicar su ticket sin pérdida de datos."
                ),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": True,
                "prefill": {
                    "title": query[:80],
                    "description": query,
                    "service_name": list(UPC_SERVICE_CATALOG.keys())[0],
                    "urgency": "Media",
                    "sede": entities["sede"],
                    "location": entities["location"],
                },
                "draft_card": None,
            }

        # 1. Guardrail de seguridad: rechazar consultas fuera del alcance TIC (RNF-13)
        norm = _norm_text(query)
        if any(bad in norm for bad in OUT_OF_SCOPE_KEYWORDS):
            return {
                "status": "out_of_scope",
                "tool_invoked": "safety_guardrail",
                "reply": (
                    "Soy **CASAGBI Agent**, el asistente oficial de la **Mesa de Servicios TIC de la UPC**. "
                    "Únicamente estoy autorizado para responder sobre tecnología universitaria: Wi-Fi Eduroam, "
                    "Vortal, Aula Web, correo `@unicesar.edu.co`, aulas inteligentes, equipos y software académico."
                ),
                "matched_articles": [],
                "prediction": None,
                "should_offer_ticket": False,
                "prefill": None,
                "draft_card": None,
            }

        # 2. Herramienta 2: Consulta de estado de ticket (MS-AAAA-NNNNNN o "mis tickets")
        ticket_match = TICKET_ID_REGEX.search(query)
        asks_ticket_status = any(
            kw in norm
            for kw in (
                "mis tickets",
                "estado de mi ticket",
                "estado del ticket",
                "estado ticket",
                "como va mi caso",
                "como va mi ticket",
                "consultar radicado",
                "radicado ms-",
            )
        )
        if ticket_match or asks_ticket_status:
            return self.ticket_status_tool.execute({"query": query, "user": user})

        # 3. Solicitud explícita de transferencia humana
        if any(esc in norm for esc in ESCALATE_TERMS):
            draft_res = self.classify_draft_tool.execute({"query": query, "user": user})
            return {
                "status": "no_kb_match",
                "tool_invoked": "escalate_to_human",
                "reply": (
                    "Entendido. He preparado la transferencia directa hacia un técnico humano con el resumen "
                    "clasificado de tu caso. Haz clic en **'Confirmar y Radicar Ticket'** en la tarjeta inferior "
                    "o pulsa **'Transferir a un Técnico Humano'** en la barra superior."
                ),
                "matched_articles": [],
                "prediction": draft_res["prediction"],
                "should_offer_ticket": True,
                "prefill": draft_res["prefill"],
                "draft_card": draft_res["draft_card"],
            }

        # 4. Comprensión conversacional natural del dominio UPC (saludos, horarios, sedes, SLA)
        conv_res = self._handle_conversational_domain(query, user)
        if conv_res is not None:
            return conv_res

        # 5. Evaluar si el usuario pide redactar/abrir ticket directamente o consultar KB primero
        wants_direct_draft = any(kw in norm for kw in DRAFT_TICKET_TERMS)

        # Ejecutar Tool 1 (KB Search) si no pidió exclusivamente abrir ticket
        matches: List[Dict[str, Any]] = []
        if not wants_direct_draft:
            kb_res = self.kb_tool.execute({"query": query, "top_k": 2, "min_similarity": 0.25})
            matches = kb_res["matches"]

        # Ejecutar Tool 3 (Clasificación ML + Borrador con entidades)
        fallback_svc = matches[0]["service_name"] if matches else list(UPC_SERVICE_CATALOG.keys())[0]
        draft_res = self.classify_draft_tool.execute(
            {"query": query, "user": user, "fallback_service": fallback_svc}
        )
        prediction = draft_res["prediction"]
        prefill = draft_res["prefill"]
        draft_card = draft_res["draft_card"]

        if matches:
            top = matches[0]
            conf_txt = (
                f" | Servicio estimado por IA: **{draft_card['service_name']}** ({draft_card['confidence_pct']}%)"
                if prediction
                else ""
            )
            reply = (
                f"Encontré una guía oficial en la Base de Conocimiento que puede resolver tu consulta:\n\n"
                f"**[{top['code']}] {top['title']}** *(Similitud: {top['similarity_score']:.2f}{conf_txt})*\n\n"
                f"**Pasos recomendados:**\n{top['solution_steps']}\n\n"
                "¿Esta guía resolvió tu inconveniente? Si el problema continúa, puedo generar el ticket pre-clasificado por ti."
            )
            return {
                "status": "kb_matched",
                "tool_invoked": "search_knowledge_base",
                "reply": reply,
                "matched_articles": matches,
                "prediction": prediction,
                "should_offer_ticket": failed_attempts >= 1,
                "prefill": prefill,
                "draft_card": draft_card,
            }

        # Sin coincidencia >= 0.25 o solicitud explícita de ticket -> Tool 3 devuelve borrador estructurado
        reason_intro = (
            "He analizado tu solicitud con nuestro clasificador NLP para preparar el borrador del ticket."
            if wants_direct_draft
            else (
                "No encontré un artículo oficial en la Base de Conocimiento con suficiente certeza automática "
                "(similitud < 0.25), por lo que prefiero no improvisar."
            )
        )
        return {
            "status": "no_kb_match",
            "tool_invoked": "classify_and_draft_ticket",
            "reply": (
                f"{reason_intro}\n\n"
                f"Diagnostiqué el caso como **{draft_card['service_name']}** "
                f"(Área: **{draft_card['area']}**, Prioridad **OR-03 {draft_card['priority']}**, "
                f"Sede detectada: **{draft_card['sede']}** — {draft_card['location']}). "
                "Revisa la tarjeta de confirmación debajo para radicarlo en 1 clic con la transcripción adjunta."
            ),
            "matched_articles": [],
            "prediction": prediction,
            "should_offer_ticket": True,
            "prefill": prefill,
            "draft_card": draft_card,
        }

    def escalate_to_human(
        self,
        user: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        draft_card: Optional[Dict[str, Any]],
        ticket_service: Any,
    ) -> Dict[str, Any]:
        """Ejecuta Tool 4 (escalate_to_human) creando un ticket real con la transcripción completa."""
        return self.escalate_tool.execute(
            {
                "user": user,
                "conversation_history": conversation_history,
                "draft_card": draft_card or {},
                "ticket_service": ticket_service,
            }
        )

    # --- Operaciones MLOps para Laboratorio de IA ---
    def get_registry(self) -> Optional[Dict[str, Any]]:
        return load_model_registry(self.registry_path)

    def run_full_retraining_pipeline(
        self,
        actor_email: str,
        n_rows: int = 18000,
    ) -> Dict[str, Any]:
        raw_df = generate_synthetic_dataset(n_rows=n_rows)
        clean_df, excluded_df, clean_stats = clean_tickets_dataset()
        registry = train_and_evaluate_models()
        self.invalidate_model_cache()
        self.audit_repo.append(
            {
                "user_email": actor_email,
                "ip_address": "127.0.0.1",
                "action": "ML_PIPELINE_RETRAINED",
                "entity": "ml_model",
                "entity_id": registry["active_model_id"],
                "new_value": f"Raw={len(raw_df)}, Clean={len(clean_df)}, Excluded={len(excluded_df)}",
            }
        )
        return {"clean_stats": clean_stats, "registry": registry}

    def activate_model(self, actor_email: str, model_id: str) -> Dict[str, Any]:
        old_reg = load_model_registry(self.registry_path)
        old_id = old_reg.get("active_model_id") if old_reg else None
        updated = set_active_model(model_id, self.registry_path)
        self.invalidate_model_cache()
        self.audit_repo.append(
            {
                "user_email": actor_email,
                "ip_address": "127.0.0.1",
                "action": "ML_ACTIVE_MODEL_CHANGED",
                "entity": "ml_model",
                "entity_id": model_id,
                "old_value": old_id,
                "new_value": model_id,
            }
        )
        return updated
