"""Validación de archivos adjuntos, firmas binarias (magic bytes) y notas de voz (SCR-04)."""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from typing import Any, Dict, Optional

from src.domain.common.exceptions import (
    InvalidAttachmentSignatureError,
    ValidationDomainError,
)

ALLOWED_ATTACHMENT_EXTENSIONS = {
    "jpg", "jpeg", "png", "webp", "pdf", "docx", "xlsx", "txt",
    "webm", "ogg", "mp3", "wav", "m4a", "mp4",
}
AUDIO_ATTACHMENT_EXTENSIONS = {"webm", "ogg", "mp3", "wav", "m4a", "mp4"}
FORBIDDEN_ATTACHMENT_EXTENSIONS = {
    "zip", "svg", "exe", "bat", "cmd", "sh", "js", "mjs",
    "html", "htm", "msi", "dll", "scr", "ps1", "vbs",
}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_TICKET = 5
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_AUDIO_DURATION_SECONDS = 180


def validate_attachment(filename: str, size_bytes: int) -> None:
    """Valida extensión permitida y límite de 10 MB para adjuntos (RF-04 / RF-13)."""
    if not filename or "." not in filename:
        raise ValueError("El archivo adjunto debe tener una extensión válida.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS)).upper()
        raise ValueError(f"Formato no permitido '.{ext}'. Formatos válidos: {allowed}.")
    if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValueError(f"El archivo '{filename}' supera el límite máximo permitido de 10 MB.")


def sanitize_filename(filename: str) -> str:
    """Limpia el nombre del archivo eliminando rutas y caracteres inseguros."""
    base = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not base or base in (".", ".."):
        return "archivo.bin"
    if "." in base:
        stem, ext = base.rsplit(".", 1)
        clean_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "adjunto"
        clean_ext = re.sub(r"[^A-Za-z0-9]+", "", ext).lower()
        return f"{clean_stem[:80]}.{clean_ext}" if clean_ext else clean_stem[:80]
    return re.sub(r"[^A-Za-z0-9_-]+", "_", base)[:80] or "adjunto"


def _detect_ooxml_office_mime(content_bytes: bytes, declared_ext: str) -> Optional[str]:
    """Verifica estructura interna OOXML real para distinguir .docx/.xlsx de un .zip genérico."""
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return None
    if "[Content_Types].xml" not in names:
        return None
    if declared_ext == "docx" and any(n.startswith("word/") for n in names):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if declared_ext == "xlsx" and any(n.startswith("xl/") for n in names):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None


def _detect_mime_by_magic_bytes(ext: str, content_bytes: bytes) -> Optional[str]:
    head = content_bytes[:64]
    if ext in ("jpg", "jpeg") and head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if ext == "png" and head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if ext == "webp" and len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if ext == "pdf" and head.startswith(b"%PDF-"):
        return "application/pdf"
    if ext in ("docx", "xlsx") and head.startswith(b"PK\x03\x04"):
        return _detect_ooxml_office_mime(content_bytes, ext)
    if ext == "txt":
        if (
            b"\x00" not in content_bytes[:4096]
            and not head.startswith((b"%PDF-", b"PK\x03\x04", b"\x89PNG", b"\xff\xd8\xff", b"OggS", b"RIFF", b"\x1a\x45\xdf\xa3"))
        ):
            for enc in ("utf-8", "latin-1"):
                try:
                    content_bytes.decode(enc)
                    return f"text/plain; charset={enc}"
                except UnicodeDecodeError:
                    continue
        return None
    if ext == "webm" and head.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if ext == "ogg" and head.startswith(b"OggS"):
        return "audio/ogg"
    if ext == "mp3" and (head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)):
        return "audio/mpeg"
    if ext == "wav" and len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if ext in ("m4a", "mp4") and len(head) >= 12 and head[4:8] == b"ftyp":
        return "audio/mp4"
    return None


def validate_attachment_binary(
    filename: str,
    content_bytes: bytes,
    *,
    audio_duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Valida firma binaria (magic bytes), extensión permitida, tamaño (10 MB) y duración de audio."""
    clean_name = sanitize_filename(filename)
    if "." not in clean_name:
        raise ValidationDomainError("El archivo adjunto debe incluir una extensión válida.")
    ext = clean_name.rsplit(".", 1)[-1].lower()

    if ext in FORBIDDEN_ATTACHMENT_EXTENSIONS or ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS)).upper()
        raise ValidationDomainError(f"Formato '.{ext}' prohibido o no permitido. Formatos válidos: {allowed}.")

    size_bytes = len(content_bytes)
    if size_bytes <= 0:
        raise ValidationDomainError(f"El archivo '{clean_name}' está vacío.")
    if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValidationDomainError(
            f"El archivo '{clean_name}' ({size_bytes / (1024 * 1024):.1f} MB) supera el límite máximo de 10 MB."
        )

    head = content_bytes[:64]
    head_lower = content_bytes[:512].lstrip().lower()
    if head.startswith(b"MZ") or head.startswith(b"\x7fELF") or head.startswith(b"#!"):
        raise InvalidAttachmentSignatureError(
            f"El archivo '{clean_name}' contiene firma de ejecutable/script y fue rechazado por seguridad."
        )
    if b"<svg" in head_lower or b"<script" in head_lower or head_lower.startswith(b"<!doctype html") or head_lower.startswith(b"<html"):
        raise InvalidAttachmentSignatureError(
            f"El archivo '{clean_name}' contiene marcado SVG/HTML activo no permitido."
        )

    detected_mime = _detect_mime_by_magic_bytes(ext, content_bytes)
    if not detected_mime:
        raise InvalidAttachmentSignatureError(
            f"La firma binaria (magic bytes) de '{clean_name}' no corresponde a un archivo '.{ext}' legítimo."
        )

    is_audio = ext in AUDIO_ATTACHMENT_EXTENSIONS
    if is_audio and audio_duration_seconds is not None:
        if audio_duration_seconds <= 0:
            raise ValidationDomainError("La duración de la nota de voz debe ser mayor a 0 segundos.")
        if audio_duration_seconds > MAX_AUDIO_DURATION_SECONDS:
            raise ValidationDomainError(
                f"La nota de voz ({audio_duration_seconds:.0f} s) supera el máximo permitido de {MAX_AUDIO_DURATION_SECONDS} s."
            )

    return {
        "sanitized_name": clean_name,
        "extension": ext,
        "mime_type": detected_mime,
        "size_bytes": size_bytes,
        "is_audio": is_audio,
        "sha256_hash": hashlib.sha256(content_bytes).hexdigest(),
    }
