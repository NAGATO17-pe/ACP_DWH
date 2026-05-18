"""
fact_fisiologia.py
==================
Carga Silver.Fact_Fisiologia desde Bronce.Fisiologia.

Grain: Geo + Tiempo + Variedad + Tercio
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
)


TABLA_ORIGEN  = 'Bronce.Fisiologia'
TABLA_DESTINO = 'Silver.Fact_Fisiologia'

MAPA_TERCIO = {
    'BAJO': 'BAJO', 'B': 'BAJO', 'LOW': 'BAJO',
    'MEDIO': 'MEDIO', 'M': 'MEDIO', 'MID': 'MEDIO',
    'ALTO': 'ALTO', 'A': 'ALTO', 'HIGH': 'ALTO',
}


def _normalizar_tercio(valor) -> str | None:
    tercio_raw = str(valor or '').strip().upper()
    return MAPA_TERCIO.get(tercio_raw, tercio_raw or None)


class ProcesadorFisiologia(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Fisiologia')
        # Grain: Geo + Tiempo + Variedad + Tercio
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Tercio']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Fisiologia'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'fisiologia')
            if fecha is None:
                continue

            v_raw = self.parsear_raw(fila.get('Valores_Raw'))
            
            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                self.get_raw_val(fila, 'Fundo_Raw', v_raw),
                self.get_raw_val(fila, 'Modulo_Raw', v_raw),
                turno=self.get_raw_val(fila, 'Turno_Raw', v_raw),
                valvula=self.get_raw_val(fila, 'Valvula_Raw', v_raw),
            )
            if resultado_geo is None:
                continue

            id_var = self._validar_y_resolver_variedad(id_origen, fila.get('Variedad_Canonica'), fila.get('Variedad_Raw'))
            if id_var is None:
                continue

            brotes_prod = self.a_int(self.get_raw_val(fila, 'BrotesProd_Raw', v_raw))
            if brotes_prod is None:
                brotes_prod = self.a_int(self.get_raw_val(fila, 'Brote_Raw', v_raw))

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':     resultado_geo['id_geografia'],
                '_id_modulo_catalogo': resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':        obtener_id_tiempo(fecha),
                'ID_Variedad':      id_var,
                'Tercio':           _normalizar_tercio(self.get_raw_val(fila, 'Tercio_Raw', v_raw)),
                'Brotes_Productivos': brotes_prod,
                'Brotes_Vegetativos': self.a_int(self.get_raw_val(fila, 'BrotesVeg_Raw', v_raw)),
                'Hinchadas':        self.a_int(self.get_raw_val(fila, 'Hinchadas_Raw',  v_raw)),
                'Productivas':      self.a_int(self.get_raw_val(fila, 'Productivas_Raw', v_raw)),
                'Total_Organos':    self.a_int(self.get_raw_val(fila, 'Total_Org_Raw',  v_raw)),
                'Fecha_Evento':     fecha,
                'Estado_DQ':        'OK',
                'id_origen_rastreo': id_origen,
            })
        return payload


def cargar_fact_fisiologia(engine: Engine) -> dict:
    proc = ProcesadorFisiologia(engine)

    # Definición de columnas RAW necesarias
    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Sector_Raw', 'Modulo_Raw', 'Turno_Raw', 
        'Valvula_Raw', 'Variedad_Raw', 'Tercio_Raw', 'Hinchadas_Raw', 
        'Productivas_Raw', 'Total_Org_Raw', 'Brote_Raw', 'BrotesProd_Raw', 
        'BrotesVeg_Raw', 'Valores_Raw'
    ]
    
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion
        )
        # Deduplicación temprana
        df = proc.pre_limpiar_duplicados_batch(df, ['Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 'Tercio_Raw'])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Fisiologia')

        return proc.finalizar_proceso(contexto)
