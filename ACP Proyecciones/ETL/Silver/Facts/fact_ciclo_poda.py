"""
fact_ciclo_poda.py
==================
Carga Silver.Fact_Ciclo_Poda desde:
  - Bronce.Evaluacion_Calidad_Poda
  - Bronce.Ciclos_Fenologicos

Grain: Fecha + Geo + Variedad
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.texto import titulo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact
from utils.tipos import a_decimal as _a_decimal


TABLA_PODA    = 'Bronce.Evaluacion_Calidad_Poda'
TABLA_CICLOS  = 'Bronce.Ciclos_Fenologicos'
TABLA_DESTINO = 'Silver.Fact_Ciclo_Poda'


def _leer_bronce_poda(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Evaluacion_Poda,
                ID_Evaluacion_Calidad_Poda,
                Fecha_Raw, Fundo_Raw, Modulo_Raw, Turno_Raw, Valvula_Raw, Variedad_Raw,
                Tipo_Evaluacion_Raw,
                TallosPlanta_Raw, LongitudTallo_Raw, DiametroTallo_Raw,
                RamillaPlanta_Raw, ToconesPlanta_Raw,
                CortesDefectuosos_Raw, AlturaPoda_Raw,
                Fecha_Sistema
            FROM {TABLA_PODA}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


class ProcesadorCicloPoda(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_PODA, TABLA_DESTINO, columna_id='ID_Evaluacion_Poda')
        # Grain: Geo + Tiempo + Variedad + Tipo_Evaluacion
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Tipo_Evaluacion']
        self.columna_tiebreaker_timestamp = 'Fecha_Sistema'

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Evaluacion_Poda'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'ciclo_poda')
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                fila.get('Fundo_Raw'),
                fila.get('Modulo_Raw'),
                turno=fila.get('Turno_Raw'),
                valvula=fila.get('Valvula_Raw'),
            )
            if resultado_geo is None:
                continue

            id_var = self._validar_y_resolver_variedad(
                id_origen,
                fila.get('Variedad_Canonica'),
                fila.get('Variedad_Raw'),
            )
            if id_var is None:
                continue

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':              resultado_geo['id_geografia'],
                'ID_Tiempo':                 obtener_id_tiempo(fecha),
                'ID_Variedad':               id_var,
                'Tipo_Evaluacion':           titulo(fila.get('Tipo_Evaluacion_Raw')) or 'SIN_TIPO',
                'Promedio_Tallos_Planta':    _a_decimal(fila.get('TallosPlanta_Raw')),
                'Promedio_Longitud_Tallo':   _a_decimal(fila.get('LongitudTallo_Raw')),
                'Promedio_Diametro_Tallo':   _a_decimal(fila.get('DiametroTallo_Raw')),
                'Promedio_Ramilla_Planta':   _a_decimal(fila.get('RamillaPlanta_Raw')),
                'Promedio_Tocones_Planta':   _a_decimal(fila.get('ToconesPlanta_Raw')),
                'Promedio_Cortes_Defectuosos': _a_decimal(fila.get('CortesDefectuosos_Raw')),
                'Promedio_Altura_Poda':      _a_decimal(fila.get('AlturaPoda_Raw')),
                'Fecha_Evento':              fecha,
                'Fecha_Sistema':             fila.get('Fecha_Sistema'),
                'Estado_DQ':                 'OK',
                'id_origen_rastreo':         id_origen,
            })
        return payload


def cargar_fact_ciclo_poda(engine: Engine) -> dict:
    proc = ProcesadorCicloPoda(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Variedad_Raw', 'Tipo_Evaluacion_Raw', 'TallosPlanta_Raw',
        'LongitudTallo_Raw', 'DiametroTallo_Raw', 'RamillaPlanta_Raw',
        'ToconesPlanta_Raw', 'CortesDefectuosos_Raw', 'AlturaPoda_Raw',
        'Fecha_Sistema'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_PODA, conexion,
            columna_id_origen='ID_Evaluacion_Poda'
        )
        df = proc.pre_limpiar_duplicados_batch(df, ['Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 'Tipo_Evaluacion_Raw'])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_CicloPoda')

        return proc.finalizar_proceso(contexto)
