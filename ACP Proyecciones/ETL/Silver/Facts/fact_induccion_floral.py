"""
fact_induccion_floral.py
========================
Carga Silver.Fact_Induccion_Floral desde Bronce.Induccion_Floral.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    a_entero_no_negativo as _a_entero_no_negativo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    texto_nulo as _texto_nulo,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN = 'Bronce.Induccion_Floral'
TABLA_DESTINO = 'Silver.Fact_Induccion_Floral'

# Conservado para referencia del schema — ya no se usa directamente (bulk insert via #Temp)
SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Induccion_Floral (
        ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal,
        Tipo_Evaluacion, Codigo_Consumidor,
        Cantidad_Plantas_Por_Cama, Cantidad_Plantas_Con_Induccion,
        Cantidad_Brotes_Con_Induccion, Cantidad_Brotes_Totales,
        Cantidad_Brotes_Con_Flor,
        Pct_Plantas_Con_Induccion, Pct_Brotes_Con_Induccion, Pct_Brotes_Con_Flor,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad, :id_personal,
        :tipo_evaluacion, :codigo_consumidor,
        :plantas_por_cama, :plantas_con_induccion,
        :brotes_con_induccion, :brotes_totales,
        :brotes_con_flor,
        :pct_plantas_induccion, :pct_brotes_induccion, :pct_brotes_flor,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _pct(parte: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round((parte / total) * 100.0, 2)


def _validar_layout_migrado(engine: Engine) -> str:
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Induccion_Floral',
        columnas_bronce_requeridas={
            'ID_Induccion_Floral',
            'Fecha_Raw',
            'DNI_Raw',
            'Consumidor_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'PlantasPorCama_Raw',
            'PlantasConInduccion_Raw',
            'BrotesConInduccion_Raw',
            'BrotesTotales_Raw',
            'BrotesConFlor_Raw',
            'Estado_Carga',
        },
        columnas_silver_requeridas={
            'ID_Geografia',
            'ID_Tiempo',
            'ID_Variedad',
            'ID_Personal',
            'Codigo_Consumidor',
            'Cantidad_Plantas_Por_Cama',
            'Cantidad_Plantas_Con_Induccion',
            'Cantidad_Brotes_Con_Induccion',
            'Cantidad_Brotes_Totales',
            'Cantidad_Brotes_Con_Flor',
        },
        nombre_layout='Induccion_Floral',
    )


def _leer_bronce(engine: Engine, columna_id: str) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                {columna_id} AS ID_Registro_Origen,
                Fecha_Raw,
                DNI_Raw,
                Fecha_Subida_Raw,
                Consumidor_Raw,
                Modulo_Raw,
                Turno_Raw,
                Valvula_Raw,
                Tipo_Evaluacion_Raw,
                Cama_Raw,
                Descripcion_Raw,
                Variedad_Raw,
                PlantasPorCama_Raw,
                PlantasConInduccion_Raw,
                BrotesConInduccion_Raw,
                BrotesTotales_Raw,
                BrotesConFlor_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


class ProcesadorInduccionFloral(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        # Grain: Geo + Tiempo + Variedad + Personal + Tipo_Evaluacion + Consumidor
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal', 'Tipo_Evaluacion', 'Codigo_Consumidor']
        self._columna_id = columna_id

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = _a_entero_nulo(fila.get('ID_Registro_Origen'))

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'induccion_floral')
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
                id_origen,
                fila.get('Variedad_Canonica'),
                fila.get('Variedad_Fuente_Raw'),
            )
            if id_var is None:
                continue

            id_personal = self._validar_y_resolver_personal(fila.get('DNI_Raw'))

            plantas_por_cama = _a_entero_no_negativo(fila.get('PlantasPorCama_Raw'))
            plantas_con_induccion = _a_entero_no_negativo(fila.get('PlantasConInduccion_Raw'))
            brotes_con_induccion = _a_entero_no_negativo(fila.get('BrotesConInduccion_Raw'))
            brotes_totales = _a_entero_no_negativo(fila.get('BrotesTotales_Raw'))
            brotes_con_flor = _a_entero_no_negativo(fila.get('BrotesConFlor_Raw'))

            if plantas_por_cama is None or plantas_por_cama <= 0:
                self.registrar_rechazo(id_origen, 'PlantasPorCama_Raw', fila.get('PlantasPorCama_Raw'), 'Cantidad de plantas por cama invalida')
                continue
            if plantas_con_induccion is None or plantas_con_induccion > plantas_por_cama:
                self.registrar_rechazo(id_origen, 'PlantasConInduccion_Raw', fila.get('PlantasConInduccion_Raw'), 'Plantas con induccion invalida o mayor al total por cama')
                continue
            if brotes_totales is None or brotes_totales <= 0:
                self.registrar_rechazo(id_origen, 'BrotesTotales_Raw', fila.get('BrotesTotales_Raw'), 'Cantidad de brotes totales invalida')
                continue
            if brotes_con_induccion is None or brotes_con_induccion > brotes_totales:
                self.registrar_rechazo(id_origen, 'BrotesConInduccion_Raw', fila.get('BrotesConInduccion_Raw'), 'Brotes con induccion invalida o mayor al total de brotes')
                continue
            if brotes_con_flor is None or brotes_con_flor > brotes_totales:
                self.registrar_rechazo(id_origen, 'BrotesConFlor_Raw', fila.get('BrotesConFlor_Raw'), 'Brotes con flor invalida o mayor al total de brotes')
                continue

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':                   resultado_geo['id_geografia'],
                '_id_modulo_catalogo':            resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':                      obtener_id_tiempo(fecha),
                'ID_Variedad':                    id_var,
                'ID_Personal':                    id_personal,
                'Tipo_Evaluacion':                _texto_nulo(fila.get('Tipo_Evaluacion_Raw')),
                'Codigo_Consumidor':              _texto_nulo(fila.get('Consumidor_Raw')),
                'Cantidad_Plantas_Por_Cama':      plantas_por_cama,
                'Cantidad_Plantas_Con_Induccion': plantas_con_induccion,
                'Cantidad_Brotes_Con_Induccion':  brotes_con_induccion,
                'Cantidad_Brotes_Totales':        brotes_totales,
                'Cantidad_Brotes_Con_Flor':       brotes_con_flor,
                'Pct_Plantas_Con_Induccion':      _pct(plantas_con_induccion, plantas_por_cama),
                'Pct_Brotes_Con_Induccion':       _pct(brotes_con_induccion, brotes_totales),
                'Pct_Brotes_Con_Flor':            _pct(brotes_con_flor, brotes_totales),
                'Fecha_Evento':                   fecha,
                'Estado_DQ':                      'OK',
                'id_origen_rastreo':              id_origen,
            })
        return payload


def cargar_fact_induccion_floral(engine: Engine) -> dict:
    proc = ProcesadorInduccionFloral(engine, columna_id='ID_Induccion_Floral')

    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Fecha_Subida_Raw', 'Consumidor_Raw',
        'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Tipo_Evaluacion_Raw',
        'Cama_Raw', 'Descripcion_Raw', 'Variedad_Raw', 'PlantasPorCama_Raw',
        'PlantasConInduccion_Raw', 'BrotesConInduccion_Raw', 'BrotesTotales_Raw',
        'BrotesConFlor_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df['Variedad_Fuente_Raw'] = df['Variedad_Raw'].where(
            df['Variedad_Raw'].notna(),
            df['Descripcion_Raw'],
        )
        df, cuar_var = homologar_columna(
            df, 'Variedad_Fuente_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Induccion_Floral',
        )
        df = proc.pre_limpiar_duplicados_batch(df, ['Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 'DNI_Raw', 'Tipo_Evaluacion_Raw', 'Consumidor_Raw'])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_InduccionFloral')

        return proc.finalizar_proceso(contexto)
