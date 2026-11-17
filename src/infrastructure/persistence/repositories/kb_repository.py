"""Repositorio SQLAlchemy de Base de Conocimiento (KB) con paginación y versionado."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from src.domain.common.pagination import PageRequest, PagedResult
from src.domain.ports import IKnowledgeRepo
from src.domain.rules import now_bogota, sanitize_kb_html
from src.infrastructure.persistence.models import (
    KnowledgeArticleORM,
    KnowledgeArticleVersionORM,
)
from src.infrastructure.persistence.repositories.base import (
    execute_paginated_query,
    model_to_dict,
)


class SqlAlchemyKnowledgeRepo(IKnowledgeRepo):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _build_filtered_stmt(
        self,
        *,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
        category_topic: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Any:
        stmt = select(KnowledgeArticleORM)
        if visibility:
            stmt = stmt.where(KnowledgeArticleORM.visibility == visibility)
        if status:
            stmt = stmt.where(KnowledgeArticleORM.status == status)
        if service_name:
            stmt = stmt.where(KnowledgeArticleORM.service_name == service_name)
        if category_topic:
            stmt = stmt.where(KnowledgeArticleORM.category_topic == category_topic)
        if search:
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(KnowledgeArticleORM.code).like(like),
                    func.lower(KnowledgeArticleORM.title).like(like),
                    func.lower(KnowledgeArticleORM.symptoms).like(like),
                    func.lower(KnowledgeArticleORM.keywords).like(like),
                )
            )
        return stmt.order_by(asc(KnowledgeArticleORM.code))

    def list_articles(
        self,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
        category_topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            visibility=visibility,
            status=status,
            service_name=service_name,
            category_topic=category_topic,
        )
        return [model_to_dict(a) for a in self.session.scalars(stmt).all()]

    def list_articles_paginated(
        self,
        page_request: PageRequest,
        *,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
        category_topic: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PagedResult[Dict[str, Any]]:
        stmt = self._build_filtered_stmt(
            visibility=visibility,
            status=status,
            service_name=service_name,
            category_topic=category_topic,
            search=search,
        )
        return execute_paginated_query(self.session, stmt, KnowledgeArticleORM.id, page_request)

    def get_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        obj = self.session.get(KnowledgeArticleORM, int(article_id))
        return model_to_dict(obj) if obj is not None else None

    def _record_version_snapshot(
        self, obj: KnowledgeArticleORM, actor_email: str, change_summary: str, created_at: str
    ) -> None:
        self.session.add(
            KnowledgeArticleVersionORM(
                article_id=obj.id,
                version_number=int(obj.version or 1),
                title=obj.title,
                service_name=obj.service_name,
                category_topic=obj.category_topic,
                symptoms=obj.symptoms,
                probable_cause=obj.probable_cause,
                solution_steps=obj.solution_steps,
                escalation_criteria=obj.escalation_criteria,
                keywords=obj.keywords,
                visibility=obj.visibility,
                status=obj.status,
                review_notes=obj.review_notes,
                actor_email=actor_email,
                change_summary=change_summary[:255],
                created_at=created_at,
            )
        )
        self.session.flush()

    def upsert(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = now_bogota().isoformat()
        article_id = article_data.get("id")
        obj: Optional[KnowledgeArticleORM] = (
            self.session.get(KnowledgeArticleORM, int(article_id)) if article_id else None
        )
        if obj is None and article_data.get("code"):
            obj = self.session.scalars(
                select(KnowledgeArticleORM).where(
                    KnowledgeArticleORM.code == article_data["code"].strip().upper()
                )
            ).first()

        clean_symptoms = sanitize_kb_html(article_data.get("symptoms", ""))
        clean_cause = sanitize_kb_html(
            article_data.get("probable_cause") or "Por verificar en diagnóstico técnico [CONFIRMAR]."
        )
        clean_steps = sanitize_kb_html(article_data.get("solution_steps", ""))
        clean_escalation = sanitize_kb_html(
            article_data.get("escalation_criteria")
            or "Escalar a soporte Nivel 2 del área técnica si persiste el incidente tras aplicar los pasos."
        )
        actor_email = (
            article_data.get("actor_email")
            or article_data.get("reviewer_email")
            or article_data.get("author_email")
            or "tecnico1@unicesar.edu.co"
        )
        change_summary = (article_data.get("change_summary") or "").strip()

        if obj is not None:
            obj.title = article_data["title"].strip()
            obj.service_name = article_data["service_name"]
            obj.category_topic = (article_data.get("category_topic") or obj.category_topic or "General").strip()
            obj.symptoms = clean_symptoms
            obj.probable_cause = clean_cause
            obj.solution_steps = clean_steps
            obj.escalation_criteria = clean_escalation
            obj.keywords = (article_data.get("keywords") or "").strip()
            obj.visibility = article_data.get("visibility", obj.visibility or "Pública")
            obj.status = article_data.get("status", obj.status or "Publicado")
            obj.version = int(obj.version or 1) + 1
            if "reviewer_email" in article_data:
                obj.reviewer_email = article_data.get("reviewer_email")
            if "review_notes" in article_data:
                obj.review_notes = article_data.get("review_notes")
            if "is_demo" in article_data:
                obj.is_demo = bool(article_data["is_demo"])
            if not obj.created_at:
                obj.created_at = now_iso
            obj.updated_at = now_iso
            self.session.flush()
            self._record_version_snapshot(
                obj, actor_email, change_summary or f"Actualización a estado {obj.status}", now_iso
            )
            return model_to_dict(obj)

        code = (
            article_data.get("code") or f"KB-{int(datetime.now().timestamp()) % 10000:04d}"
        ).strip().upper()
        new_obj = KnowledgeArticleORM(
            code=code,
            title=article_data["title"].strip(),
            service_name=article_data["service_name"],
            category_topic=(article_data.get("category_topic") or "General").strip(),
            symptoms=clean_symptoms,
            probable_cause=clean_cause,
            solution_steps=clean_steps,
            escalation_criteria=clean_escalation,
            keywords=(article_data.get("keywords") or "").strip(),
            visibility=article_data.get("visibility", "Pública"),
            status=article_data.get("status", "En revisión"),
            version=1,
            author_email=article_data.get("author_email", "tecnico1@unicesar.edu.co"),
            reviewer_email=article_data.get("reviewer_email"),
            review_notes=article_data.get("review_notes"),
            is_demo=bool(article_data.get("is_demo", False)),
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.session.add(new_obj)
        self.session.flush()
        self._record_version_snapshot(
            new_obj, new_obj.author_email, change_summary or f"Creación inicial ({new_obj.status})", now_iso
        )
        return model_to_dict(new_obj)

    def list_versions(self, article_id: int) -> List[Dict[str, Any]]:
        stmt = (
            select(KnowledgeArticleVersionORM)
            .where(KnowledgeArticleVersionORM.article_id == int(article_id))
            .order_by(desc(KnowledgeArticleVersionORM.version_number))
        )
        return [model_to_dict(v) for v in self.session.scalars(stmt).all()]

    def get_version(self, article_id: int, version_number: int) -> Optional[Dict[str, Any]]:
        stmt = select(KnowledgeArticleVersionORM).where(
            KnowledgeArticleVersionORM.article_id == int(article_id),
            KnowledgeArticleVersionORM.version_number == int(version_number),
        )
        obj = self.session.scalars(stmt).first()
        return model_to_dict(obj) if obj is not None else None
