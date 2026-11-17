"""Manejador principal CQRS para turnos del Agente IA Nivel 0 CASAGBI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.application.ai_agent.agent_intents import (
    DRAFT_TICKET_TERMS,
    EMAIL_REGEX,
    OUT_OF_SCOPE_KEYWORDS,
    build_agent_draft_card,
    collect_incident_context,
    handle_conversational_domain,
    is_already_introduced,
)
from src.application.ai_agent.agent_ticket_lookup import handle_check_ticket_tool
from src.application.common import Command
from src.domain.exceptions import ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import UPC_LOCATIONS, UPC_SEDES, UPC_SERVICE_CATALOG
from src.infrastructure.ml.ai_engine import (
    MIN_CONFIDENCE_THRESHOLD,
    TICKET_ID_REGEX,
    LocalNLPEngine,
    extract_campus_entities,
    extract_explicit_ticket_entities,
    scrub_pii_for_model,
    strip_accents_lower,
)


def _default_guest_token_factory(**kwargs: Any) -> str:
    from src.infrastructure.security import create_ticket_guest_token

    return create_ticket_guest_token(**kwargs)


@dataclass(frozen=True)
class ProcessAgentTurnCommand(Command):
    user: Optional[Dict[str, Any]]
    message: str
    simulate_failure: bool = False
    failed_attempts: int = 0
    history: Optional[List[Dict[str, str]]] = None
    email: Optional[str] = None
    selected_service: Optional[str] = None
    selected_sede: Optional[str] = None
    selected_location: Optional[str] = None
    selected_urgency: Optional[str] = None
    ip_address: str = "127.0.0.1"


class ProcessAgentTurnCommandHandler:
    """Agente conversacional Nivel 0 con memoria multiturno, umbral >= 0.60, RAG y tools."""

    def __init__(
        self,
        uow_factory: Callable[[], IUnitOfWork],
        ai_engine: LocalNLPEngine,
        guest_token_factory: Optional[Callable[..., str]] = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._ai_engine = ai_engine
        self._guest_token_factory = guest_token_factory or _default_guest_token_factory

    def _fallback_contingency(self, query: str, actor: Dict[str, Any]) -> Dict[str, Any]:
        entities = extract_campus_entities(query, user_default_sede=actor.get("sede"))
        first_svc = list(UPC_SERVICE_CATALOG.keys())[0]
        return {
            "status": "ai_unavailable",
            "tool_invoked": "fallback_contingency",
            "reply": (
                "**Servicio de IA temporalmente no disponible (RNF-06).**\n\n"
                "Tu descripción ha sido preservada íntegramente. Puedes completar el borrador manual o pulsar "
                "**Hablar con una persona** para radicar sin pérdida de datos."
            ),
            "matched_articles": [],
            "prediction": None,
            "draft_card": {
                "title": query[:75] if len(query) <= 75 else query[:72] + "...",
                "description": query if len(query) >= 15 else f"{query} — Radicado en contingencia manual.",
                "service_name": first_svc,
                "ticket_type": "Incidencia",
                "area": UPC_SERVICE_CATALOG[first_svc]["area"],
                "impact": "Alto",
                "urgency": "Media",
                "priority": "P2 Alta",
                "sla_resolution_hours": 8.0,
                "sede": entities["sede"],
                "location": entities["location"],
                "confidence_pct": 0.0,
                "model_name": "Contingencia manual RNF-06",
                "editable": True,
                "requires_auth": actor.get("role") == "public",
            },
        }

    def handle(self, cmd: ProcessAgentTurnCommand) -> Dict[str, Any]:
        query = (cmd.message or "").strip()
        if not query:
            raise ValidationDomainError("Escriba una consulta para el asistente inteligente CASAGBI.")

        actor = cmd.user or {
            "id": 0, "email": "visitante@unicesar.edu.co", "full_name": "Comunidad UPC", "role": "public", "sede": None
        }
        already_introduced = is_already_introduced(cmd.history)
        if cmd.simulate_failure:
            return self._fallback_contingency(query, actor)

        norm = strip_accents_lower(query)
        if any(bad in norm for bad in OUT_OF_SCOPE_KEYWORDS):
            return {
                "status": "out_of_scope",
                "tool_invoked": "safety_guardrail",
                "reply": (
                    "Solo atiendo consultas e incidentes sobre infraestructura, plataformas y servicios TIC institucionales de la UPC. "
                    "Si tienes un problema técnico, indícamelo o usa **Hablar con una persona**."
                ),
                "matched_articles": [], "prediction": None, "draft_card": None,
            }

        last_assistant_asked_email = False
        if cmd.history:
            for item in reversed(cmd.history[-4:]):
                if item.get("role") == "assistant":
                    last_txt = strip_accents_lower(str(item.get("content") or ""))
                    last_assistant_asked_email = "correo institucional" in last_txt and "radicado" in last_txt
                    break

        if (
            TICKET_ID_REGEX.search(query)
            or (last_assistant_asked_email and EMAIL_REGEX.search(query))
            or any(
                kw in norm
                for kw in (
                    "mis tickets", "estado de mi ticket", "estado del ticket", "estado ticket",
                    "como va mi caso", "como va mi ticket", "consultar radicado", "consultar ticket",
                )
            )
        ):
            return handle_check_ticket_tool(
                self._uow_factory,
                self._guest_token_factory,
                query,
                actor,
                history=cmd.history,
                email=cmd.email,
                ip_address=cmd.ip_address,
            )

        conv = handle_conversational_domain(query, actor, already_introduced=already_introduced)
        if conv is not None:
            return conv

        accumulated_text = collect_incident_context(query, cmd.history)
        scrubbed_text, pii_scrubbed = scrub_pii_for_model(accumulated_text)
        with self._uow_factory() as uow:
            articles = uow.kb_articles.list_articles(visibility="Pública", status="Publicado")
            sla_table = uow.catalog.get_sla_table()

        wants_direct_draft = any(kw in strip_accents_lower(accumulated_text) for kw in DRAFT_TICKET_TERMS)
        matches = (
            []
            if wants_direct_draft
            else self._ai_engine.search_knowledge_base(
                query=scrubbed_text or accumulated_text, articles=articles, top_k=2, min_similarity=0.22
            )
        )
        prediction = self._ai_engine.classify_text(scrubbed_text or accumulated_text)
        chosen_service = (
            cmd.selected_service if cmd.selected_service in UPC_SERVICE_CATALOG else prediction["predicted_service"]
        )
        confidence_pct = 100.0 if cmd.selected_service in UPC_SERVICE_CATALOG else float(prediction["confidence_pct"])
        low_confidence = (
            False
            if cmd.selected_service in UPC_SERVICE_CATALOG
            else bool(prediction.get("is_low_confidence", confidence_pct < (MIN_CONFIDENCE_THRESHOLD * 100.0)))
        )

        if low_confidence and (not matches or float(matches[0].get("similarity_score", 0.0)) < 0.35):
            return {
                "status": "needs_clarification",
                "tool_invoked": "clarify_service",
                "reply": (
                    f"No estoy seguro de la categoría exacta (confianza `{confidence_pct:.1f}%`, por debajo del mínimo del `60 %`). "
                    "¿Podrías describir un poco más el síntoma o elegir a qué servicio corresponde tu caso?"
                ),
                "service_options": list(UPC_SERVICE_CATALOG.keys()),
                "matched_articles": matches, "prediction": prediction,
                "pii_scrubbed": pii_scrubbed, "draft_card": None,
            }

        cited_kb = matches[0] if matches else None
        explicit = extract_explicit_ticket_entities(accumulated_text)
        resolved_sede = cmd.selected_sede if cmd.selected_sede in UPC_SEDES else explicit["sede"]
        resolved_location = cmd.selected_location if cmd.selected_location in UPC_LOCATIONS else explicit["location"]
        resolved_urgency = cmd.selected_urgency if cmd.selected_urgency in ("Alta", "Media", "Baja") else explicit["urgency"]
        missing_fields = [k for k, v in (("sede", resolved_sede), ("location", resolved_location), ("urgency", resolved_urgency)) if not v]

        if matches and not wants_direct_draft and cmd.failed_attempts == 0:
            top = matches[0]
            missing_note = (
                "\n\nSi estos pasos no resuelven la falla, indícame tu **sede**, **ubicación exacta** y **si puedes seguir trabajando** para preparar el borrador de tu ticket."
                if missing_fields
                else "\n\nSi persiste tras validar esta guía, puedes confirmarme para generar el borrador de tu ticket."
            )
            return {
                "status": "kb_matched",
                "tool_invoked": "search_kb",
                "reply": (
                    f"Encontré una guía oficial en la Base de Conocimiento que puede ayudarte:\n\n"
                    f"**[{top['code']}] {top['title']}** *(Similitud: {top['similarity_score']:.2f} | "
                    f"Clasificación: {chosen_service} {confidence_pct:.1f}%)*\n\n"
                    f"**Pasos recomendados:**\n{top['solution_steps']}{missing_note}"
                ),
                "matched_articles": matches, "prediction": prediction,
                "pii_scrubbed": pii_scrubbed, "missing_fields": missing_fields, "draft_card": None,
            }

        can_auto_prompt_urgency = (
            wants_direct_draft and resolved_sede is not None and resolved_location is not None and missing_fields == ["urgency"]
        )
        if missing_fields and not can_auto_prompt_urgency:
            prompts_map = {
                "sede": "**¿En qué sede UPC te encuentras?** (Sabanas, Hurtado o Seccional Aguachica)",
                "location": "**¿Cuál es la ubicación exacta o bloque?** (Bloque A/B/C/D, Laboratorios de Cómputo, Biblioteca o Edificio Administrativo)",
                "urgency": "**¿Puedes seguir trabajando o realizando la actividad?** (Alta: detenido sin alternativa · Media: avance parcial · Baja: programable)",
            }
            questions_md = "\n".join(f"- {prompts_map[f]}" for f in missing_fields)
            kb_ref = f"\n\n*(Artículo relacionado consultado: **[{cited_kb['code']}] {cited_kb['title']}**)*" if cited_kb else ""
            return {
                "status": "needs_missing_fields",
                "tool_invoked": "ask_missing_fields",
                "reply": (
                    f"Entendido, corresponde al servicio **{chosen_service}** ({confidence_pct:.1f}% de confianza). "
                    "Antes de armar el borrador editable, necesito confirmar estos datos (nunca los asumo por ti):\n\n"
                    f"{questions_md}{kb_ref}"
                ),
                "missing_fields": missing_fields,
                "partial_draft": {
                    "title": accumulated_text[:75] if len(accumulated_text) <= 75 else accumulated_text[:72] + "...",
                    "description": accumulated_text, "service_name": chosen_service,
                    "sede": resolved_sede, "location": resolved_location, "urgency": resolved_urgency,
                    "confidence_pct": confidence_pct,
                },
                "matched_articles": matches, "prediction": prediction,
                "pii_scrubbed": pii_scrubbed, "draft_card": None,
            }

        draft_card = build_agent_draft_card(
            description_text=accumulated_text, title_text=accumulated_text.split("|")[0],
            user=actor, service_name=chosen_service, confidence_pct=confidence_pct,
            model_name=prediction["model_name"], sede=resolved_sede, location=resolved_location,
            urgency=resolved_urgency or "Media", sla_table=sla_table,
            cited_kb_code=cited_kb["code"] if cited_kb else None,
            urgency_needs_confirmation=can_auto_prompt_urgency,
        )
        kb_cite_line = f"\n- **Guía KB citada:** `[{cited_kb['code']}]` {cited_kb['title']}" if cited_kb else ""
        urgency_note = "\n\n*Nota: verifica o ajusta la **Urgencia** en la tarjeta editable antes de confirmar.*" if can_auto_prompt_urgency else ""
        return {
            "status": "draft_ready",
            "tool_invoked": "draft_ticket",
            "reply": (
                f"He preparado el borrador editable de tu ticket con cálculo determinista **OR-03**:\n\n"
                f"- **Servicio:** `{draft_card['service_name']}` ({draft_card['confidence_pct']}%)\n"
                f"- **Área:** **{draft_card['area']}**\n"
                f"- **Prioridad OR-03:** **{draft_card['priority']}** (`{draft_card['impact']} × {draft_card['urgency']}`, SLA `{draft_card['sla_resolution_hours']}h`)\n"
                f"- **Sede y ubicación:** **{draft_card['sede']}** · {draft_card['location']}"
                f"{kb_cite_line}{urgency_note}\n\n"
                "Revisa o edita los campos en la tarjeta inferior y confirma para radicar."
            ),
            "matched_articles": matches, "prediction": prediction,
            "pii_scrubbed": pii_scrubbed, "draft_card": draft_card,
        }
