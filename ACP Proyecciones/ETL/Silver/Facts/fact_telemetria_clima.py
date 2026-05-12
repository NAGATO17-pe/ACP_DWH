"""
fact_telemetria_clima.py
========================
Carga Silver.Fact_Telemetria_Clima desde dos fuentes independientes:
  - Bronce.Reporte_Clima      (temp, humedad, precipitacion)
  - Bronce.Variables_Meteorologicas (temp, humedad, VPD, radiacion)

Grano: Sector_Climatico + ID_Tiempo.
Transformacion critica: Humedad proporcion (0-1) -> porcentaje (0-100).

ARQUITECTURA DE DEDUPLICACION (excepcion justificada al patron BaseFactProcessor):
  Este fact NO usa la subclase BaseFactProcessor como orquestador principal porque
  maneja dos fuentes Bronce con esquemas distintos que convergen en la misma tabla
  destino. En su lugar implementa _resolver_duplicados_clima(), que aplica una
  politica de firma de metricas:
    - Duplicados con metricas identicas: se descarta silenciosamente el segundo.
    - Duplicados con metricas en conflicto: se rechazan TODOS a cuarentena.
  El BaseFactProcessor se instancia de forma auxiliar (una vez por fuente) para
  reutilizar _ejecutar_insercion_masiva_segura() y la deduplicacion SQL final
  (WHERE NOT EXISTS). El resumen de insertados/rechazados se gestiona manualmente
  porque cada fuente tiene su propio ciclo de estados de carga en Bronce.
"""

import re
import math

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from dq.validador import normalizar_humedad
from mdm.lookup import obtener_id_tiempo as obtener_id_tiempo_dim
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo as construir_id_tiempo, procesar_fecha
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_CLIMA = 'Bronce.Reporte_Clima'
TABLA_VARIABLES = 'Bronce.Variables_Meteorologicas'
TABLA_CUARENTENA = 'Bronce.Clima'
TABLA_DESTINO = 'Silver.Fact_Telemetria_Clima'
TAM_LOTE_CLIMA = 2000
PATRON_HORA_VALORES_RAW = re.compile(r'(?:^|\s\|\s)Hora_Raw=([^|]+)')


