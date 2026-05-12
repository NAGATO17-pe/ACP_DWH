"""
fact_sanidad_activo.py
======================
Carga Silver.Fact_Sanidad_Activo desde Bronce.Seguimiento_Errores.

Validación crítica: Total_Plantas >= 1 (evita división por cero en Pct_Mortalidad PERSISTED)
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_total_plantas
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact
from mdm.homologador import homologar_columna


TABLA_ORIGEN  = 'Bronce.Seguimiento_Errores'
TABLA_DESTINO = 'Silver.Fact_Sanidad_Activo'


def _leer_bronce(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Seguimiento_Errores,
                Fecha_Raw, Fundo_Raw, Modulo_Raw, Variedad_Raw,
                Plantas_Vivas_Raw, Plantas_Muertas_Raw, Total_Plantas_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_int(valor) -> int | None:
    try:
        return int(float(str(valor)))
    except (ValueError, TypeError):
        return None


class ProcesadorSanidadActivo(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Seguimiento_Errores')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Seguimiento_Errores'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'sanidad_activo')
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                fila.get('Fundo_Raw'),
                fila.get('Modulo_Raw'),
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

            total, error_total = validar_total_plantas(fila.get('Total_Plantas_Raw'))
            if error_total:
                self.registrar_rechazo(
                    id_origen,
                    columna=error_total.get('columna', 'Total_Plantas_Raw'),
                    valor=error_total.get('valor'),
                    motivo=error_total.get('motivo', 'Total_Plantas invalido'),
                    severidad=error_total.get('severidad', 'ALTO'),
                )
                continue

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':  resultado_geo['id_geografia'],
                'ID_Tiempo':     obtener_id_tiempo(fecha),
                'ID_Variedad':   id_var,
                'Plantas_Vivas':   _a_int(fila.get('Plantas_Vivas_Raw')),
                'Plantas_Muertas': _a_int(fila.get('Plantas_Muertas_Raw')),
                'Total_Plantas':   total,
                'Fecha_Evento':    fecha,
                'id_origen_rastreo': id_origen,
            })
        return payload


def cargar_fact_sanidad_activo(engine: Engine) -> dict:
    proc = ProcesadorSanidadActivo(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Variedad_Raw',
        'Plantas_Vivas_Raw', 'Plantas_Muertas_Raw', 'Total_Plantas_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Seguimiento_Errores'
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_SanidadActivo')

        return proc.finalizar_proceso(contexto)
