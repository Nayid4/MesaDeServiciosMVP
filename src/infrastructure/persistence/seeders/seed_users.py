"""Seeder idempotente de catálogo de servicios UPC, tabla SLA OR-03 y usuarios demo."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.rules import SLA_BY_PRIORITY, UPC_SERVICE_CATALOG, get_service_prefix
from src.infrastructure.persistence.models import SLAConfigORM, ServiceCatalogORM, UserORM
from src.infrastructure.security.password_hasher import hash_password

SEED_USERS = [
    ("admin@unicesar.edu.co", "Carlos Mendoza (Administrador)", "Admin2026*", "admin", "Oficina de Informática y Sistemas", "Sede Sabanas (Valledupar)"),
    ("coordinador@unicesar.edu.co", "Kathy Sagbini (Coordinadora Mesa)", "Coord2026*", "coordinador", "Oficina de Informática y Sistemas", "Sede Sabanas (Valledupar)"),
    ("director@unicesar.edu.co", "Nayid Castellar (Director TIC)", "Director2026*", "director", "Dirección TIC", "Sede Sabanas (Valledupar)"),
    ("tecnico1@unicesar.edu.co", "Andrés Martínez (Redes)", "Tecnico2026*", "tecnico", "Redes e Infraestructura", "Sede Sabanas (Valledupar)"),
    ("tecnico2@unicesar.edu.co", "Laura Gómez (Sistemas)", "Tecnico2026*", "tecnico", "Sistemas de Información", "Sede Sabanas (Valledupar)"),
    ("tecnico3@unicesar.edu.co", "Mateo Rojas (Identidad)", "Tecnico2026*", "tecnico", "Identidad y Accesos", "Sede Sabanas (Valledupar)"),
    ("tecnico4@unicesar.edu.co", "Valentina Díaz (Soporte Campo)", "Tecnico2026*", "tecnico", "Soporte en Campo", "Sede Hurtado (Valledupar)"),
    ("tecnico5@unicesar.edu.co", "Julián Torres (Mesa Software)", "Tecnico2026*", "tecnico", "Mesa de Software", "Seccional Aguachica"),
    ("tecnico6@unicesar.edu.co", "Camila Herrera (Soporte Campo)", "Tecnico2026*", "tecnico", "Soporte en Campo", "Sede Sabanas (Valledupar)"),
    ("estudiante@unicesar.edu.co", "Sofía Paternina (Estudiante)", "User2026*", "usuario", None, "Sede Sabanas (Valledupar)"),
    ("docente@unicesar.edu.co", "Prof. Maribel Romero (Docente)", "User2026*", "usuario", None, "Sede Sabanas (Valledupar)"),
]


def seed_catalog_sla_and_users(session: Session, now_iso: str) -> None:
    """Precarga catálogo de servicios, acuerdos SLA y cuentas institucionales."""
    for svc_name, meta in UPC_SERVICE_CATALOG.items():
        prefix = get_service_prefix(svc_name)
        existing = session.scalars(
            select(ServiceCatalogORM).where(ServiceCatalogORM.service_name == svc_name)
        ).first()
        if existing is None:
            session.add(
                ServiceCatalogORM(
                    service_name=svc_name,
                    category_prefix=prefix,
                    area=meta["area"],
                    base_impact=meta["base_impact"],
                    default_type=meta["default_type"],
                    description=meta["description"],
                    is_active=True,
                )
            )
        elif not existing.category_prefix or existing.category_prefix == "GEN":
            existing.category_prefix = prefix

    for prio, vals in SLA_BY_PRIORITY.items():
        if session.get(SLAConfigORM, prio) is None:
            session.add(
                SLAConfigORM(
                    priority=prio,
                    sla_response_hours=vals["sla_response_hours"],
                    sla_resolution_hours=vals["sla_resolution_hours"],
                    updated_at=now_iso,
                )
            )
    session.flush()

    existing_emails = set(session.scalars(select(UserORM.email)).all())
    for email, name, pwd, role, area, sede in SEED_USERS:
        if email in existing_emails:
            continue
        session.add(
            UserORM(
                email=email,
                full_name=name,
                password_hash=hash_password(pwd),
                role=role,
                area=area,
                sede=sede,
                is_active=True,
                privacy_accepted=True,
                created_at=now_iso,
            )
        )
    session.flush()
