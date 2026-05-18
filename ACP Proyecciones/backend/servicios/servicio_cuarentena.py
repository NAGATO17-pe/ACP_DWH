"""
servicios/servicio_cuarentena.py
================================
Lógica para consultar y gestionar registros en MDM.Cuarentena.
Delega todo el acceso a datos a repositorios.repo_cuarentena.
La lógica de negocio aquí: validación de rowcount, invalidación de caché,
registro de decisiones MDM.
"""

from __future__ import annotations

from nucleo.cache import cache
from nucleo.excepciones import ErrorRecursoNoEncontrado
from nucleo.logging import obtener_logger
import repositorios.repo_auditoria as repo_auditoria
import repositorios.repo_cuarentena as repo

log = obtener_logger(__name__)


_TTL_CACHE_LISTAR_SEG = 60


def _clave_cache_listar(pagina: int, tamano: int, tabla_filtro: str | None) -> str:
    return f"cuarentena:listar:p{pagina}:t{tamano}:f{tabla_filtro or 'todos'}"


def listar_cuarentena(
    pagina: int = 1,
    tamano: int = 20,
    tabla_filtro: str | None = None,
) -> dict:
    """Read-through cache: TTL corto para reducir presion sobre MDM.Cuarentena."""
    clave = _clave_cache_listar(pagina, tamano, tabla_filtro)
    cacheado = cache.obtener(clave)
    if cacheado is not None:
        return cacheado

    resultado = repo.listar_pendientes(
        pagina=pagina,
        tamano=tamano,
        tabla_filtro=tabla_filtro,
    )
    try:
        cache.guardar(clave, resultado, ttl_segundos=_TTL_CACHE_LISTAR_SEG)
    except (TypeError, ValueError):
        log.debug("Cache no serializable; salto guardado", extra={"clave": clave})
    return resultado


def _invalidar_cache_cuarentena() -> None:
    """Limpia toda la caché cuando hay cambios en cuarentena."""
    cache.limpiar_todo()


def resolver_registro(
    tabla_origen: str,
    id_registro: str,
    valor_canonico: str,
    analista: str,
    comentario: str | None,
) -> dict:
    """Marca un registro de MDM.Cuarentena como RESUELTO."""
    rowcount = repo.marcar_resuelto(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico=valor_canonico,
        analista=analista,
    )
    if rowcount == 0:
        raise ErrorRecursoNoEncontrado(f"Registro #{id_registro} en {tabla_origen}")

    _invalidar_cache_cuarentena()
    repo_auditoria.insertar_decision_mdm(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico=valor_canonico,
        decision="RESUELTO",
        analista=analista,
        comentario=comentario or "",
    )
    log.info(
        "Registro de cuarentena resuelto",
        extra={"id_registro": id_registro, "tabla_origen": tabla_origen},
    )
    return {
        "id_registro":  id_registro,
        "estado_nuevo": "RESUELTO",
        "mensaje":      f"Registro resuelto con valor corregido '{valor_canonico}'.",
    }


def rechazar_registro(
    tabla_origen: str,
    id_registro: str,
    motivo: str,
    analista: str,
) -> dict:
    """Marca un registro de MDM.Cuarentena como DESCARTADO."""
    rowcount = repo.marcar_descartado(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        analista=analista,
    )
    if rowcount == 0:
        raise ErrorRecursoNoEncontrado(f"Registro #{id_registro} en {tabla_origen}")

    _invalidar_cache_cuarentena()
    repo_auditoria.insertar_decision_mdm(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico="",
        decision="DESCARTADO",
        analista=analista,
        comentario=motivo,
    )
    log.info(
        "Registro de cuarentena descartado",
        extra={"id_registro": id_registro, "tabla_origen": tabla_origen},
    )
    return {
        "id_registro":  id_registro,
        "estado_nuevo": "DESCARTADO",
        "mensaje":      f"Registro descartado. Motivo: {motivo}",
    }
