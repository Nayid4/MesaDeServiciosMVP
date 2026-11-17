"""Hashing seguro y verificación de contraseñas institucionales mediante bcrypt."""

from __future__ import annotations

import bcrypt


def hash_password(plain_password: str) -> str:
    """Genera hash bcrypt seguro con salt aleatorio."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False
