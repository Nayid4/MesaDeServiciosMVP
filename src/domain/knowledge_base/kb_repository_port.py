"""Puerto de repositorio para Base de Conocimiento y versionado."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.common.pagination import PageRequest, PagedResult


class IKnowledgeRepo(ABC):
    @abstractmethod
    def list_articles(
        self,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
        category_topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def list_articles_paginated(
        self,
        page_request: PageRequest,
        *,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        service_name: Optional[str] = None,
        category_topic: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PagedResult[Dict[str, Any]]: ...

    @abstractmethod
    def get_by_id(self, article_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def upsert(self, article_data: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def list_versions(self, article_id: int) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_version(self, article_id: int, version_number: int) -> Optional[Dict[str, Any]]: ...


IKnowledgeRepository = IKnowledgeRepo
