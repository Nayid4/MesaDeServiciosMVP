"""
Gestión centralizada de estado (Stores), Ciclos de Vida y Lazy Loading para CASAGBI.

Stores desacoplados sobre st.session_state:
- AuthStore: Sesión JWT, Refresh Token, usuario autenticado y control de inactividad (30m).
- NavigationStore: Ruta activa, historial de navegación y parámetros de transición.
- TicketStore: Filtros, paginación, versión de caché reactiva y borrador de predicción IA.
- AIAssistantStore: Historial conversacional, intentos fallidos, simulación RNF-06 y prefill.
- NotificationStore: Conteo de no leídas y bandeja rápida de avisos en plataforma.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.application.ai_use_cases import AIService
from src.application.auth_use_cases import AuthService
from src.application.ticket_use_cases import TicketService
from src.bootstrap import ensure_system_bootstrapped
from src.cleaning import DEFAULT_CLEAN_PATH, DEFAULT_EXCLUDED_PATH
from src.infrastructure.container import get_container, reset_container

SESSION_INACTIVITY_TIMEOUT_SEC = 30 * 60  # 30 minutos (RF-01 / HU-01 / RNF-07)
_STORE_ROOT_KEY = "_casagbi_stores"


@dataclass
class AuthStore:
    is_authenticated: bool = False
    user: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    last_activity_ts: float = 0.0
    token_refreshed_count: int = 0
    last_auth_notice: Optional[str] = None


@dataclass
class NavigationStore:
    current_route: str = "landing"
    previous_route: Optional[str] = None
    selected_ticket_number: Optional[str] = None
    prefill_ticket_data: Optional[Dict[str, Any]] = None
    route_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TicketStore:
    status_filter: str = "Todos"
    priority_filter: str = "Todas"
    sede_filter: str = "Todas"
    search_query: str = ""
    page: int = 1
    page_size: int = 10
    cache_version: int = 1
    ai_draft_prediction: Optional[Dict[str, Any]] = None


@dataclass
class AIAssistantStore:
    messages: List[Dict[str, Any]] = field(default_factory=list)
    failed_attempts: int = 0
    simulate_ai_failure: bool = False
    pending_prefill: Optional[Dict[str, Any]] = None
    pending_draft_card: Optional[Dict[str, Any]] = None
    last_prediction: Optional[Dict[str, Any]] = None


@dataclass
class NotificationStore:
    unread_count: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)
    last_version: int = 0


class StoreManager:
    """Fachada tipada para leer y mutar los stores de sesión sin dispersar claves."""

    @staticmethod
    def ensure_initialized() -> Dict[str, Any]:
        if _STORE_ROOT_KEY not in st.session_state:
            st.session_state[_STORE_ROOT_KEY] = {
                "auth": AuthStore(),
                "nav": NavigationStore(),
                "tickets": TicketStore(),
                "ai": AIAssistantStore(),
                "notifications": NotificationStore(),
                "bootstrapped": False,
            }
        return st.session_state[_STORE_ROOT_KEY]

    @classmethod
    def auth(cls) -> AuthStore:
        return cls.ensure_initialized()["auth"]

    @classmethod
    def nav(cls) -> NavigationStore:
        return cls.ensure_initialized()["nav"]

    @classmethod
    def tickets(cls) -> TicketStore:
        return cls.ensure_initialized()["tickets"]

    @classmethod
    def ai(cls) -> AIAssistantStore:
        return cls.ensure_initialized()["ai"]

    @classmethod
    def notifications(cls) -> NotificationStore:
        return cls.ensure_initialized()["notifications"]

    @classmethod
    def set_authenticated_session(
        cls,
        user: Dict[str, Any],
        access_token: str,
        refresh_token: str,
        notice: Optional[str] = None,
    ) -> None:
        auth = cls.auth()
        auth.is_authenticated = True
        auth.user = user
        auth.access_token = access_token
        auth.refresh_token = refresh_token
        auth.last_activity_ts = time.time()
        auth.last_auth_notice = notice

    @classmethod
    def clear_auth_session(cls, notice: Optional[str] = None) -> None:
        root = cls.ensure_initialized()
        root["auth"] = AuthStore(last_auth_notice=notice)
        root["notifications"] = NotificationStore()
        root["ai"] = AIAssistantStore()
        root["tickets"] = TicketStore()
        root["nav"] = NavigationStore(current_route="landing")

    @classmethod
    def snapshot(cls) -> Dict[str, Any]:
        root = cls.ensure_initialized()
        return {
            "auth": {
                "is_authenticated": root["auth"].is_authenticated,
                "user_email": (root["auth"].user or {}).get("email"),
                "role": (root["auth"].user or {}).get("role"),
                "token_refreshed_count": root["auth"].token_refreshed_count,
            },
            "nav": asdict(root["nav"]),
            "tickets_cache_version": root["tickets"].cache_version,
        }


# --- Recursos cacheados (Lazy Loading de infraestructura pesada) ---

@st.cache_resource(show_spinner="Inicializando plataforma CASAGBI (primera ejecución)...")
def cached_system_bootstrap() -> Dict[str, Any]:
    """Bootstrap único por proceso: asegura dataset 18k, limpieza, modelos ML y SQLite."""
    return ensure_system_bootstrapped()


@st.cache_resource(show_spinner=False)
def get_lazy_ai_service() -> AIService:
    """Instancia compartida con carga perezosa desde el Contenedor DI."""
    return get_container().ai_service


def get_auth_service() -> AuthService:
    """Retorna AuthService cableado por el Contenedor DI."""
    return get_container().auth_service


def get_ticket_service() -> TicketService:
    """Retorna TicketService cableado por el Contenedor DI."""
    return get_container().ticket_service


@st.cache_data(ttl=120, show_spinner=False)
def load_clean_dataset_cached(cache_version: int = 1) -> pd.DataFrame:
    """Carga perezosa y cacheada del dataset analítico limpio para el Dashboard/Lab."""
    _ = cache_version
    path = Path(DEFAULT_CLEAN_PATH)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8")


@st.cache_data(ttl=120, show_spinner=False)
def load_excluded_dataset_cached(cache_version: int = 1) -> pd.DataFrame:
    """Carga perezosa y cacheada de registros excluidos en la auditoría CRISP-DM."""
    _ = cache_version
    path = Path(DEFAULT_EXCLUDED_PATH)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8")


class LifecycleManager:
    """Controlador determinista de ciclos de vida de la UI en Streamlit."""

    @staticmethod
    def on_app_bootstrap() -> None:
        StoreManager.ensure_initialized()
        root = st.session_state[_STORE_ROOT_KEY]
        if not root["bootstrapped"]:
            cached_system_bootstrap()
            root["bootstrapped"] = True

    @staticmethod
    def on_request_start(auth_service: Optional[AuthService] = None) -> None:
        """
        Hook ejecutado al inicio de cada render:
        1. Verifica timeout de inactividad (30 minutos).
        2. Verifica validez del JWT Access Token y rota silenciosamente con Refresh Token si expiró.
        """
        auth = StoreManager.auth()
        if not auth.is_authenticated:
            return

        now_ts = time.time()
        if auth.last_activity_ts and (now_ts - auth.last_activity_ts) > SESSION_INACTIVITY_TIMEOUT_SEC:
            svc = auth_service or get_auth_service()
            svc.logout(
                (auth.user or {}).get("email"),
                auth.refresh_token,
            )
            StoreManager.clear_auth_session(
                notice="Su sesión se cerró automáticamente tras 30 minutos de inactividad (RF-01)."
            )
            StoreManager.nav().current_route = "auth"
            return

        svc = auth_service or get_auth_service()
        validation = svc.verify_or_refresh_session(auth.access_token, auth.refresh_token)
        if not validation["valid"]:
            StoreManager.clear_auth_session(
                notice=f"Sesión finalizada: {validation.get('reason', 'Token inválido')}."
            )
            StoreManager.nav().current_route = "auth"
            return

        auth.user = validation["user"]
        auth.access_token = validation["access_token"]
        auth.refresh_token = validation["refresh_token"]
        auth.last_activity_ts = now_ts
        if validation.get("refreshed"):
            auth.token_refreshed_count += 1
            auth.last_auth_notice = (
                "Access Token JWT renovado silenciosamente mediante Refresh Token rotativo."
            )

    @staticmethod
    def on_route_change(
        target_route: str,
        preserve_prefill: bool = False,
        selected_ticket: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Transición limpia de rutas: resetea estados transitorios de la vista saliente."""
        nav = StoreManager.nav()
        t_store = StoreManager.tickets()

        if nav.current_route != target_route:
            nav.previous_route = nav.current_route
            nav.current_route = target_route
            t_store.page = 1
            t_store.ai_draft_prediction = None
            if not preserve_prefill:
                nav.prefill_ticket_data = None

        if selected_ticket is not None:
            nav.selected_ticket_number = selected_ticket
        nav.route_params = params or {}

    @staticmethod
    def invalidate_caches(clear_data: bool = True, clear_ai_model: bool = False) -> None:
        """Invalida caches reactivamente después de cualquier mutación de datos o modelo."""
        t_store = StoreManager.tickets()
        t_store.cache_version += 1
        n_store = StoreManager.notifications()
        n_store.last_version = 0
        if clear_data:
            load_clean_dataset_cached.clear()
            load_excluded_dataset_cached.clear()
        if clear_ai_model:
            get_lazy_ai_service().invalidate_model_cache()
            get_lazy_ai_service.clear()
            reset_container()
