"""Entrypoint principal FastAPI para CASAGBI — Mesa de Servicios TIC UPC (ITIL v4)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.bootstrap import ensure_system_bootstrapped
from src.presentation.api.middlewares.problem_details_handler import (
    register_problem_details_handlers,
)
from src.presentation.api.middlewares.trace_middleware import TraceMiddleware
from src.presentation.api.v1.ai_agent_router import router as ai_agent_router
from src.presentation.api.v1.analytics_router import router as analytics_router
from src.presentation.api.v1.auth_router import router as auth_router
from src.presentation.api.v1.kb_router import router as kb_router
from src.presentation.api.v1.tickets_chat_router import router as tickets_chat_router
from src.presentation.api.v1.tickets_public_router import router as tickets_public_router
from src.presentation.api.v1.tickets_router import router as tickets_router
from src.presentation.api.v1.users_router import router as users_router
from src.presentation.api.v1.ws_router import router as ws_router

WEB_DIR = Path(__file__).resolve().parent / "presentation" / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_system_bootstrapped()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="CASAGBI — Mesa de Servicios TIC UPC (ITIL v4)",
        version="2.0.0",
        description="Monolito Clean Architecture + CQRS + Unit of Work + WebSockets + ML NLP",
        lifespan=lifespan,
    )

    application.add_middleware(TraceMiddleware)
    register_problem_details_handlers(application)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    for router in (
        auth_router,
        users_router,
        tickets_public_router,
        tickets_router,
        tickets_chat_router,
        ai_agent_router,
        analytics_router,
        kb_router,
        ws_router,
    ):
        application.include_router(router)

    @application.get("/health", tags=["Sistema"])
    def healthcheck() -> dict:
        return {"status": "ok", "service": "CASAGBI-UPC-ITIL4"}

    @application.get("/", response_class=HTMLResponse, tags=["Web UI"])
    def landing_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={"page_title": "CASAGBI · Mesa de Servicios TIC UPC"},
        )

    @application.get("/login", response_class=HTMLResponse, tags=["Web UI"])
    def login_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"page_title": "Ingreso Institucional · CASAGBI UPC"},
        )

    @application.get("/dashboard", response_class=HTMLResponse, tags=["Web UI"])
    def dashboard_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"page_title": "Workspace Operativo · CASAGBI UPC"},
        )

    @application.get("/ticket-track/{code}", response_class=HTMLResponse, tags=["Web UI"])
    def public_ticket_track_page(request: Request, code: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="public_ticket.html",
            context={"page_title": f"Seguimiento {code.upper()} · CASAGBI UPC", "ticket_code": code.upper()},
        )

    @application.get("/reset-password", response_class=HTMLResponse, tags=["Web UI"])
    def reset_password_page(request: Request, token: str = "") -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context={"page_title": "Restablecer Contraseña · CASAGBI UPC", "reset_token": token},
        )

    return application


app = create_app()
