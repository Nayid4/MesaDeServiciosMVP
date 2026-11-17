"""Puerto abstracto del motor de IA (clasificación NLP, búsqueda RAG KB y turnos del agente)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IAIService(ABC):
    """Puerto del motor de IA (clasificación NLP, búsqueda RAG KB y turnos del agente)."""

    @abstractmethod
    def classify_text(self, text: str) -> Dict[str, Any]: ...

    @abstractmethod
    def search_knowledge_base(
        self,
        query: str,
        articles: List[Dict[str, Any]],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def process_turn(
        self,
        user: Optional[Dict[str, Any]],
        message: str,
        *,
        simulate_failure: bool = False,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]: ...
