"""
fact_areas_plantas.py
=====================
Carga Silver.Fact_Areas_Plantas (censo de plantas) desde el Excel histórico.
NO pasa por Bronce — el Excel se lee directo y se inserta a Silver.

Grano de negocio: (ID_Geografia, ID_Variedad, ID_Tiempo).
Idempotente: WHERE NOT EXISTS sobre esa tripleta.
"""

import datetime as _dt
import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from bronce.cargador import normalizar_columnas
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from mdm.lookup import resolver_geografia, obtener_id_variedad, obtener_id_campana


TABLA_DESTINO = 'Silver.Fact_Areas_Plantas'


def _anio_desde_campana(valor) -> int | None:
    if valor is None:
        return None
    txt = str(valor).strip()
    if not txt or txt.lower() == 'nan':
        return None
    # "2021-2022" / "2021 - 2022" → 2021 ; "2016" → 2016
    m = re.search(r'(\d{4})', txt)
    return int(m.group(1)) if m else None


def _safe_float(v, default=0.0) -> float:
    if v is None:
        return default
    try:
        s = str(v).strip()
        if not s or s.lower() == 'nan':
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def cargar_fact_areas_plantas(engine: Engine, ruta_excel: str) -> dict:
    """Lee fact_Censo_Plantas.xlsx y carga Silver.Fact_Areas_Plantas."""
    resumen = {'leidos': 0, 'insertados': 0, 'rechazados': 0, 'cuarentena': []}

    df_raw = pd.read_excel(ruta_excel)
    if df_raw.empty:
        return resumen

    df_raw = normalizar_columnas(df_raw)
    resumen['leidos'] = len(df_raw)

    # Dedup: una fila por (Modulo, Turno, Valvula, Variedad) con máxima Campana
    cols_dedup = [c for c in ['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw']
                  if c in df_raw.columns]
    if 'Campana_Raw' in df_raw.columns:
        df = df_raw.sort_values(cols_dedup + ['Campana_Raw'], ascending=False).drop_duplicates(
            subset=cols_dedup, keep='first')
    else:
        df = df_raw.drop_duplicates(subset=cols_dedup, keep='first')

    df = df.reset_index(drop=True)
    df['ID_Registro_Origen'] = range(1, len(df) + 1)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', 'Bronce.Censo', conexion,
            columna_id_origen='ID_Registro_Origen',
        )
        resumen['cuarentena'].extend(cuar_var)

        cache_geo: dict[tuple, dict | None] = {}
        cache_var: dict[str, int | None] = {}

        insertados = 0
        for _, fila in df.iterrows():
            modulo  = fila.get('Modulo_Raw')
            turno   = fila.get('Turno_Raw')
            valvula = fila.get('Valvula_Raw')
            var_can = fila.get('Variedad_Canonica')

            anio = _anio_desde_campana(fila.get('Campana_Raw')) or _dt.date.today().year
            fecha_evento = _dt.date(anio, 7, 1)
            id_tiempo = obtener_id_tiempo(fecha_evento)
            if id_tiempo is None:
                resumen['rechazados'] += 1
                continue

            clave_geo = (str(modulo), str(turno), str(valvula))
            if clave_geo not in cache_geo:
                cache_geo[clave_geo] = resolver_geografia(
                    None, None, modulo, engine, turno=turno, valvula=valvula
                )
            res_geo = cache_geo[clave_geo]
            if not res_geo or not res_geo.get('id_geografia'):
                resumen['rechazados'] += 1
                resumen['cuarentena'].append({
                    'columna': 'Modulo_Raw',
                    'valor': f'M={modulo}|T={turno}|V={valvula}',
                    'motivo': 'Geografia no encontrada para censo',
                    'tipo_regla': 'MDM',
                    'severidad': 'ALTO',
                    'id_registro_origen': int(fila['ID_Registro_Origen']),
                })
                continue

            clave_var = str(var_can)
            if clave_var not in cache_var:
                cache_var[clave_var] = obtener_id_variedad(var_can, engine)
            id_var = cache_var[clave_var]
            if not id_var:
                resumen['rechazados'] += 1
                resumen['cuarentena'].append({
                    'columna': 'Variedad_Raw',
                    'valor': fila.get('Variedad_Raw'),
                    'motivo': 'Variedad sin match en Dim_Variedad',
                    'tipo_regla': 'MDM',
                    'severidad': 'ALTO',
                    'id_registro_origen': int(fila['ID_Registro_Origen']),
                })
                continue

            id_geo = res_geo['id_geografia']
            id_campana = obtener_id_campana(
                id_geo, id_var, fecha_evento, engine,
                id_modulo_catalogo=res_geo.get('id_modulo_catalogo')
            )

            cantidad = _safe_float(fila.get('Plantas_Raw'))
            area     = _safe_float(fila.get('Area_Raw'))

            res = conexion.execute(text(f"""
                INSERT INTO {TABLA_DESTINO} (
                    ID_Geografia, ID_Variedad, ID_Tiempo, Cantidad_Plantas, Area_ha,
                    Fecha_Sistema, Estado_DQ, ID_Campana
                )
                SELECT :id_geo, :id_var, :id_tiempo, :cant, :area, SYSDATETIME(), 'OK', :id_camp
                WHERE NOT EXISTS (
                    SELECT 1 FROM {TABLA_DESTINO}
                    WHERE ID_Geografia = :id_geo
                      AND ID_Variedad  = :id_var
                      AND ID_Tiempo    = :id_tiempo
                )
            """), {
                'id_geo':    id_geo,
                'id_var':    id_var,
                'id_tiempo': id_tiempo,
                'cant':      cantidad,
                'area':      area,
                'id_camp':   id_campana,
            })
            insertados += int(res.rowcount or 0)

        resumen['insertados'] = insertados

    return {
        'Tabla_Destino': TABLA_DESTINO,
        'Filas_Leidas_Bronce': resumen['leidos'],
        'Filas_Insertadas': resumen['insertados'],
        'Nuevos_Casos_Cuarentena': resumen['rechazados'],
        'cuarentena': resumen['cuarentena'],
    }
