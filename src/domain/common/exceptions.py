"""Excepciones puras del dominio CASAGBI mapeables a RFC 7807 Problem Details."""

from __future__ import annotations

from typing import Optional


class DomainError(Exception):
    """Excepción base de reglas de negocio e invariantes de dominio."""

    def __init__(
        self,
        detail: str,
        *,
        code: str = "domain-error",
        title: str = "Error de regla de negocio",
        status_code: int = 400,
        type_uri: Optional[str] = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.title = title
        self.status_code = status_code
        self.detail = detail
        self.type_uri = type_uri or f"https://casagbi.unicesar.edu.co/problems/{code}"


class ValidationDomainError(DomainError):
    """Error de validación semántica sobre entidades o invariantes (HTTP 422)."""

    def __init__(self, detail: str, title: str = "Error de validación de dominio") -> None:
        super().__init__(detail, code="validation-error", title=title, status_code=422)


class InvalidTransitionError(DomainError):
    """Violación al grafo de ciclo de vida ITIL v4 o estado terminal (HTTP 409)."""

    def __init__(self, detail: str, title: str = "Transición de estado no permitida") -> None:
        super().__init__(detail, code="invalid-itil-transition", title=title, status_code=409)


class NotFoundError(DomainError):
    """Recurso o agregado no encontrado (HTTP 404)."""

    def __init__(self, detail: str, title: str = "Recurso no encontrado") -> None:
        super().__init__(detail, code="resource-not-found", title=title, status_code=404)


class UnauthorizedError(DomainError):
    """Credenciales inválidas, token expirado o ausencia de autenticación (HTTP 401)."""

    def __init__(self, detail: str, title: str = "No autenticado") -> None:
        super().__init__(detail, code="unauthorized", title=title, status_code=401)


class ForbiddenError(DomainError):
    """Violación de control de acceso basado en rol RBAC o propiedad (HTTP 403)."""

    def __init__(
        self,
        detail: str,
        title: str = "Acceso denegado (RBAC)",
        *,
        code: str = "forbidden-rbac",
    ) -> None:
        super().__init__(detail, code=code, title=title, status_code=403)


class EditWindowExpiredError(ForbiddenError):
    """Ventana de edición de mensaje (5 minutos) expirada (HTTP 403)."""

    def __init__(
        self,
        detail: str = "Solo se permite editar un mensaje dentro de los primeros 5 minutos (300 s) posteriores a su envío.",
        title: str = "Ventana de edición expirada",
    ) -> None:
        super().__init__(detail, title=title, code="EDIT_WINDOW_EXPIRED")


class TooManyRequestsError(DomainError):
    """Bloqueo temporal por exceso de intentos fallidos (HTTP 429)."""

    def __init__(self, detail: str, title: str = "Demasiados intentos fallidos") -> None:
        super().__init__(detail, code="TOO_MANY_ATTEMPTS", title=title, status_code=429)


class InvalidAttachmentSignatureError(ValidationDomainError):
    """Archivo rechazado por no coincidir sus magic bytes con la extensión permitida (HTTP 422)."""

    def __init__(
        self,
        detail: str,
        title: str = "Archivo rechazado por validación binaria",
    ) -> None:
        super().__init__(detail, title=title)
        self.code = "INVALID_FILE_SIGNATURE"
        self.type_uri = "https://casagbi.unicesar.edu.co/problems/INVALID_FILE_SIGNATURE"


class ConflictError(DomainError):
    """Conflicto de unicidad o concurrencia de negocio (HTTP 409)."""

    def __init__(self, detail: str, title: str = "Conflicto de recurso") -> None:
        super().__init__(detail, code="resource-conflict", title=title, status_code=409)


class AIServiceUnavailableError(DomainError):
    """Indisponibilidad controlada del motor NLP/IA según RNF-06 (HTTP 503)."""

    def __init__(
        self,
        detail: str = "El motor de Inteligencia Artificial no está disponible temporalmente. Puede radicar su ticket manualmente.",
        title: str = "Servicio de IA temporalmente no disponible",
    ) -> None:
        super().__init__(detail, code="ai-service-unavailable", title=title, status_code=503)


ValidationError = ValidationDomainError
