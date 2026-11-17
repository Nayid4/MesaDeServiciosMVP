"""Servicio de hashing bcrypt y validación de complejidad de contraseñas."""

from __future__ import annotations

import re

from src.domain.exceptions import ValidationError
from src.infrastructure.security.password_hasher import hash_password, verify_password


def validate_password_complexity(plain_password: str) -> str:
    """Valida reglas mínimas: >=8 caracteres, mayúscula, minúscula y dígito/símbolo."""
    pwd = plain_password or ""
    if len(pwd) < 8:
        raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Z]", pwd) or not re.search(r"[a-z]", pwd):
        raise ValidationError("La contraseña debe combinar letras mayúsculas y minúsculas.")
    if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>_\-+=/\\[\]]", pwd):
        raise ValidationError("La contraseña debe incluir al menos un número o carácter especial.")
    return pwd


__all__ = ["hash_password", "validate_password_complexity", "verify_password"]
