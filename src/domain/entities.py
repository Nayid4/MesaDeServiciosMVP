"""Entidades del dominio CASAGBI (Mesa de Servicios TIC UPC - ITIL v4)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """Representa un usuario institucional o miembro del equipo TIC de la UPC."""

    id: Optional[int]
    email: str
    full_name: str
    role: str
    area: Optional[str]
    sede: str
    is_active: bool = True
    privacy_accepted: bool = False
    last_assigned_at: Optional[str] = None
    created_at: Optional[str] = None
    password_hash: Optional[str] = field(default=None, repr=False)


@dataclass
class RefreshToken:
    """Token opaco de refresco persistido para rotación segura de sesiones."""

    id: Optional[int]
    user_id: int
    token_hash: str
    expires_at: str
    revoked: bool = False
    created_at: Optional[str] = None


@dataclass
class Ticket:
    """Ticket institucional de incidencia o solicitud de servicio TIC."""

    id: Optional[int]
    ticket_number: str
    title: str
    description: str
    ticket_type: str
    service_name: str
    area: str
    sede: str
    location: str
    impact: str
    urgency: str
    priority: str
    status: str
    requester_id: int
    requester_email: str
    requester_role: str
    assigned_tech_id: Optional[int] = None
    assigned_tech_email: Optional[str] = None
    sla_response_hours: float = 4.0
    sla_resolution_hours: float = 24.0
    response_deadline: Optional[str] = None
    resolution_deadline: Optional[str] = None
    first_response_at: Optional[str] = None
    paused_at: Optional[str] = None
    paused_seconds: int = 0
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    diagnosis: Optional[str] = None
    solution: Optional[str] = None
    closing_category: Optional[str] = None
    csat_score: Optional[int] = None
    csat_comment: Optional[str] = None
    ai_suggested_service: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_human_validated: bool = False
    priority_justification: Optional[str] = None
    sla_breached: bool = False
    sla_alert_75_sent: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TicketMessage:
    """Mensaje del canal de comunicación interno de un ticket."""

    id: Optional[int]
    ticket_id: int
    sender_id: int
    sender_email: str
    sender_role: str
    message: str
    attachment_name: Optional[str] = None
    attachment_path: Optional[str] = None
    is_read: bool = False
    created_at: Optional[str] = None


@dataclass
class TicketHistory:
    """Registro cronológico de eventos y transiciones de estado de un ticket."""

    id: Optional[int]
    ticket_id: int
    actor_email: str
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    comment: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class KnowledgeArticle:
    """Artículo técnico o público de la Base de Conocimiento institucional."""

    id: Optional[int]
    code: str
    title: str
    service_name: str
    symptoms: str
    solution_steps: str
    keywords: str
    visibility: str = "Pública"
    status: str = "Publicado"
    version: int = 1
    author_email: str = "coordinador@unicesar.edu.co"
    reviewer_email: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class AuditLog:
    """Registro inmutable (append-only) de auditoría para control interno."""

    id: Optional[int]
    timestamp: str
    user_email: str
    ip_address: str
    action: str
    entity: str
    entity_id: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class Notification:
    """Notificación en plataforma para usuarios y equipo técnico."""

    id: Optional[int]
    user_email: str
    ticket_number: Optional[str]
    title: str
    message: str
    is_read: bool = False
    created_at: Optional[str] = None
