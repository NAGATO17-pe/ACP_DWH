"""
fact_peladas.py
===============
Carga Silver.Fact_Peladas desde Bronce.Peladas.

Grain: Fecha + Geo + Variedad + Punto
Validación crítica: Muestras >= 1 (evita división por cero)
"""

from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_muestras
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    parsear_valores_raw as _parsear_valores_raw,
)
from utils.tipos import a_entero, obtener_valor_raw as _obtener_valor_raw_util


TABLA_ORIGEN  = 'Bronce.Peladas'
TABLA_DESTINO = 'Silver.Fact_Peladas'


def _leer_bronce(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        columnas_resultado = conexion.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'Bronce'
              AND TABLE_NAME = 'Peladas'
        """)).fetchall()
        columnas_disponibles = {str(fila[0]) for fila in columnas_resultado}

        def _columna_sql(nombre_columna: str) -> str:
            if nombre_columna in columnas_disponibles:
                return nombre_columna
            return f"CAST(NULL AS NVARCHAR(MAX)) AS {nombre_columna}"

        filtro_estado = "WHERE Estado_Carga = 'CARGADO'" if 'Estado_Carga' in columnas_disponibles else ""
        columnas_select = [
            'ID_Peladas',
            _columna_sql('Fecha_Raw'),
            _columna_sql('Fundo_Raw'),
            _columna_sql('Modulo_Raw'),
            _columna_sql('Turno_Raw'),
            _columna_sql('Valvula_Raw'),
            _columna_sql('Variedad_Raw'),
            _columna_sql('DNI_Raw'),
            _columna_sql('Evaluador_Raw'),
            _columna_sql('Punto_Raw'),
            _columna_sql('Muestras_Raw'),
            _columna_sql('BotonesFlorales_Raw'),
            _columna_sql('Flores_Raw'),
            _columna_sql('BayasPequenas_Raw'),
            _columna_sql('BayasGrandes_Raw'),
            _columna_sql('Fase1_Raw'),
            _columna_sql('Fase2_Raw'),
            _columna_sql('BayasCremas_Raw'),
            _columna_sql('BayasMaduras_Raw'),
            _columna_sql('BayasCosechables_Raw'),
            _columna_sql('YemasActivadas_Raw'),
            _columna_sql('PlantasProductivas_Raw'),
            _columna_sql('PlantasNoProductivas_Raw'),
            _columna_sql('Valores_Raw'),
        ]

        resultado = conexion.execute(text(f"""
            SELECT {", ".join(columnas_select)}
            FROM {TABLA_ORIGEN}
            {filtro_estado}
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_int(valor, default: int = 0) -> int:
    n = a_entero(valor)
    return max(0, n) if n is not None else default


def _obtener_campo(fila: pd.Series, nombre_columna: str, valores_raw: dict) -> Any:
    """Retorna el valor de la columna directa si existe, sino busca en valores_raw."""
    valor = fila.get(nombre_columna)
    if valor is not None and str(valor).strip() not in ('', 'None', 'nan'):
        return valor
    return _obtener_valor_raw_util(fila, nombre_columna, valores_raw)


class ProcesadorPeladas(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Punto']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Peladas'])
            valores_raw = _parsear_valores_raw(fila.get('Valores_Raw'))

            fecha = self._validar_y_resolver_fecha(
                id_origen,
                _obtener_campo(fila, 'Fecha_Raw', valores_raw),
                'peladas',
            )
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                _obtener_campo(fila, 'Fundo_Raw', valores_raw),
                _obtener_campo(fila, 'Modulo_Raw', valores_raw),
                turno=_obtener_campo(fila, 'Turno_Raw', valores_raw),
                valvula=_obtener_campo(fila, 'Valvula_Raw', valores_raw),
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

            muestras, error_muestras = validar_muestras(
                _obtener_campo(fila, 'Muestras_Raw', valores_raw)
            )
            if error_muestras:
                self.registrar_rechazo(
                    id_origen,
                    columna=error_muestras.get('columna', 'Muestras'),
                    valor=error_muestras.get('valor'),
                    motivo=error_muestras.get('motivo', 'Muestras invalidas'),
                    tipo_regla='DQ',
                    severidad=error_muestras.get('severidad', 'ALTO'),
                )
                continue

            id_personal = self._validar_y_resolver_personal(
                _obtener_campo(fila, 'DNI_Raw', valores_raw)
            )

            try:
                punto = int(float(str(_obtener_campo(fila, 'Punto_Raw', valores_raw) or 1)))
            except (ValueError, TypeError):
                punto = 1

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':           resultado_geo['id_geografia'],
                '_id_modulo_catalogo':      resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':              obtener_id_tiempo(fecha),
                'ID_Variedad':            id_var,
                'ID_Personal':            id_personal,
                'Punto':                  punto,
                'Muestras':               muestras,
                'Botones_Florales':       _a_int(_obtener_campo(fila, 'BotonesFlorales_Raw', valores_raw)),
                'Flores':                 _a_int(_obtener_campo(fila, 'Flores_Raw', valores_raw)),
                'Bayas_Pequenas':         _a_int(_obtener_campo(fila, 'BayasPequenas_Raw', valores_raw)),
                'Bayas_Grandes':          _a_int(_obtener_campo(fila, 'BayasGrandes_Raw', valores_raw)),
                'Fase_1':                 _a_int(_obtener_campo(fila, 'Fase1_Raw', valores_raw)),
                'Fase_2':                 _a_int(_obtener_campo(fila, 'Fase2_Raw', valores_raw)),
                'Bayas_Cremas':           _a_int(_obtener_campo(fila, 'BayasCremas_Raw', valores_raw)),
                'Bayas_Maduras':          _a_int(_obtener_campo(fila, 'BayasMaduras_Raw', valores_raw)),
                'Bayas_Cosechables':      _a_int(_obtener_campo(fila, 'BayasCosechables_Raw', valores_raw)),
                'Yemas_Activadas':        _a_int(_obtener_campo(fila, 'YemasActivadas_Raw', valores_raw)),
                'Plantas_Productivas':    _a_int(_obtener_campo(fila, 'PlantasProductivas_Raw', valores_raw)),
                'Plantas_No_Productivas': _a_int(_obtener_campo(fila, 'PlantasNoProductivas_Raw', valores_raw)),
                'Fecha_Evento':           fecha,
                'Estado_DQ':              'OK',
                'id_origen_rastreo':      id_origen,
            })
        return payload


def cargar_fact_peladas(engine: Engine) -> dict:
    proc = ProcesadorPeladas(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Variedad_Raw', 'DNI_Raw', 'Evaluador_Raw', 'Punto_Raw', 'Muestras_Raw',
        'BotonesFlorales_Raw', 'Flores_Raw', 'BayasPequenas_Raw', 'BayasGrandes_Raw',
        'Fase1_Raw', 'Fase2_Raw', 'BayasCremas_Raw', 'BayasMaduras_Raw',
        'BayasCosechables_Raw', 'YemasActivadas_Raw', 'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw',
        'Valores_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Peladas'
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Peladas')

        return proc.finalizar_proceso(contexto)
