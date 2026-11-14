"""Vista de inicio de sesión institucional (@unicesar.edu.co), registro y gestión JWT."""

from __future__ import annotations

import streamlit as st

from dashboard.shared.components import render_breadcrumbs, render_section_header
from dashboard.shared.icons import svg_icon
from dashboard.shared.store import LifecycleManager, StoreManager, get_auth_service
from dashboard.shared.styles import UPC_GREEN
from src.domain.rules import ROLE_LABELS, UPC_SEDES, is_valid_institutional_email
from src.infrastructure.security import decode_access_token

DEMO_CREDENTIALS = [
    ("Estudiante", "estudiante@unicesar.edu.co", "User2026*", "usuario"),
    ("Docente", "docente@unicesar.edu.co", "User2026*", "usuario"),
    ("Técnico Redes", "tecnico1@unicesar.edu.co", "Tecnico2026*", "tecnico"),
    ("Técnico Sistemas", "tecnico2@unicesar.edu.co", "Tecnico2026*", "tecnico"),
    ("Coordinador Mesa", "coordinador@unicesar.edu.co", "Coord2026*", "coordinador"),
    ("Director TIC", "director@unicesar.edu.co", "Director2026*", "director"),
    ("Administrador", "admin@unicesar.edu.co", "Admin2026*", "admin"),
]


def _default_route_for_role(role: str) -> str:
    if role == "usuario":
        return "create_ticket"
    if role == "tecnico":
        return "manage_tickets"
    if role in ("coordinador", "director", "admin"):
        return "kpi_dashboard"
    return "landing"


