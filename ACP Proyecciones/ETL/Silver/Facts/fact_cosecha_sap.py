"""
fact_cosecha_sap.py
===================
Carga Silver.Fact_Cosecha_SAP desde:
  - Bronce.Reporte_Cosecha
  - Bronce.Data_SAP

Grain: Fecha + Geografia + Variedad + Condicion_Cultivo
FKs obligatorias: ID_Tiempo, ID_Geografia, ID_Variedad, ID_Condicion_Cultivo
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from config.parametros import obtener_int
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import procesar_fecha, obtener_id_tiempo
from utils.texto import titulo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_COSECHA = 'Bronce.Reporte_Cosecha'
TABLA_SAP     = 'Bronce.Data_SAP'
TABLA_DESTINO = 'Silver.Fact_Cosecha_SAP'


def _obtener_id_condicion_default() -> int:
    try:
        return obtener_int('ID_CONDICION_CULTIVO_DEFAULT', 1)
    except Exception:
        return 1


def _leer_bronce_cosecha(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Reporte_Cosecha,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                Variedad_Raw,
                KgNeto_Raw,
                Jabas_Raw,
                Lote_Raw,
                Responsable_Raw
            FROM {TABLA_COSECHA}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _leer_bronce_sap(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Data_SAP,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                Variedad_Raw,
                Peso_Bruto_Raw,
                Peso_Neto_Raw,
                Cantidad_Jabas_Raw,
                Lote_Raw,
                Almacen_Raw,
                Doc_Remision_Raw,
                Codigo_Cliente_Raw,
                Responsable_Raw,
                Descripcion_Material_Raw,
                Material_Codigo_Raw,
                Fecha_Recepcion_Raw
            FROM {TABLA_SAP}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_decimal(v):
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def _a_int(v):
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return None


class ProcesadorCosechaReporte(BaseFactProcessor):
    """Procesador para Bronce.Reporte_Cosecha → Silver.Fact_Cosecha_SAP."""

    def __init__(self, engine: Engine, id_condicion_default: int):
        super().__init__(engine, TABLA_COSECHA, TABLA_DESTINO)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Condicion_Cultivo']
        self._id_condicion_default = id_condicion_default

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Reporte_Cosecha'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'cosecha_sap')
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
            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':        resultado_geo['id_geografia'],
                '_id_modulo_catalogo': resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':           obtener_id_tiempo(fecha),
                'ID_Variedad':         id_var,
                'ID_Condicion_Cultivo': self._id_condicion_default,
                'Kg_Brutos':           None,
                'Kg_Neto_MP':          _a_decimal(fila.get('KgNeto_Raw')),
                'Cantidad_Jabas':      _a_int(fila.get('Jabas_Raw')),
                'Lote':                fila.get('Lote_Raw'),
                'Almacen':             None,
                'Doc_Remision':        None,
                'Codigo_Cliente':      None,
                'Responsable':         titulo(fila.get('Responsable_Raw')),
                'Descripcion_Material': None,
                'Codigo_SAP_Material': None,
                'Fecha_Recepcion':     None,
                'Fecha_Evento':        fecha,
                'Estado_DQ':           'OK',
                'id_origen_rastreo':   id_origen,
            })
        return payload


class ProcesadorCosechaSAP(BaseFactProcessor):
    """Procesador para Bronce.Data_SAP → Silver.Fact_Cosecha_SAP."""

    def __init__(self, engine: Engine, id_condicion_default: int):
        super().__init__(engine, TABLA_SAP, TABLA_DESTINO)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Condicion_Cultivo']
        self._id_condicion_default = id_condicion_default

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Data_SAP'])

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'cosecha_sap')
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

            fecha_recepcion, _ = procesar_fecha(fila.get('Fecha_Recepcion_Raw'), dominio='historico')

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':        resultado_geo['id_geografia'],
                '_id_modulo_catalogo': resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':           obtener_id_tiempo(fecha),
                'ID_Variedad':         id_var,
                'ID_Condicion_Cultivo': self._id_condicion_default,
                'Kg_Brutos':           _a_decimal(fila.get('Peso_Bruto_Raw')),
                'Kg_Neto_MP':          _a_decimal(fila.get('Peso_Neto_Raw')),
                'Cantidad_Jabas':      _a_int(fila.get('Cantidad_Jabas_Raw')),
                'Lote':                fila.get('Lote_Raw'),
                'Almacen':             fila.get('Almacen_Raw'),
                'Doc_Remision':        fila.get('Doc_Remision_Raw'),
                'Codigo_Cliente':      fila.get('Codigo_Cliente_Raw'),
                'Responsable':         titulo(fila.get('Responsable_Raw')),
                'Descripcion_Material': fila.get('Descripcion_Material_Raw'),
                'Codigo_SAP_Material': fila.get('Material_Codigo_Raw'),
                'Fecha_Recepcion':     fecha_recepcion,
                'Fecha_Evento':        fecha,
                'Estado_DQ':           'OK',
                'id_origen_rastreo':   id_origen,
            })
        return payload


def cargar_fact_cosecha_sap(engine: Engine) -> dict:
    id_condicion_default = _obtener_id_condicion_default()

    df_cosecha = _leer_bronce_cosecha(engine)
    df_sap = _leer_bronce_sap(engine)

    if df_cosecha.empty and df_sap.empty:
        return _finalizar_resumen_fact({'leidos': 0, 'insertados': 0, 'rechazados': 0, 'cuarentena': []})

    proc_cosecha = ProcesadorCosechaReporte(engine, id_condicion_default)
    proc_sap = ProcesadorCosechaSAP(engine, id_condicion_default)

    proc_cosecha.resumen['leidos'] = len(df_cosecha)
    proc_sap.resumen['leidos'] = len(df_sap)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        # Homologar variedades de cada fuente dentro de la misma transaccion
        if not df_cosecha.empty:
            df_cosecha, cuar_cosecha = homologar_columna(
                df_cosecha, 'Variedad_Raw', 'Variedad_Canonica', TABLA_COSECHA, conexion
            )
            proc_cosecha.resumen['cuarentena'].extend(cuar_cosecha)

        if not df_sap.empty:
            df_sap, cuar_sap = homologar_columna(
                df_sap, 'Variedad_Raw', 'Variedad_Canonica', TABLA_SAP, conexion
            )
            proc_sap.resumen['cuarentena'].extend(cuar_sap)

        # Construir payloads y cargar cada fuente con su procesador
        if not df_cosecha.empty:
            payload_cosecha = proc_cosecha._construir_payload(df_cosecha)
            proc_cosecha._ejecutar_insercion_masiva_segura(contexto, payload_cosecha, '#Temp_CosechaReporte')
            proc_cosecha.finalizar_proceso(contexto)

        if not df_sap.empty:
            payload_sap = proc_sap._construir_payload(df_sap)
            proc_sap._ejecutar_insercion_masiva_segura(contexto, payload_sap, '#Temp_CosechaSAP')
            proc_sap.finalizar_proceso(contexto)

    # Consolidar resumen de ambas fuentes
    resumen_total = {
        'leidos':      proc_cosecha.resumen['leidos'] + proc_sap.resumen['leidos'],
        'insertados':  proc_cosecha.resumen['insertados'] + proc_sap.resumen['insertados'],
        'rechazados':  proc_cosecha.resumen['rechazados'] + proc_sap.resumen['rechazados'],
        'cuarentena':  proc_cosecha.resumen['cuarentena'] + proc_sap.resumen['cuarentena'],
    }
    return _finalizar_resumen_fact(resumen_total)
