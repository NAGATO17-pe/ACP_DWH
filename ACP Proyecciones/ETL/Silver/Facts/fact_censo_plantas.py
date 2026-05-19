"""
fact_censo_plantas.py
=====================
Carga Silver.Fact_Censo_Plantas desde Bronce.Seguimiento_Errores.

Nota historica: este modulo era antes ``fact_sanidad_activo.py`` y poblaba
Silver.Fact_Sanidad_Activo con las metricas Plantas_Vivas / Plantas_Muertas /
Total_Plantas. En la fase35 la tabla pasa a llamarse Silver.Fact_Censo_Plantas
y la semantica cambia a Plantas_Buenas / Plantas_Regulares / Plantas_Malas.

PENDIENTE de decision de negocio: como mapean las columnas Raw del Bronce
(Plantas_Vivas_Raw, Plantas_Muertas_Raw, Total_Plantas_Raw) a las nuevas
metricas (Buenas/Regulares/Malas). Hasta definirlo, el loader lanza
NotImplementedError para evitar inserts incorrectos.
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
TABLA_DESTINO = 'Silver.Fact_Censo_Plantas'


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


class ProcesadorCensoPlantas(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Seguimiento_Errores')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # TODO(fase35): definir mapeo Raw -> (Plantas_Buenas, Plantas_Regulares, Plantas_Malas).
        # Las columnas Plantas_Vivas / Plantas_Muertas / Total_Plantas fueron eliminadas de
        # Silver.Fact_Censo_Plantas. Hasta que se defina el mapeo, este loader no puede ejecutar.
        raise NotImplementedError(
            'cargar_fact_censo_plantas: mapeo Raw -> Buenas/Regulares/Malas pendiente de definir'
        )


def cargar_fact_censo_plantas(engine: Engine) -> dict:
    proc = ProcesadorCensoPlantas(engine)

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
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_CensoPlantas')

        return proc.finalizar_proceso(contexto)
