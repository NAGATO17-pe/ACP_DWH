"""
fact_tareo.py
=============
Carga Silver.Fact_Tareo desde Bronce.Consolidado_Tareos.

Grain: Fecha + DNI + Actividad + Geo
FKs obligatorias: ID_Tiempo, ID_Personal, ID_Actividad_Operativa, ID_Geografia
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from config.parametros import TOKENS_FECHA_NO_OPERATIVA, TOKENS_SUPERVISOR_NO_OPERATIVO
from utils.contexto_transaccional import ContextoTransaccionalETL
from mdm.lookup import obtener_id_actividad
from utils.fechas import obtener_id_tiempo
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Consolidado_Tareos'
TABLA_DESTINO = 'Silver.Fact_Tareo'


def _leer_bronce(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Tareo,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                DNIResponsable_Raw,
                IDPersonalGeneral_Raw,
                Labor_Raw,
                HorasTrabajadas_Raw,
                IDPlanilla_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _es_fila_no_operativa(fila) -> bool:
    fecha_raw = str(fila.get('Fecha_Raw') or '').strip()
    supervisor_raw = str(fila.get('IDPersonalGeneral_Raw') or '').strip().upper()
    return fecha_raw.upper() in TOKENS_FECHA_NO_OPERATIVA or supervisor_raw in TOKENS_SUPERVISOR_NO_OPERATIVO


class ProcesadorTareo(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Personal', 'ID_Actividad_Operativa']
        self.ids_descartados: list[int] = []

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = None
            try:
                id_origen = int(fila['ID_Tareo'])
            except (ValueError, TypeError):
                pass

            if _es_fila_no_operativa(fila):
                if id_origen is not None:
                    self.ids_descartados.append(id_origen)
                continue

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'tareo')
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                fila.get('Fundo_Raw'),
                fila.get('Modulo_Raw'),
            )
            if resultado_geo is None:
                continue

            id_personal = self._validar_y_resolver_personal(fila.get('DNIResponsable_Raw'))

            id_supervisor = self._validar_y_resolver_personal(fila.get('IDPersonalGeneral_Raw'))
            if id_supervisor == -1:
                id_supervisor = None

            id_actividad = obtener_id_actividad(fila.get('Labor_Raw'), self.engine)
            if not id_actividad:
                self.registrar_rechazo(
                    id_origen,
                    columna='Labor_Raw',
                    valor=fila.get('Labor_Raw'),
                    motivo='Actividad no reconocida en Dim_Actividad_Operativa',
                )
                continue

            try:
                horas = float(str(fila.get('HorasTrabajadas_Raw', 0)).replace(',', '.'))
            except (ValueError, TypeError):
                horas = 0.0

            planilla = str(fila.get('IDPlanilla_Raw', '')) or None

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':           resultado_geo['id_geografia'],
                '_id_modulo_catalogo':      resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':              obtener_id_tiempo(fecha),
                'ID_Personal':            id_personal,
                'ID_Actividad_Operativa': id_actividad,
                'ID_Personal_Supervisor': id_supervisor,
                'Horas_Trabajadas':       horas,
                'ID_Planilla':            planilla,
                'Es_Observado_SAP':       0,
                'Fecha_Evento':           fecha,
                'id_origen_rastreo':      id_origen,
            })
        return payload


def cargar_fact_tareo(engine: Engine) -> dict:
    proc = ProcesadorTareo(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'DNIResponsable_Raw',
        'IDPersonalGeneral_Raw', 'Labor_Raw', 'HorasTrabajadas_Raw',
        'IDPlanilla_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Tareo')

        # Marcar DESCARTADO para filas no operativas (encabezados, totales, etc.)
        if proc.ids_descartados:
            contexto.marcar_estado_carga(TABLA_ORIGEN, 'ID_Tareo', proc.ids_descartados, estado='DESCARTADO')

        return proc.finalizar_proceso(contexto)
