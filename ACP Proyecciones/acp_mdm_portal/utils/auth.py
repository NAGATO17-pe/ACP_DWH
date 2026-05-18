"""
Autenticacion y control de acceso del portal MDM ACP.

La autenticacion se delega al backend FastAPI via JWT.
Este modulo solo administra la sesion local de Streamlit.
"""

from __future__ import annotations

import base64
import json
import time

import streamlit as st


_AVATARES_ROL: dict[str, str] = {
    "admin": "ADM",
    "analista_mdm": "MDM",
    "operador_etl": "ETL",
    "viewer": "USR",
}

_PERMISOS: dict[str, set[str]] = {
    "admin": {"leer", "escribir", "configurar", "ejecutar_etl", "admin"},
    "analista_mdm": {"leer", "escribir"},
    "operador_etl": {"leer", "ejecutar_etl"},
    "viewer": {"leer"},
}


def tiene_permiso(accion: str) -> bool:
    usuario = obtener_usuario()
    if usuario is None:
        return False
    rol = usuario.get("rol", "viewer")
    return accion in _PERMISOS.get(rol, set())



def obtener_usuario() -> dict | None:
    if st.session_state.get("autenticado"):
        return {
            "username": st.session_state.get("username", ""),
            "nombre": st.session_state.get("nombre_usuario", ""),
            "rol": st.session_state.get("rol_usuario", "viewer"),
            "avatar": st.session_state.get("avatar_usuario", "USR"),
        }
    return None



# TTL de sesión local — sincronizar con ACP_JWT_TTL_MIN del backend (default 480 min = 8 h)
_SESSION_MAX_SEG = 8 * 3600


def _token_expirado() -> bool:
    """Verifica si el token JWT local ha expirado por tiempo de sesión o por el campo exp."""
    if time.time() - st.session_state.get("login_time", 0) > _SESSION_MAX_SEG:
        return True
    token = st.session_state.get("jwt_token", "")
    if not token:
        return True
    try:
        partes = token.split(".")
        if len(partes) != 3:
            return True
        padding = partes[1] + "=" * (4 - len(partes[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padding))
        exp = payload.get("exp", 0)
        if exp and time.time() > exp:
            return True
    except Exception:
        return True
    return False


def cerrar_sesion() -> None:
    _claves_auth = [
        "autenticado", "username", "nombre_usuario", "rol_usuario",
        "avatar_usuario", "login_error", "login_time", "jwt_token",
    ]
    _claves_app = [
        "etl_en_ejecucion", "etl_id_corrida", "etl_log", "etl_estado_final",
        "etl_pasos_lista", "etl_fase_actual", "etl_paso_num", "etl_total_pasos",
        "etl_archivo_listo", "health_historial", "health_refresh_interval",
        "health_last_refresh", "current_page",
    ]
    for key in _claves_auth + _claves_app:
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if key.startswith(("pg_", "pend_", "nav_", "aud_", "editor_")):
            st.session_state.pop(key, None)



def _validar_credenciales(username: str, password: str) -> dict | None:
    from utils.api_client import login_backend, mostrar_error_api

    resultado = login_backend(username, password)
    if not resultado.ok:
        if resultado.status_code not in (401, 403):
            mostrar_error_api(resultado, "No se pudo autenticar contra el backend.")
        return None

    datos_login = resultado.data if isinstance(resultado.data, dict) else {}
    token = datos_login.get("access_token")
    perfil = datos_login.get("usuario") or {}
    if not token:
        return None

    rol = perfil.get("rol") or "viewer"
    nombre_display = perfil.get("nombre_display") or username.strip()
    nombre_usuario = perfil.get("nombre_usuario") or username.lower().strip()
    return {
        "username": nombre_usuario,
        "nombre": nombre_display,
        "rol": rol,
        "avatar": _AVATARES_ROL.get(rol, "USR"),
        "token": token,
    }


_LOGIN_CSS = """
<style>
section[data-testid="stSidebar"], header[data-testid="stHeader"], footer {
    display: none !important;
}
.stApp {
    background:
        radial-gradient(ellipse at 20% 10%, rgba(27,107,90,0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 85%, rgba(212,145,94,0.05) 0%, transparent 50%),
        linear-gradient(170deg, #FAFBFC 0%, #F1F5F4 40%, #F5F3F0 100%) !important;
}
div[data-testid="stForm"] {
    max-width: 400px;
    margin: 8vh auto 0 auto;
    padding: 32px 30px 28px 30px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(20px) saturate(1.3);
    -webkit-backdrop-filter: blur(20px) saturate(1.3);
    border: 1px solid rgba(255, 255, 255, 0.5);
    box-shadow: 0 16px 48px rgba(27, 107, 90, 0.10), 0 2px 8px rgba(0,0,0,0.04);
    animation: loginSlideIn 0.5s ease-out;
}
@keyframes loginSlideIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.login-logo {
    text-align: center;
    margin-bottom: 20px;
}
.login-logo h2 {
    font-family: 'Outfit', 'Inter', sans-serif;
    color: #1B6B5A;
    margin: 0;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.login-logo p {
    color: #64748B;
    margin: 6px 0 0 0;
    font-size: 0.8rem;
    letter-spacing: 0.2px;
}
.login-label {
    color: #374151;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 10px 0 4px 0;
}
.login-error {
    background: rgba(254, 243, 242, 0.9);
    border: 1px solid #FECACA;
    color: #B42318;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 0.84rem;
    font-weight: 500;
}
.login-footer-out {
    text-align: center;
    color: #94A3B8;
    font-size: 0.76rem;
    margin-top: 20px;
    letter-spacing: 0.2px;
}
</style>
"""



def _render_login() -> bool:
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.markdown(
            """
            <div class="login-logo">
                <h2>ACP MDM Portal</h2>
                <p>Data Quality - Enterprise</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("login_error"):
            st.markdown(
                '<div class="login-error">Credenciales invalidas.</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="login-label">Usuario</div>', unsafe_allow_html=True)
        username = st.text_input(
            "Usuario",
            key="login_username",
            placeholder="ej: usuario",
            label_visibility="collapsed",
        )

        st.markdown('<div class="login-label">Contrasena</div>', unsafe_allow_html=True)
        password = st.text_input(
            "Contrasena",
            key="login_password",
            type="password",
            placeholder="********",
            label_visibility="collapsed",
        )

        submit = st.form_submit_button("Iniciar sesion", type="primary", width='stretch')
        if submit:
            user = _validar_credenciales(username, password)
            if user:
                st.session_state["autenticado"] = True
                st.session_state["username"] = user["username"]
                st.session_state["nombre_usuario"] = user["nombre"]
                st.session_state["rol_usuario"] = user["rol"]
                st.session_state["avatar_usuario"] = user["avatar"]
                st.session_state["jwt_token"] = user.get("token")
                st.session_state["login_time"] = time.time()
                st.session_state["login_error"] = False
                st.rerun()
            else:
                st.session_state["login_error"] = True
                st.rerun()

    st.markdown(
        """
        <div class="login-footer-out">
            ACP Equipo de Proyecciones - 2026
        </div>
        """,
        unsafe_allow_html=True,
    )
    return False



def login_gate() -> bool:
    if st.session_state.get("autenticado"):
        if _token_expirado():
            cerrar_sesion()
            st.warning("Tu sesión ha expirado. Por favor inicia sesión nuevamente.")
            _render_login()
            return False
        return True
    _render_login()
    return False
