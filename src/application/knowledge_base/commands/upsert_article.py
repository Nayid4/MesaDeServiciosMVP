"""Caso de uso CQRS de creación y actualización de artículos de Base de Conocimiento."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.domain.exceptions import ForbiddenError, NotFoundError, ValidationDomainError
from src.domain.ports import IUnitOfWork
from src.domain.rules import (
    KB_ARTICLE_STATUSES,
    KB_VISIBILITIES,
    now_bogota,
    sanitize_kb_html,
)


@dataclass(frozen=True)
class UpsertKnowledgeArticleCommand(Command):
    actor: Dict[str, Any]
    article_id: Optional[int]
    code: str
    title: str
    service_name: str
    symptoms: str
    solution_steps: str
    keywords: str
    visibility: str = "Pública"
    status: str = "Publicado"
    category_topic: str = "General"
    probable_cause: str = ""
    escalation_criteria: str = ""
    change_summary: str = ""
    source_ticket_id: Optional[int] = None
    ip_address: str = "127.0.0.1"


class UpsertKnowledgeArticleCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: UpsertKnowledgeArticleCommand) -> Dict[str, Any]:
        role = cmd.actor.get("role")
        if role not in ("tecnico", "coordinador", "admin"):
            raise ForbiddenError("No tiene permisos para crear o editar en la Base de Conocimiento.")
        if not cmd.title or len(cmd.title.strip()) < 5:
            raise ValidationDomainError("El título del artículo KB debe tener al menos 5 caracteres.")
        if not cmd.symptoms or len(cmd.symptoms.strip()) < 5:
            raise ValidationDomainError("Debe describir los síntomas del incidente (mínimo 5 caracteres).")
        if not cmd.solution_steps or len(cmd.solution_steps.strip()) < 10:
            raise ValidationDomainError("Debe detallar los pasos de solución (mínimo 10 caracteres).")
        if cmd.visibility not in KB_VISIBILITIES:
            raise ValidationDomainError(f"Visibilidad inválida '{cmd.visibility}'. Use Pública o Interna.")

        status = (cmd.status or "En revisión").strip()
        if role == "tecnico":
            status = "Borrador" if status == "Borrador" else "En revisión"
        elif status not in KB_ARTICLE_STATUSES:
            raise ValidationDomainError(f"Estado editorial inválido '{status}'.")

        with self._uow_factory() as uow:
            existing = uow.kb_articles.get_by_id(int(cmd.article_id)) if cmd.article_id else None
            if cmd.article_id and existing is None:
                raise NotFoundError(f"Artículo KB #{cmd.article_id} no encontrado.")

            art = uow.kb_articles.upsert(
                {
                    "id": cmd.article_id,
                    "code": cmd.code,
                    "title": cmd.title,
                    "service_name": cmd.service_name,
                    "category_topic": cmd.category_topic or "General",
                    "symptoms": sanitize_kb_html(cmd.symptoms),
                    "probable_cause": sanitize_kb_html(
                        cmd.probable_cause or "Por verificar en diagnóstico técnico [CONFIRMAR]."
                    ),
                    "solution_steps": sanitize_kb_html(cmd.solution_steps),
                    "escalation_criteria": sanitize_kb_html(
                        cmd.escalation_criteria
                        or "Escalar a soporte Nivel 2 del área técnica si persiste el incidente."
                    ),
                    "keywords": cmd.keywords,
                    "visibility": cmd.visibility,
                    "status": status,
                    "author_email": existing["author_email"] if existing else cmd.actor["email"],
                    "actor_email": cmd.actor["email"],
                    "reviewer_email": (
                        cmd.actor["email"]
                        if status == "Publicado"
                        else (existing.get("reviewer_email") if existing else None)
                    ),
                    "review_notes": None if status != "Borrador" else (existing.get("review_notes") if existing else None),
                    "is_demo": bool(existing.get("is_demo", False)) if existing else False,
                    "change_summary": cmd.change_summary
                    or (f"Edición ({status})" if existing else f"Propuesta inicial ({status})"),
                }
            )
            if cmd.source_ticket_id:
                src_ticket = uow.tickets.get_by_id(int(cmd.source_ticket_id))
                if src_ticket is not None:
                    uow.tickets.add_audit_event(
                        {
                            "ticket_id": int(src_ticket["id"]),
                            "actor_email": cmd.actor["email"],
                            "action": "Artículo KB propuesto desde ticket",
                            "old_status": src_ticket["status"],
                            "new_status": src_ticket["status"],
                            "comment": f"Generado borrador KB {art['code']} ({art['status']}): {art['title']}",
                            "created_at": now_bogota().isoformat(),
                        }
                    )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "KB_ARTICLE_UPSERTED",
                    "entity": "kb_articles",
                    "entity_id": art["code"],
                    "new_value": f"v{art['version']} | Estado={art['status']} | Visibilidad={art['visibility']}",
                }
            )
            uow.commit()
        return art


CreateArticleCommand = UpsertKnowledgeArticleCommand
UpdateArticleCommand = UpsertKnowledgeArticleCommand
CreateArticleCommandHandler = UpsertKnowledgeArticleCommandHandler
UpdateArticleCommandHandler = UpsertKnowledgeArticleCommandHandler
