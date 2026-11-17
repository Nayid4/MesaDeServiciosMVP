"""Value Objects de paginación pura del dominio."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Generic, List, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PageRequest:
    """Solicitud de paginación validada e inmutable."""

    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        safe_page = max(1, int(self.page or 1))
        safe_size = max(1, min(100, int(self.page_size or 20)))
        object.__setattr__(self, "page", safe_page)
        object.__setattr__(self, "page_size", safe_size)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class PagedResult(Generic[T]):
    """Resultado paginado inmutable con conteo total SQL real."""

    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: List[T], total: int, page_request: PageRequest) -> "PagedResult[T]":
        total_int = max(0, int(total))
        total_pages = max(1, math.ceil(total_int / page_request.page_size)) if total_int > 0 else 1
        return cls(
            items=items,
            total=total_int,
            page=page_request.page,
            page_size=page_request.page_size,
            pages=total_pages,
        )
