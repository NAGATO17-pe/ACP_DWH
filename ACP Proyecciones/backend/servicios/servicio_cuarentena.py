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


def listar_cuarentena(
    pagina: int = 1,
    tamano: int = 20,
    tabla_filtro: str | None = None,
) -> dict:
    return repo.listar_pendientes(
        pagina=pagina,
        tamano=tamano,
        tabla_filtro=tabla_filtro,
    )


def obtener_resumen_cuarentena() -> dict:
    conteos = repo.contar_por_estado()
    return {
        "total":      sum(conteos.values()),
        "pendientes": conteos.get("PENDIENTE",  0),
        "resueltos":  conteos.get("RESUELTO",   0),
        "descartados": conteos.get("DESCARTADO", 0),
    }


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
