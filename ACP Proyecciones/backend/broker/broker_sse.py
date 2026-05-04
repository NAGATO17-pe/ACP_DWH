"""
broker/broker_sse.py
====================
Broker de Server-Sent Events.
Mantiene una cola asyncio.Queue por corrida activa y registra
el event loop propietario para publicar desde threads de forma segura.
"""

import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator


@dataclass(slots=True)
class EstadoCorridaSSE:
    cola: asyncio.Queue
    loop: asyncio.AbstractEventLoop


_colas: dict[str, EstadoCorridaSSE] = {}


def registrar_corrida(id_corrida: str) -> asyncio.Queue:
    """
    Crea y registra una nueva cola para la corrida dada.
    """
    cola: asyncio.Queue = asyncio.Queue()
    _colas[id_corrida] = EstadoCorridaSSE(
        cola=cola,
        loop=asyncio.get_running_loop(),
    )
    return cola


def publicar_linea(id_corrida: str, linea: str) -> None:
    """
    Publica una linea en la cola de la corrida de manera thread-safe.
    """
    estado = _colas.get(id_corrida)
    if estado is not None:
        estado.loop.call_soon_threadsafe(estado.cola.put_nowait, linea)


def finalizar_corrida(id_corrida: str) -> None:
    """
    Envia el sentinel de cierre de manera thread-safe.
    """
    estado = _colas.get(id_corrida)
    if estado is not None:
        estado.loop.call_soon_threadsafe(estado.cola.put_nowait, None)


def liberar_corrida(id_corrida: str) -> None:
    _colas.pop(id_corrida, None)


def corrida_existe(id_corrida: str) -> bool:
    return id_corrida in _colas


async def generar_eventos(id_corrida: str) -> AsyncGenerator[dict, None]:
    """
    Generador asincrono para EventSourceResponse.
    Lee de la cola linea a linea hasta recibir el sentinel None.
    """
    estado = _colas.get(id_corrida)
    if estado is None:
        yield {"data": f"ERROR: corrida '{id_corrida}' no encontrada."}
        return

    try:
        while True:
            linea = await estado.cola.get()
            if linea is None:
                yield {"data": "[FIN_CORRIDA]"}
                break
            yield {"data": linea.rstrip("\n")}
    finally:
        liberar_corrida(id_corrida)