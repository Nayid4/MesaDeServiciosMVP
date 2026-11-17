"""Reglas de flujo editorial y sanitización HTML segura para Base de Conocimiento."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

KB_ARTICLE_STATUSES = ("Borrador", "En revisión", "Publicado", "Retirado")
KB_VISIBILITIES = ("Pública", "Interna")
KB_CATEGORIES = (
    "Cuentas y correo",
    "Wi-Fi y Eduroam",
    "Plataformas académicas",
    "Impresión",
    "Equipos de cómputo",
    "Aulas y videoproyectores",
    "Software y licencias",
    "VPN",
    "Seguridad básica",
)
KB_VALID_TRANSITIONS: Dict[str, List[str]] = {
    "Borrador": ["En revisión", "Publicado"],
    "En revisión": ["Publicado", "Borrador"],
    "Publicado": ["Retirado", "En revisión"],
    "Retirado": ["Borrador", "Publicado"],
}

_KB_ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "code", "pre", "h4", "h5", "blockquote",
}
_KB_VOID_TAGS = {"br"}
_KB_BLOCKED_CONTAINER_TAGS = {
    "script", "style", "iframe", "object", "embed", "svg", "form", "noscript", "template",
}
_UNSAFE_URI_RE = re.compile(r"(?:javascript|vbscript|data\s*:\s*text/html)\s*:", re.IGNORECASE)


class _SafeKbHtmlSanitizer(HTMLParser):
    """Sanitizador estricto por lista blanca de etiquetas sin atributos para contenido KB."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        _ = attrs
        t = tag.lower()
        if t in _KB_BLOCKED_CONTAINER_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if t in _KB_ALLOWED_TAGS:
            self.parts.append("<br/>" if t in _KB_VOID_TAGS else f"<{t}>")

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        _ = attrs
        t = tag.lower()
        if t in _KB_BLOCKED_CONTAINER_TAGS or self._skip_depth > 0:
            return
        if t in _KB_ALLOWED_TAGS:
            self.parts.append("<br/>" if t in _KB_VOID_TAGS else f"<{t}></{t}>")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _KB_BLOCKED_CONTAINER_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if t in _KB_ALLOWED_TAGS and t not in _KB_VOID_TAGS:
            self.parts.append(f"</{t}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        clean = _UNSAFE_URI_RE.sub("", data)
        self.parts.append(html.escape(clean, quote=False))

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(f"&#{name};")


def sanitize_kb_html(raw_text: str) -> str:
    """Sanea HTML del editor KB permitiendo solo formato básico seguro sin atributos ni scripts."""
    text = str(raw_text or "").strip()
    if not text:
        return ""
    parser = _SafeKbHtmlSanitizer()
    parser.feed(text)
    parser.close()
    cleaned = "".join(parser.parts)
    return _UNSAFE_URI_RE.sub("", cleaned).strip()
