from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import streamlit as st

import os

# Misma fuente de vars que el backend, para que Streamlit (al ejecutarse aparte)
# no dependa solo del entorno heredado de acp_start.
try:
    from dotenv import load_dotenv

    _RAIZ_PORTAL = Path(__file__).resolve().parents[1]
    _RAIZ_PROYECTO = _RAIZ_PORTAL.parent
    load_dotenv(_RAIZ_PROYECTO / "backend" / ".env")
    load_dotenv(_RAIZ_PROYECTO / ".env")
except ImportError:
    pass

# Si no hay .env, 8000 coincide con el arranque típico de uvicorn en dev.
_DEFAULT_PUERTO_API = "8000"


def _fallback_backend_url() -> str:
    puerto = os.getenv("ACP_PUERTO", _DEFAULT_PUERTO_API)
    return f"http://127.0.0.1:{puerto}"


def _obtener_url_backend() -> str:
    # 1. Prioridad: st.secrets (configuración de streamlit)
    # 2. Prioridad: os.getenv (variables de entorno)
    # 3. Fallback: mismo host/puerto que ACP_PUERTO (backend/.env o launcher)
    fb = _fallback_backend_url()
    try:
        return st.secrets.get("BACKEND_URL") or os.getenv("BACKEND_URL") or fb
    except Exception:
        return os.getenv("BACKEND_URL") or fb


def obtener_url_backend() -> str:
    """URL base del API; se recalcula en cada llamada para respetar .env recién cargado."""
    return _obtener_url_backend()


def obtener_url_base_api() -> str:
    return f"{obtener_url_backend()}/api/v1"


# Compatibilidad: muchos módulos importan URL_BACKEND / URL_BASE.
URL_BACKEND = obtener_url_backend()
URL_BASE = obtener_url_base_api()
TIMEOUT_API_SEG = (5, 30)

_SESSION = requests.Session()


@dataclass(slots=True)
class ResultadoApi:
    ok: bool
    status_code: int | None
    data: Any = None
    error: str | None = None
    request_id: str | None = None
    url: str | None = None


def _get_headers(content_type: str = "application/json") -> dict[str, str]:
    headers = {"Content-Type": content_type}
    token = st.session_state.get("jwt_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _extraer_request_id(response: requests.Response, data: Any) -> str | None:
    request_id = response.headers.get("X-Request-ID")
    if request_id:
        return request_id
    if isinstance(data, dict):
        return data.get("request_id")
    return None


def _intentar_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _mensaje_error_http(status_code: int | None, data: Any) -> str:
    if isinstance(data, dict):
        for clave in ("mensaje", "detail", "error"):
            valor = data.get(clave)
            if valor:
                return str(valor)
    if status_code is None:
        return "Error desconocido de comunicación con el backend."
    return f"El backend respondió con estado HTTP {status_code}."


def _resultado_desde_respuesta(response: requests.Response) -> ResultadoApi:
    data = _intentar_json(response)
    ok = 200 <= response.status_code < 300
    return ResultadoApi(
        ok=ok,
        status_code=response.status_code,
        data=data,
        error=None if ok else _mensaje_error_http(response.status_code, data),
        request_id=_extraer_request_id(response, data),
        url=response.url,
    )


def _resultado_error(url: str, mensaje: str) -> ResultadoApi:
    return ResultadoApi(
        ok=False,
        status_code=None,
        data=None,
        error=mensaje,
        request_id=None,
        url=url,
    )


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: dict | None = None,
    data: dict | None = None,
    timeout: tuple[int, int] = TIMEOUT_API_SEG,
) -> ResultadoApi:
    try:
        response = _SESSION.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            data=data,
            timeout=timeout,
        )
        return _resultado_desde_respuesta(response)
    except requests.Timeout:
        return _resultado_error(url, "Timeout conectando al backend. Verifica el estado de la API.")
    except requests.RequestException as error:
        return _resultado_error(url, f"Error conectando al backend: {error}")


def mostrar_error_api(resultado: ResultadoApi, mensaje_base: str | None = None) -> None:
    partes = []
    if mensaje_base:
        partes.append(mensaje_base)
    if resultado.error:
        partes.append(resultado.error)
    if resultado.request_id:
        partes.append(f"request_id={resultado.request_id}")
    st.error(" | ".join(partes) if partes else "Error no controlado en la comunicación con el backend.")


def _headers_login_form() -> dict[str, str]:
    """OAuth2 password: sin Bearer (evita enviar un JWT caducado en el login)."""
    return {"Content-Type": "application/x-www-form-urlencoded"}


def login_backend(username: str, password: str) -> ResultadoApi:
    return _request(
        "POST",
        f"{obtener_url_backend()}/auth/login",
        data={"username": username, "password": password},
        headers=_headers_login_form(),
    )


def get_api(endpoint: str, base_url: str | None = None) -> ResultadoApi:
    bu = obtener_url_base_api() if base_url is None else base_url
    return _request("GET", f"{bu}{endpoint}", headers=_get_headers())


def post_api(endpoint: str, payload: dict, base_url: str | None = None) -> ResultadoApi:
    bu = obtener_url_base_api() if base_url is None else base_url
    return _request("POST", f"{bu}{endpoint}", json=payload, headers=_get_headers())


def patch_api(endpoint: str, payload: dict, base_url: str | None = None) -> ResultadoApi:
    bu = obtener_url_base_api() if base_url is None else base_url
    return _request("PATCH", f"{bu}{endpoint}", json=payload, headers=_get_headers())


def delete_api(endpoint: str, base_url: str | None = None) -> ResultadoApi:
    bu = obtener_url_base_api() if base_url is None else base_url
    return _request("DELETE", f"{bu}{endpoint}", headers=_get_headers())


def stream_api(id_corrida: str):
    """
    Lee el stream SSE de una corrida ETL línea a línea.

    Generador: yield str — cada línea de log emitida por el runner.
    Termina automáticamente cuando el servidor cierra la conexión
    o cuando el stream envía un evento con data '[DONE]'.

    Uso:
        for linea in stream_api(id_corrida):
            consola += linea + "\\n"
    """
    url = f"{obtener_url_base_api()}/etl/corridas/{id_corrida}/eventos"
    headers = _get_headers()
    headers.pop("Content-Type", None)          # SSE no lleva Content-Type
    headers["Accept"] = "text/event-stream"

    try:
        with _SESSION.get(url, headers=headers, stream=True, timeout=(5, 1800)) as resp:
            if not resp.ok:
                yield f"[ERROR] El servidor respondió {resp.status_code}"
                return

            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue                    # líneas vacías = separador SSE
                if raw_line.startswith("data:"):
                    payload = raw_line[5:].strip()
                    if payload == "[DONE]":
                        return
                    if payload:
                        yield payload
                elif raw_line.startswith("event:"):
                    pass                        # ignoramos el tipo de evento
    except requests.Timeout:
        yield "[TIMEOUT] El backend tardó demasiado en responder."
    except requests.RequestException as exc:
        yield f"[ERROR] Conexión perdida: {exc}"

