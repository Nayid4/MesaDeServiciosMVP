"""Casos de uso CQRS de transiciones editoriales y restauración de versiones KB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.application.common import Command
from src.domain.exceptions import (
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    ValidationDomainError,
)
from src.domain.ports import IUnitOfWork
from src.domain.rules import KB_VALID_TRANSITIONS


@dataclass(frozen=True)
class TransitionKnowledgeArticleCommand(Command):
    actor: Dict[str, Any]
    article_id: int
    action: str
    review_notes: Optional[str] = None
    restore_to_status: Optional[str] = None
    ip_address: str = "127.0.0.1"


@dataclass(frozen=True)
class RestoreKnowledgeArticleVersionCommand(Command):
    actor: Dict[str, Any]
    article_id: int
    version_number: int
    ip_address: str = "127.0.0.1"


class TransitionKnowledgeArticleCommandHandler:
    """Gestiona transiciones editoriales KB: enviar a revisión, publicar, devolver, retirar y restaurar."""

    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: TransitionKnowledgeArticleCommand) -> Dict[str, Any]:
        role = cmd.actor.get("role")
        if role not in ("tecnico", "coordinador", "admin"):
            raise ForbiddenError("No tiene permisos para modificar el ciclo editorial de la KB.")

        action = (cmd.action or "").strip().lower()
        action_target = {
            "enviar_revision": "En revisión",
            "publicar": "Publicado",
            "devolver": "Borrador",
            "retirar": "Retirado",
            "restaurar": cmd.restore_to_status if cmd.restore_to_status in ("Publicado", "Borrador") else "Publicado",
        }
        if action not in action_target:
            raise ValidationDomainError(
                f"Acción editorial desconocida '{cmd.action}'. Use enviar_revision, publicar, devolver, retirar o restaurar."
            )
        if action in ("publicar", "devolver", "retirar", "restaurar") and role not in ("coordinador", "admin"):
            raise ForbiddenError(
                f"Solo Coordinador o Administrador pueden ejecutar la acción '{action}' sobre artículos KB."
            )
        if action == "devolver" and (not cmd.review_notes or len(cmd.review_notes.strip()) < 5):
            raise ValidationDomainError(
                "Al devolver un artículo a Borrador debe registrar observaciones de revisión (mínimo 5 caracteres)."
            )

        target_status = action_target[action]
        with self._uow_factory() as uow:
            uow.begin_immediate()
            art = uow.kb_articles.get_by_id(cmd.article_id)
            if not art:
                raise NotFoundError(f"Artículo KB #{cmd.article_id} no encontrado.")

            current_status = art["status"]
            if action == "devolver" and current_status != "En revisión":
                raise InvalidTransitionError("Solo se pueden devolver con observaciones artículos que estén 'En revisión'.")
            if action == "restaurar" and current_status != "Retirado":
                raise InvalidTransitionError("Solo se pueden restaurar artículos que estén en estado 'Retirado'.")
            if target_status not in KB_VALID_TRANSITIONS.get(current_status, []):
                raise InvalidTransitionError(f"Transición KB no permitida de '{current_status}' a '{target_status}'.")

            notes = cmd.review_notes.strip() if action == "devolver" and cmd.review_notes else None
            reviewer = cmd.actor["email"] if action in ("publicar", "devolver", "retirar", "restaurar") else art.get("reviewer_email")
            summary_map = {
                "enviar_revision": "Enviado a revisión editorial",
                "publicar": "Publicado tras revisión del coordinador",
                "devolver": f"Devuelto con observaciones: {notes}",
                "retirar": "Artículo retirado de consulta pública y asistente IA",
                "restaurar": f"Artículo restaurado a estado {target_status}",
            }
            updated = uow.kb_articles.upsert(
                {
                    **art,
                    "status": target_status,
                    "actor_email": cmd.actor["email"],
                    "reviewer_email": reviewer,
                    "review_notes": notes,
                    "change_summary": summary_map[action],
                }
            )
            if action in ("devolver", "publicar") and art.get("author_email"):
                uow.notifications.create(
                    {
                        "user_email": art["author_email"],
                        "ticket_number": art["code"],
                        "title": (
                            f"Artículo {art['code']} devuelto con observaciones"
                            if action == "devolver"
                            else f"Artículo {art['code']} publicado en la KB"
                        ),
                        "message": notes or f"Aprobado por {cmd.actor['email']}.",
                        "category": "status",
                    }
                )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "KB_ARTICLE_TRANSITIONED",
                    "entity": "kb_articles",
                    "entity_id": art["code"],
                    "old_value": current_status,
                    "new_value": f"{target_status} | {summary_map[action]}",
                }
            )
            uow.commit()
        return updated


class RestoreKnowledgeArticleVersionCommandHandler:
    def __init__(self, uow_factory: Callable[[], IUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def handle(self, cmd: RestoreKnowledgeArticleVersionCommand) -> Dict[str, Any]:
        role = cmd.actor.get("role")
        if role not in ("tecnico", "coordinador", "admin"):
            raise ForbiddenError("No tiene permisos para restaurar versiones de artículos KB.")

        with self._uow_factory() as uow:
            uow.begin_immediate()
            art = uow.kb_articles.get_by_id(cmd.article_id)
            if not art:
                raise NotFoundError(f"Artículo KB #{cmd.article_id} no encontrado.")
            target_ver = uow.kb_articles.get_version(cmd.article_id, cmd.version_number)
            if not target_ver:
                raise NotFoundError(f"La versión v{cmd.version_number} no existe para el artículo #{cmd.article_id}.")

            next_status = "En revisión" if role == "tecnico" else (art.get("status") or target_ver.get("status") or "Borrador")
            restored = uow.kb_articles.upsert(
                {
                    "id": art["id"],
                    "code": art["code"],
                    "title": target_ver["title"],
                    "service_name": target_ver["service_name"],
                    "category_topic": target_ver.get("category_topic", "General"),
                    "symptoms": target_ver["symptoms"],
                    "probable_cause": target_ver.get("probable_cause", ""),
                    "solution_steps": target_ver["solution_steps"],
                    "escalation_criteria": target_ver.get("escalation_criteria", ""),
                    "keywords": target_ver["keywords"],
                    "visibility": target_ver["visibility"],
                    "status": next_status,
                    "author_email": art["author_email"],
                    "actor_email": cmd.actor["email"],
                    "reviewer_email": cmd.actor["email"] if role in ("coordinador", "admin") else art.get("reviewer_email"),
                    "review_notes": None,
                    "is_demo": bool(art.get("is_demo", False)),
                    "change_summary": f"Restaurado desde versión v{cmd.version_number}",
                }
            )
            uow.audit_logs.append(
                {
                    "user_email": cmd.actor["email"],
                    "ip_address": cmd.ip_address,
                    "action": "KB_ARTICLE_VERSION_RESTORED",
                    "entity": "kb_articles",
                    "entity_id": art["code"],
                    "old_value": f"v{art['version']}",
                    "new_value": f"v{restored['version']} (desde v{cmd.version_number})",
                }
            )
            uow.commit()
        return restored


ChangeArticleStatusCommand = TransitionKnowledgeArticleCommand
ChangeArticleStatusCommandHandler = TransitionKnowledgeArticleCommandHandler