def _leer_bronce_clima(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Reporte_Clima,
                Fecha_Raw, Hora_Raw, Sector_Raw,
                TempMax_Raw, TempMin_Raw,
                Humedad_Raw, Precipitacion_Raw
            FROM {TABLA_CLIMA}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _leer_bronce_variables(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Variables_Met AS ID_Variables_Meteorologicas,
                Fecha_Raw, Sector_Raw,
                VPD_Raw, Radiacion_Raw,
                TempMax_Raw, TempMin_Raw, Humedad_Raw,
                Valores_Raw
            FROM {TABLA_VARIABLES}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_decimal(valor, decimales: int | None = None) -> float | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip()
        if not texto or texto.upper() in {'NONE', 'NULL', 'NAN'}:
            return None
        numero = float(texto.replace(',', '.'))
        if not math.isfinite(numero):
            return None
        if decimales is not None:
            numero = round(numero, decimales)
        return numero
    except (ValueError, TypeError):
        return None


def _a_entero_nulo(valor) -> int | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip()
        if texto in ('', 'None', 'nan'):
            return None
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def _normalizar_sector_climatico(valor) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto or texto.upper() in {'NONE', 'NULL', 'NAN'}:
        return None

    return texto.upper()


def _normalizar_hora_texto(valor) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto or texto.upper() in {'NONE', 'NULL', 'NAN'}:
        return None

    coincidencia = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', texto)
    if not coincidencia:
        return None

    hora = coincidencia.group(1)
    if len(hora) == 5:
        return f'{hora}:00'
    return hora


def _extraer_hora_desde_valores_raw(valores_raw) -> str | None:
    if valores_raw is None:
        return None

    coincidencia = PATRON_HORA_VALORES_RAW.search(str(valores_raw))
    if not coincidencia:
        return None

    return _normalizar_hora_texto(coincidencia.group(1))


def _construir_fecha_hora_clima(fecha_raw, hora_raw=None, valores_raw=None) -> str:
    fecha_base = str(fecha_raw).strip() if fecha_raw is not None else ''
    hora = _normalizar_hora_texto(hora_raw)
    if hora is None:
        hora = _extraer_hora_desde_valores_raw(valores_raw)

    if not fecha_base:
        return ''
    if hora is None:
        return fecha_base
    return f'{fecha_base} {hora}'


def _agregar_cuarentena(
    cuarentena: list[dict],
    columna: str,
    valor,
    motivo: str,
    id_registro_origen,
) -> None:
    cuarentena.append({
        'columna': columna,
        'valor': valor,
        'motivo': motivo,
        'id_registro_origen': id_registro_origen,
    })


# NOTA ARQUITECTURA: Variables_Meteorologicas usa MERGE en lugar de INSERT puro.
# Esto garantiza que si Reporte_Clima ya insertó el registro (mismo Sector+Fecha),
# los campos VPD y Radiacion_Solar se actualicen en lugar de ignorarse silenciosamente.
# MERGE: si existe -> UPDATE VPD/Radiacion; si no existe -> INSERT completo.
SQL_MERGE_CLIMA_VARIABLES = """
    MERGE Silver.Fact_Telemetria_Clima AS tgt
    USING (
        SELECT
            :sector_climatico AS Sector_Climatico,
            :id_tiempo        AS ID_Tiempo,
            :id_campana       AS ID_Campana,
            :temp_max         AS Temperatura_Max_C,
            :temp_min         AS Temperatura_Min_C,
            :humedad          AS Humedad_Relativa_Pct,
            :vpd              AS VPD,
            :radiacion        AS Radiacion_Solar,
            :fecha_evento     AS Fecha_Evento
    ) AS src
    ON tgt.Sector_Climatico = src.Sector_Climatico
   AND tgt.ID_Tiempo        = src.ID_Tiempo
    WHEN MATCHED THEN
        UPDATE SET
            ID_Campana            = ISNULL(tgt.ID_Campana, src.ID_Campana),
            VPD                   = COALESCE(src.VPD,           tgt.VPD),
            Radiacion_Solar       = COALESCE(src.Radiacion_Solar, tgt.Radiacion_Solar),
            Temperatura_Max_C     = COALESCE(src.Temperatura_Max_C, tgt.Temperatura_Max_C),
            Temperatura_Min_C     = COALESCE(src.Temperatura_Min_C, tgt.Temperatura_Min_C),
            Humedad_Relativa_Pct  = COALESCE(src.Humedad_Relativa_Pct, tgt.Humedad_Relativa_Pct)
    WHEN NOT MATCHED THEN
        INSERT (
            Sector_Climatico, ID_Tiempo, ID_Campana,
            Temperatura_Max_C, Temperatura_Min_C,
            Humedad_Relativa_Pct, Precipitacion_mm,
            VPD, Radiacion_Solar,
            Fecha_Evento, Fecha_Sistema
        ) VALUES (
            src.Sector_Climatico, src.ID_Tiempo, src.ID_Campana,
            src.Temperatura_Max_C, src.Temperatura_Min_C,
            src.Humedad_Relativa_Pct, NULL,
            src.VPD, src.Radiacion_Solar,
            src.Fecha_Evento, SYSDATETIME()
        );
"""


def _clave_logica_clima(registro: dict) -> tuple:
    return (
        registro['sector_climatico'],
        registro['fecha_evento'],
    )


def _firma_metricas_clima(registro: dict, campos_metricas: tuple[str, ...]) -> tuple:
    return tuple(registro.get(campo) for campo in campos_metricas)


def _resolver_duplicados_clima(
    registros: list[dict],
    *,
    campos_metricas: tuple[str, ...],
    resumen: dict,
    ids_rechazados: list[int],
    descripcion_origen: str,
) -> tuple[list[dict], list[int]]:
    grupos: dict[tuple, list[dict]] = {}
    for registro in registros:
        grupos.setdefault(_clave_logica_clima(registro), []).append(registro)

    registros_validos = []
    ids_insertados = []

    for clave, grupo in grupos.items():
        if len(grupo) == 1:
            registros_validos.append(grupo[0])
            if grupo[0]['id_origen'] is not None:
                ids_insertados.append(grupo[0]['id_origen'])
            continue

        # Intento de Fusión Inteligente
        # 1. Extraer valores no nulos por cada métrica
        consolidado = {campo: [r[campo] for r in grupo if r.get(campo) is not None] for campo in campos_metricas}
        
        # 2. Verificar conflictos reales (más de un valor distinto para la misma métrica)
        hay_conflicto = False
        for campo, valores in consolidado.items():
            if len(set(valores)) > 1:
                hay_conflicto = True
                break
        
        if not hay_conflicto:
            # Fusión segura: tomamos el primer valor encontrado (o None) para cada campo
            registro_fusionado = grupo[0].copy()
            for campo in campos_metricas:
                registro_fusionado[campo] = consolidado[campo][0] if consolidado[campo] else None
            
            registros_validos.append(registro_fusionado)
            # Marcamos todos los IDs del grupo como insertados (fisiológicamente representados por el fusionado)
            for r in grupo:
                if r['id_origen'] is not None:
                    ids_insertados.append(r['id_origen'])
            continue

        # Si hay conflicto real, se rechazan todos a cuarentena
        sector_climatico, fecha_evento = clave
        motivo = (
            f'Conflicto de métricas en {descripcion_origen}: '
            f'valores distintos para el mismo Sector/Fecha. '
            f'Detalle: { {k: list(set(v)) for k, v in consolidado.items() if len(set(v)) > 1} }'
        )
        for registro in grupo:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Fecha_Evento',
                str(fecha_evento),
                motivo,
                registro.get('id_origen'),
            )
            resumen['rechazados'] += 1
            if registro.get('id_origen') is not None:
                ids_rechazados.append(registro['id_origen'])

    return registros_validos, ids_insertados


def cargar_fact_telemetria_clima(engine: Engine) -> dict:
    resumen = {'insertados': 0, 'rechazados': 0, 'cuarentena': []}

    df_clima = _leer_bronce_clima(engine)
    df_vars = _leer_bronce_variables(engine)
    resumen['leidos'] = len(df_clima) + len(df_vars)
    ids_clima_rechazados = []
    registros_clima_validos = []
    total_clima = len(df_clima)

    for indice, fila in enumerate(df_clima.to_dict('records'), start=1):
        id_origen = _a_entero_nulo(fila.get('ID_Reporte_Clima'))
        fecha_str = f"{fila.get('Fecha_Raw')} {fila.get('Hora_Raw', '00:00')}"
        fecha, valida = procesar_fecha(fecha_str, dominio='clima')
        if not valida:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Fecha_Raw',
                fecha_str,
                'Fecha invalida en clima',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_clima_rechazados.append(id_origen)
            continue

        id_tiempo = obtener_id_tiempo_dim(construir_id_tiempo(fecha), engine)
        if not id_tiempo:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Fecha_Raw',
                fecha_str,
                'Fecha valida pero fuera de Dim_Tiempo',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_clima_rechazados.append(id_origen)
            continue

        sector_climatico = _normalizar_sector_climatico(fila.get('Sector_Raw'))
        if not sector_climatico:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Sector_Raw',
                fila.get('Sector_Raw'),
                'Sector climatico invalido o ausente',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_clima_rechazados.append(id_origen)
            continue

        humedad, error_hum = normalizar_humedad(fila.get('Humedad_Raw'))
        if error_hum:
            error_hum.update({
                'columna': 'Humedad_Raw',
                'valor': fila.get('Humedad_Raw'),
                'id_registro_origen': id_origen,
            })
            resumen['cuarentena'].append(error_hum)

        registros_clima_validos.append({
            'id_origen': id_origen,
            'sector_climatico': sector_climatico,
            'id_tiempo': id_tiempo,
            'temp_max': _a_decimal(fila.get('TempMax_Raw'), decimales=2),
            'temp_min': _a_decimal(fila.get('TempMin_Raw'), decimales=2),
            'humedad': humedad,
            'precipitacion': _a_decimal(fila.get('Precipitacion_Raw'), decimales=3),
            'fecha_evento': fecha,
        })
    payload_clima, ids_clima_insertados = _resolver_duplicados_clima(
        registros_clima_validos,
        campos_metricas=('temp_max', 'temp_min', 'humedad', 'precipitacion'),
        resumen=resumen,
        ids_rechazados=ids_clima_rechazados,
        descripcion_origen='Bronce.Reporte_Clima',
    )

    ids_vars_rechazados = []
    registros_vars_validos = []
    total_vars = len(df_vars)

    for indice, fila in enumerate(df_vars.to_dict('records'), start=1):
        id_origen = _a_entero_nulo(fila.get('ID_Variables_Meteorologicas'))
        fecha_str = _construir_fecha_hora_clima(
            fila.get('Fecha_Raw'),
            valores_raw=fila.get('Valores_Raw'),
        )
        fecha, valida = procesar_fecha(fecha_str, dominio='clima')
        if not valida:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Fecha_Raw',
                fecha_str or fila.get('Fecha_Raw'),
                'Fecha invalida en clima',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_vars_rechazados.append(id_origen)
            continue

        id_tiempo = obtener_id_tiempo_dim(construir_id_tiempo(fecha), engine)
        if not id_tiempo:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Fecha_Raw',
                fecha_str or fila.get('Fecha_Raw'),
                'Fecha valida pero fuera de Dim_Tiempo',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_vars_rechazados.append(id_origen)
            continue

        sector_climatico = _normalizar_sector_climatico(fila.get('Sector_Raw'))
        if not sector_climatico:
            _agregar_cuarentena(
                resumen['cuarentena'],
                'Sector_Raw',
                fila.get('Sector_Raw'),
                'Sector climatico invalido o ausente',
                id_origen,
            )
            resumen['rechazados'] += 1
            if id_origen is not None:
                ids_vars_rechazados.append(id_origen)
            continue

        humedad, error_hum = normalizar_humedad(fila.get('Humedad_Raw'))
        if error_hum:
            error_hum.update({
                'columna': 'Humedad_Raw',
                'valor': fila.get('Humedad_Raw'),
                'id_registro_origen': id_origen,
            })
            resumen['cuarentena'].append(error_hum)

        registros_vars_validos.append({
            'id_origen': id_origen,
            'sector_climatico': sector_climatico,
            'id_tiempo': id_tiempo,
            'temp_max': _a_decimal(fila.get('TempMax_Raw'), decimales=2),
            'temp_min': _a_decimal(fila.get('TempMin_Raw'), decimales=2),
            'humedad': humedad,
            'vpd': _a_decimal(fila.get('VPD_Raw'), decimales=3),
            'radiacion': _a_decimal(fila.get('Radiacion_Raw'), decimales=3),
            'fecha_evento': fecha,
        })
    payload_vars, ids_vars_insertados = _resolver_duplicados_clima(
        registros_vars_validos,
        campos_metricas=('temp_max', 'temp_min', 'humedad', 'vpd', 'radiacion'),
        resumen=resumen,
        ids_rechazados=ids_vars_rechazados,
        descripcion_origen='Bronce.Variables_Meteorologicas',
    )

    with ContextoTransaccionalETL(engine) as contexto:

        if payload_clima:
            _proc_clima = BaseFactProcessor(engine, TABLA_CLIMA, TABLA_DESTINO)
            _proc_clima.columnas_clave_unica = ['Sector_Climatico', 'ID_Tiempo']
            _proc_clima._ejecutar_insercion_masiva_segura(
                contexto,
                [
                    {
                        'Sector_Climatico': r['sector_climatico'],
                        'ID_Tiempo':        r['id_tiempo'],
                        'Temperatura_Max_C': r['temp_max'],
                        'Temperatura_Min_C': r['temp_min'],
                        'Humedad_Relativa_Pct': r['humedad'],
                        'Precipitacion_mm': r['precipitacion'],
                        'VPD':              None,
                        'Radiacion_Solar':  None,
                        'Fecha_Evento':     r['fecha_evento'],
                        'id_origen_rastreo': r['id_origen'],
                    }
                    for r in payload_clima
                ],
                '#Temp_TelemetriaClima_Reporte',
            )
            resumen['insertados'] += _proc_clima.resumen['insertados']

        if ids_clima_insertados:
            contexto.marcar_estado_carga(
                TABLA_CLIMA, 'ID_Reporte_Clima', ids_clima_insertados, estado='PROCESADO'
            )
        if ids_clima_rechazados:
            contexto.marcar_estado_carga(
                TABLA_CLIMA, 'ID_Reporte_Clima', ids_clima_rechazados, estado='RECHAZADO'
            )

        # Fase 35 Fix: Usar MERGE para que Variables_Meteorologicas actualice
        # VPD y Radiacion_Solar aunque Reporte_Clima ya haya insertado el registro.
        from mdm.lookup import obtener_id_campana
        conn_activa = contexto._conexion_activa()
        merged = 0
        for r in payload_vars:
            # Resolver campana para clima (sin geo ni variedad)
            id_campana = obtener_id_campana(None, None, r['fecha_evento'], engine)

            conn_activa.execute(
                text(SQL_MERGE_CLIMA_VARIABLES),
                {
                    'sector_climatico': r['sector_climatico'],
                    'id_tiempo':        r['id_tiempo'],
                    'id_campana':       id_campana,
                    'temp_max':         r['temp_max'],
                    'temp_min':         r['temp_min'],
                    'humedad':          r['humedad'],
                    'vpd':              r['vpd'],
                    'radiacion':        r['radiacion'],
                    'fecha_evento':     r['fecha_evento'],
                }
            )
            if r['id_origen'] is not None:
                ids_vars_insertados.append(r['id_origen'])
            merged += 1
        resumen['insertados'] += merged

        if ids_vars_insertados:
            contexto.marcar_estado_carga(
                TABLA_VARIABLES, 'ID_Variables_Met', ids_vars_insertados, estado='PROCESADO'
            )
        if ids_vars_rechazados:
            contexto.marcar_estado_carga(
                TABLA_VARIABLES, 'ID_Variables_Met', ids_vars_rechazados, estado='RECHAZADO'
            )

        if resumen['cuarentena']:
            contexto.enviar_cuarentena(TABLA_CUARENTENA, resumen['cuarentena'])

    return _finalizar_resumen_fact(resumen)
