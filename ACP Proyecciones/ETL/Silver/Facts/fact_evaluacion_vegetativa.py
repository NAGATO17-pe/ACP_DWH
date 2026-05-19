"""
fact_evaluacion_vegetativa.py
=============================
Carga Silver.Fact_Evaluacion_Vegetativa desde Bronce.Evaluacion_Vegetativa.

Grano real (verificado en BD): (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Campana, Piso, ID_Origen_Bronce).
Cada fila Bronce se EXPANDE a 5 filas Silver (una por Piso 1..5).
Pisos sin datos quedan con medidas en 0 (no NULL).
"""

import pandas as pd
from sqlalchemy.engine import Engine

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.tipos import a_entero, a_decimal
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Evaluacion_Vegetativa'
TABLA_DESTINO = 'Silver.Fact_Evaluacion_Vegetativa'

PISOS = range(1, 6)


def _a_decimal_cero(v) -> float:
    d = a_decimal(v)
    return float(d) if d is not None else 0.0


def _a_entero_cero(v) -> int:
    d = a_entero(v)
    return int(d) if d is not None else 0


class ProcesadorEvaluacionVegetativa(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Evaluacion_Veg')
        self.columnas_clave_unica = [
            'ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Campana', 'Piso', 'ID_Origen_Bronce'
        ]

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload: list[dict] = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Evaluacion_Veg'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'evaluacion_vegetativa')
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                None,
                fila.get('Modulo_Raw'),
                turno=fila.get('Turno_Raw'),
                valvula=fila.get('Valvula_Raw'),
                cama=fila.get('Cama_Raw'),
            )
            if resultado_geo is None:
                continue

            id_var = self._validar_y_resolver_variedad(
                id_origen, fila.get('Variedad_Canonica'), fila.get('Variedad_Raw')
            )
            if id_var is None:
                continue

            id_tiempo = obtener_id_tiempo(fecha)
            if id_tiempo is None:
                self.registrar_rechazo(id_origen, 'Fecha_Raw', fila.get('Fecha_Raw'),
                                       'Fecha valida pero fuera de Dim_Tiempo')
                continue

            semanas = _a_entero_cero(fila.get('Semanas_Poda_Raw'))
            altura  = _a_decimal_cero(fila.get('Altura_Raw'))
            tb      = _a_decimal_cero(fila.get('Tallos_Basales_Raw'))
            tbn     = _a_decimal_cero(fila.get('Tallos_Basales_Nuevos_Raw'))
            muestra = _a_entero_cero(fila.get('Muestra_Plantas_Raw'))

            for piso in PISOS:
                payload.append({
                    'ID_Geografia':          resultado_geo['id_geografia'],
                    '_id_modulo_catalogo':   resultado_geo.get('id_modulo_catalogo'),
                    'ID_Tiempo':             id_tiempo,
                    'ID_Variedad':           id_var,
                    'Piso':                  piso,
                    'Semanas_Despues_Poda':  semanas,
                    'Altura':                altura,
                    'Tallos_Basales':        tb,
                    'Tallos_Basales_Nuevos': tbn,
                    'Muestra_Plantas':       muestra,
                    'Brotes_Generales':      _a_decimal_cero(fila.get(f'Piso{piso}_Brotes_Raw')),
                    'Brotes_Productivos':    _a_decimal_cero(fila.get(f'Piso{piso}_Productivos_Raw')),
                    'Diametro_Brote':        _a_decimal_cero(fila.get(f'Piso{piso}_Diametro_Raw')),
                    'Fecha_Evento':          fecha,
                    'Estado_DQ':             'OK',
                    'ID_Origen_Bronce':      id_origen,
                    'id_origen_rastreo':     id_origen,
                })
            self.ids_procesados.append(id_origen)
        return payload


def cargar_fact_evaluacion_vegetativa(engine: Engine) -> dict:
    proc = ProcesadorEvaluacionVegetativa(engine)

    cols_raw = [
        'Fecha_Raw', 'Campana_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Cama_Raw',
        'Variedad_Raw', 'Evaluador_Raw', 'DNI_Raw', 'Semanas_Poda_Raw',
        'Altura_Raw', 'Tallos_Basales_Raw', 'Tallos_Basales_Nuevos_Raw', 'Muestra_Plantas_Raw',
        'Piso1_Brotes_Raw', 'Piso1_Productivos_Raw', 'Piso1_Diametro_Raw',
        'Piso2_Brotes_Raw', 'Piso2_Productivos_Raw', 'Piso2_Diametro_Raw',
        'Piso3_Brotes_Raw', 'Piso3_Productivos_Raw', 'Piso3_Diametro_Raw',
        'Piso4_Brotes_Raw', 'Piso4_Productivos_Raw', 'Piso4_Diametro_Raw',
        'Piso5_Brotes_Raw', 'Piso5_Productivos_Raw', 'Piso5_Diametro_Raw',
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Evaluacion_Veg',
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_EvaluacionVegetativa')

        return proc.finalizar_proceso(contexto)
