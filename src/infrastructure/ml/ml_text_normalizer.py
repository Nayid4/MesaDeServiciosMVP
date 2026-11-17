"""Normalización léxica, stopwords y expansión de sinónimos TIC para NLP."""

from __future__ import annotations

import re
import unicodedata
from typing import List

SPANISH_STOPWORDS: List[str] = [
    "a", "al", "algo", "ante", "aqui", "ayuda", "como", "con", "cual", "cuando",
    "de", "del", "desde", "el", "en", "es", "esa", "ese", "eso", "esta", "este",
    "esto", "favor", "fue", "hace", "hay", "hoy", "la", "las", "le", "les", "lo",
    "los", "mas", "me", "mi", "mis", "muy", "necesito", "no", "o", "para", "pasa",
    "pero", "por", "problema", "que", "se", "si", "sin", "sirve", "solo", "su",
    "sus", "te", "tengo", "tiene", "tienen", "tu", "un", "una", "uno", "y", "ya",
]

_SYNONYM_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(computadora|computador|compu|conputadora|conputador|ordenador|pc|torre|cpu|portatil|laptop)\b"),
        " computador pc equipo_computo ",
    ),
    (
        re.compile(r"\bno\s+(prende|prene|enciende|ensiende|arranca|inicia)\b"),
        " no_enciende no_prende encendido falla_hardware ",
    ),
    (
        re.compile(r"\b(pantalla\s+negra|monitor\s+negro|no\s+da\s+video|sin\s+video|sin\s+imagen)\b"),
        " pantalla_negra monitor sin_video computador falla_hardware ",
    ),
    (
        re.compile(r"\b(teclado|mouse|puertos?\s+usb|usb|pantallazo|lentitud|fuente\s+de\s+poder)\b"),
        " equipo_computo hardware falla_hardware periferico ",
    ),
    (
        re.compile(r"\b(wiffi|wifi|wi[- ]?fi|interner|internet|interne|eduroan|eduroam|inalambric\w*|ethernet|lan|rj45|dhcp|switch|router|access\s+point|punto\s+de\s+red|no\s+da\s+red|sin\s+red|no\s+hay\s+internet)\b"),
        " wifi eduroam internet red_inalambrica conectividad switch lan ",
    ),
    (
        re.compile(r"\b(vpn|tunel|forticlient|sin\s+internet|sin\s+salida\s+a\s+internet|ip\s+169\w*)\b"),
        " vpn internet red_inalambrica conectividad ",
    ),
    (
        re.compile(r"\b(videobeam|video\s+beam|videobean|videoproyector|proyector|hdmi|vga|pantalla\s+interactiva|parlantes|amplificador|sonido\s+del\s+(salon|aula)|zumbido|telon|pizarra)\b"),
        " videoproyector proyector hdmi aula_inteligente sonido_aula ",
    ),
    (
        re.compile(r"\b(bortal|vortal|aulaweb|aula\s+web|moodle|matricul\w*|calificacion\w*|notas)\b"),
        " vortal aula_web plataforma_academica ",
    ),
    (
        re.compile(r"\b(inpresora|impresora|impresion|toner|escaner|atasco|spooler)\b"),
        " impresora escaner toner equipo_computo ",
    ),
    (
        re.compile(r"\b(contrasena|clabe|clave|mfa|buzon|correo|coreo|unicesar|webmail)\b"),
        " contrasena clave correo_institucional cuenta ",
    ),
    (
        re.compile(r"\b(autocat|autocad|matla|matlab|ofice|office|spss|rstudio|licensia|licencia|licenciamiento|word|excel|powerpoint|antivirus|python)\b"),
        " software licencia licenciamiento spss matlab autocad office ",
    ),
]

DOMAIN_SIGNAL_TERMS: set[str] = {
    "computador", "pc", "equipo_computo", "hardware", "falla_hardware", "no_enciende",
    "no_prende", "pantalla_negra", "monitor", "sin_video", "impresora", "escaner", "toner",
    "teclado", "mouse", "lentitud", "usb", "periferico", "fuente", "pantallazo", "wifi",
    "eduroam", "internet", "red_inalambrica", "conectividad", "lan", "ethernet", "switch",
    "dhcp", "vpn", "rj45", "vortal", "aula_web", "plataforma_academica", "moodle",
    "matricula", "calificaciones", "notas", "contrasena", "clave", "correo_institucional",
    "cuenta", "buzon", "mfa", "unicesar", "videoproyector", "proyector", "hdmi", "vga",
    "aula_inteligente", "sonido_aula", "parlantes", "amplificador", "zumbido", "lampara",
    "audio", "software", "licencia", "licenciamiento", "spss", "matlab", "autocad",
    "office", "rstudio", "antivirus", "python",
}


def strip_accents_lower(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def normalize_tic_synonyms_impl(text: str) -> str:
    """Normaliza tildes, typos comunes y sinónimos TIC."""
    norm = strip_accents_lower(text)
    expansions: List[str] = [norm]
    for pattern, suffix in _SYNONYM_PATTERNS:
        if pattern.search(norm):
            expansions.append(suffix)
    return " ".join(expansions)


def count_domain_signals(text: str) -> int:
    """Cuenta señales léxicas TIC explícitas presentes en el texto normalizado."""
    norm = normalize_tic_synonyms_impl(text)
    tokens = set(re.findall(r"[a-z0-9_@.-]+", norm))
    return sum(1 for t in tokens if t in DOMAIN_SIGNAL_TERMS)
