"""Value Object TicketCode por categoría (MS-<CAT>-AAAA-NNNNNN) y alias legado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.common.exceptions import ValidationDomainError
from src.domain.tickets.catalog_rules import (
    CATEGORY_TICKET_NUMBER_PATTERN,
    LEGACY_TICKET_NUMBER_PATTERN,
    TICKET_NUMBER_PATTERN,
    VALID_CATEGORY_PREFIXES,
    format_ticket_number,
)


@dataclass(frozen=True)
class TicketCode:
    """Consecutivo institucional inmutable por categoría MS-<CAT>-AAAA-NNNNNN (o alias heredado MS-AAAA-NNNNNN)."""

    value: str

    def __post_init__(self) -> None:
        normalized = (self.value or "").strip().upper()
        if not TICKET_NUMBER_PATTERN.match(normalized):
            allowed = ", ".join(VALID_CATEGORY_PREFIXES)
            raise ValidationDomainError(
                f"El código de ticket '{self.value}' no cumple el formato institucional MS-<CAT>-AAAA-NNNNNN "
                f"(prefijos válidos: {allowed}) ni el formato histórico MS-AAAA-NNNNNN."
            )
        object.__setattr__(self, "value", normalized)

    @property
    def is_legacy(self) -> bool:
        return bool(LEGACY_TICKET_NUMBER_PATTERN.match(self.value))

    @property
    def prefix(self) -> Optional[str]:
        m = CATEGORY_TICKET_NUMBER_PATTERN.match(self.value)
        return m.group(1) if m else None

    @property
    def year(self) -> int:
        m = CATEGORY_TICKET_NUMBER_PATTERN.match(self.value)
        if m:
            return int(m.group(2))
        m_leg = LEGACY_TICKET_NUMBER_PATTERN.match(self.value)
        return int(m_leg.group(1)) if m_leg else 2026

    @property
    def seq(self) -> int:
        m = CATEGORY_TICKET_NUMBER_PATTERN.match(self.value)
        if m:
            return int(m.group(3))
        m_leg = LEGACY_TICKET_NUMBER_PATTERN.match(self.value)
        return int(m_leg.group(2)) if m_leg else 0

    @classmethod
    def from_sequence(
        cls,
        seq: int,
        year: int = 2026,
        prefix: Optional[str] = "GEN",
    ) -> "TicketCode":
        return cls(format_ticket_number(seq=seq, year=year, prefix=prefix))

    def __str__(self) -> str:
        return self.value