def render() -> None:
    auth = StoreManager.auth()
    auth_svc = get_auth_service()

    col_back, _ = st.columns([1.4, 4.6])
    with col_back:
        if not auth.is_authenticated:
            if st.button("Volver al Portal Público", use_container_width=True, key="auth_back_landing"):
                LifecycleManager.on_route_change("landing")
                st.rerun()

    render_breadcrumbs(["CASAGBI UPC", "Acceso Institucional"])
    render_section_header(
        "Acceso Institucional CASAGBI · UPC",
        "Autenticación segura con JWT Access Token (15 min) + Refresh Token rotativo y control estricto RBAC.",
        icon_name="lock",
    )

    if auth.is_authenticated and auth.user:
        u = auth.user
        st.success(
            f"Sesión activa como **{u['full_name']}** (`{u['email']}` · Rol: `{ROLE_LABELS.get(u['role'], u['role'])}`)."
        )

        col_info, col_actions = st.columns([2, 1])
        with col_info:
            claims = {}
            try:
                claims = decode_access_token(auth.access_token or "")
            except Exception:
                claims = {"estado": "Token pendiente de rotación"}
            with st.expander("Estado del ciclo de vida JWT + Refresh Token", expanded=True):
                st.json(
                    {
                        "sub": claims.get("sub"),
                        "email": claims.get("email"),
                        "role": claims.get("role"),
                        "area": claims.get("area"),
                        "exp_unix": claims.get("exp"),
                        "renovaciones_silenciosas": auth.token_refreshed_count,
                        "refresh_token_activo": bool(auth.refresh_token),
                    }
                )
        with col_actions:
            if st.button("Ir a mi espacio de trabajo", type="primary", use_container_width=True, key="auth_go_home"):
                LifecycleManager.on_route_change(_default_route_for_role(u["role"]))
                st.rerun()
            if st.button("Cerrar sesión de forma segura", use_container_width=True, key="auth_logout_btn"):
                auth_svc.logout(u["email"], auth.refresh_token)
                StoreManager.clear_auth_session(notice="Sesión cerrada y Refresh Token revocado en SQLite.")
                LifecycleManager.on_route_change("landing")
                st.rerun()
        return

    tab_login, tab_register = st.tabs(["Iniciar Sesión (@unicesar.edu.co)", "Registro Rápido Institucional"])

    with tab_login:
        col_form, col_info_sec = st.columns([1.4, 1.0])
        with col_form:
            email = st.text_input(
                "Correo institucional *",
                placeholder="usuario@unicesar.edu.co",
                key="login_email_live",
            )
            if email.strip():
                if is_valid_institutional_email(email):
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#166534;font-weight:600;margin-bottom:0.4rem;'>"
                        f"{svg_icon('check-circle', size=14, color='#166534')} Dominio institucional @unicesar.edu.co verificado"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#991B1B;font-weight:600;margin-bottom:0.4rem;'>"
                        f"{svg_icon('x-circle', size=14, color='#991B1B')} Solo se permiten cuentas @unicesar.edu.co"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            password = st.text_input("Contraseña *", type="password", placeholder="••••••••", key="login_pwd_live")
            submitted = st.button("Ingresar con cuenta institucional", type="primary", use_container_width=True, key="login_submit_btn")

            if submitted:
                try:
                    session = auth_svc.login(email, password)
                    StoreManager.set_authenticated_session(
                        user=session["user"],
                        access_token=session["access_token"],
                        refresh_token=session["refresh_token"],
                        notice=f"Bienvenido(a), {session['user']['full_name']}.",
                    )
                    LifecycleManager.on_route_change(_default_route_for_role(session["user"]["role"]))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        with col_info_sec:
            st.markdown(
                f"""<div class="upc-card-accent">
<div style="font-weight:700;color:{UPC_GREEN};display:flex;align-items:center;gap:0.45rem;margin-bottom:0.45rem;">
{svg_icon('shield-check', size=18, color=UPC_GREEN)}<span>Seguridad de Sesión CASAGBI</span>
</div>
<ul style="font-size:0.88rem;color:#475569;padding-left:1.1rem;margin:0;">
<li>Token de acceso JWT firmado (HS256, expiración 15 min).</li>
<li>Refresh Token rotativo almacenado con hash SHA-256 en SQLite.</li>
<li>Cierre automático tras 30 minutos de inactividad.</li>
<li>Control de acceso estricto por rol (RBAC) auditado.</li>
</ul>
</div>""",
                unsafe_allow_html=True,
            )

        st.divider()
        st.subheader("Accesos rápidos de evaluación por rol (Sustentación MVP)")
        st.caption("Permite validar el Workspace privado por rol, matriz RBAC, flujos ITIL y métricas sin digitar contraseñas.")
        cols = st.columns(4)
        for idx, (label, d_email, d_pwd, d_role) in enumerate(DEMO_CREDENTIALS):
            with cols[idx % 4]:
                if st.button(label, key=f"demo_login_{d_email}", use_container_width=True):
                    try:
                        session = auth_svc.login(d_email, d_pwd)
                        StoreManager.set_authenticated_session(
                            user=session["user"],
                            access_token=session["access_token"],
                            refresh_token=session["refresh_token"],
                            notice=f"Sesión iniciada como {label} ({d_email}).",
                        )
                        LifecycleManager.on_route_change(_default_route_for_role(d_role))
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error en acceso rápido: {exc}")

    with tab_register:
        st.info("Solo se permiten correos institucionales `@unicesar.edu.co` (RF-01 / OR-05).")
        with st.form("register_form"):
            r_name = st.text_input("Nombre completo *")
            r_email = st.text_input("Correo institucional *", placeholder="nombre.apellido@unicesar.edu.co")
            r_sede = st.selectbox("Sede principal *", UPC_SEDES)
            r_pass = st.text_input("Contraseña (mín. 8 caracteres) *", type="password")
            r_privacy = st.checkbox(
                "Acepto el aviso de privacidad y la política de tratamiento de datos personales de la UPC (Ley 1581 de 2012)."
            )
            r_submit = st.form_submit_button("Crear cuenta institucional", type="primary")

        if r_submit:
            try:
                session = auth_svc.register_institutional_user(
                    email=r_email,
                    full_name=r_name,
                    password=r_pass,
                    sede=r_sede,
                    privacy_accepted=r_privacy,
                )
                StoreManager.set_authenticated_session(
                    user=session["user"],
                    access_token=session["access_token"],
                    refresh_token=session["refresh_token"],
                    notice="Cuenta institucional creada exitosamente.",
                )
                LifecycleManager.on_route_change("create_ticket")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
