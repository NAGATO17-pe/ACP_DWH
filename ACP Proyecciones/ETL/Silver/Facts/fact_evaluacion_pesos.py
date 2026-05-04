"""
fact_evaluacion_pesos.py
========================
Carga Silver.Fact_Evaluacion_Pesos desde Bronce.Evaluacion_Pesos.

Grain: Fecha + Geo + Personal + Variedad
FKs obligatorias: ID_Tiempo, ID_Geografia, ID_Variedad, ID_Personal
Validacion critica: Peso_Baya_g BETWEEN 0.5 AND 8.0
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_peso_baya
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Evaluacion_Pesos'
TABLA_DESTINO = 'Silver.Fact_Evaluacion_Pesos'


def _leer_bronce(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Evaluacion_Pesos,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                Valvula_Raw,
                Turno_Raw,
                Cama_Raw,
                Variedad_Raw,
                Evaluacion_Raw,
                DNI_Raw,
                PesoBaya_Raw,
                CantMuestra_Raw,
                BayasPequenas_Raw,
                PesoBayasPequenas_Raw,
                BayasGrandes_Raw,
                BayasFase1_Raw,
                PesoBayasFase1_Raw,
                BayasFase2_Raw,
                PesoBayasFase2_Raw,
                Cremas_Raw,
                PesoCremas_Raw,
                Maduras_Raw,
                PesoMaduras_Raw,
                Cosechables_Raw,
                PesoCosechables_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _calcular_peso_ponderado(fila) -> float | None:
    """
    Calcula el peso promedio ponderado de baya en gramos.
    Usa todas las categorias de bayas disponibles en el reporte horizontal.
    Retorna None si no hay datos suficientes para calcular.
    """
    def safe_float(val, default=0.0):
        try:
            return float(str(val)) if val is not None and str(val).strip() not in ('', 'None', 'nan') else default
        except (ValueError, TypeError):
            return default

    # Si ya viene un PesoBaya_Raw directo (otros formatos), usarlo
    peso_directo = safe_float(fila.get('PesoBaya_Raw'))
    cant_directo = safe_float(fila.get('CantMuestra_Raw'))
    if peso_directo > 0 and cant_directo > 0:
        return round(peso_directo / cant_directo, 4)

    # Calcular desde columnas horizontales
    pares = [
        ('BayasPequenas_Raw',  'PesoBayasPequenas_Raw'),
        ('BayasGrandes_Raw',   None),
        ('BayasFase1_Raw',     'PesoBayasFase1_Raw'),
        ('BayasFase2_Raw',     'PesoBayasFase2_Raw'),
        ('Cremas_Raw',         'PesoCremas_Raw'),
        ('Maduras_Raw',        'PesoMaduras_Raw'),
        ('Cosechables_Raw',    'PesoCosechables_Raw'),
    ]

    total_bayas = 0.0
    total_peso  = 0.0
    for col_cnt, col_peso in pares:
        cnt  = safe_float(fila.get(col_cnt))
        peso = safe_float(fila.get(col_peso)) if col_peso else 0.0
        total_bayas += cnt
        total_peso  += peso

    if total_bayas > 0 and total_peso > 0:
        return round(total_peso / total_bayas, 4)

    return None


def _safe_int(v) -> int:
    try:
        return max(0, int(float(str(v)))) if v is not None and str(v).strip() not in ('', 'None', 'nan') else 0
    except (ValueError, TypeError):
        return 0


class ProcesadorEvaluacionPesos(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO)
        # Grain: Geo + Tiempo + Variedad + Personal + Peso
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = None
            try:
                id_origen = int(fila['ID_Evaluacion_Pesos'])
            except (ValueError, TypeError):
                pass

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'evaluacion_pesos')
            if fecha is None:
                continue

            # Evaluacion_Pesos usa Valvula como modulo cuando Modulo_Raw esta vacio
            modulo_raw = fila.get('Modulo_Raw')
            valvula_raw = fila.get('Valvula_Raw')
            geo_modulo = modulo_raw if modulo_raw and str(modulo_raw).strip() not in ('None', '', 'nan') else valvula_raw

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                fila.get('Fundo_Raw'),
                geo_modulo,
                turno=fila.get('Turno_Raw'),
                valvula=fila.get('Valvula_Raw'),
                cama=fila.get('Cama_Raw'),
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

            id_personal = self._validar_y_resolver_personal(fila.get('DNI_Raw'))

            # Calcular peso ponderado desde columnas horizontales
            peso = _calcular_peso_ponderado(fila)
            if peso is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='PesoBaya',
                    valor=None,
                    motivo='No se pudo calcular peso promedio de baya',
                    severidad='MEDIO',
                )
                continue

            # Validar rango DQ dinámico (desde Config.Parametros_Pipeline)
            peso_val, error_peso = validar_peso_baya(peso, config=self.config_params)
            if error_peso:
                self.registrar_rechazo(
                    id_origen,
                    columna=error_peso.get('columna', 'Peso_Baya_g'),
                    valor=error_peso.get('valor'),
                    motivo=error_peso.get('motivo', 'Peso invalido'),
                    severidad=error_peso.get('severidad', 'ALTO'),
                )
                continue

            cantidad = (
                _safe_int(fila.get('BayasPequenas_Raw')) +
                _safe_int(fila.get('BayasGrandes_Raw'))  +
                _safe_int(fila.get('BayasFase1_Raw'))     +
                _safe_int(fila.get('BayasFase2_Raw'))     +
                _safe_int(fila.get('Cremas_Raw'))         +
                _safe_int(fila.get('Maduras_Raw'))        +
                _safe_int(fila.get('Cosechables_Raw'))
            ) or _safe_int(fila.get('CantMuestra_Raw'))

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':              resultado_geo['id_geografia'],
                '_id_modulo_catalogo':         resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':                 obtener_id_tiempo(fecha),
                'ID_Variedad':               id_var,
                'ID_Personal':               id_personal,
                'Peso_Promedio_Baya_g':      peso_val,
                'Cantidad_Bayas_Muestra':    cantidad,
                'Fecha_Evento':              fecha,
                'Estado_DQ':                 'OK',
                'id_origen_rastreo':         id_origen,
            })
        return payload


def cargar_fact_evaluacion_pesos(engine: Engine) -> dict:
    proc = ProcesadorEvaluacionPesos(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Valvula_Raw', 'Turno_Raw',
        'Cama_Raw', 'Variedad_Raw', 'Evaluacion_Raw', 'DNI_Raw', 'PesoBaya_Raw',
        'CantMuestra_Raw', 'BayasPequenas_Raw', 'PesoBayasPequenas_Raw',
        'BayasGrandes_Raw', 'BayasFase1_Raw', 'PesoBayasFase1_Raw',
        'BayasFase2_Raw', 'PesoBayasFase2_Raw', 'Cremas_Raw', 'PesoCremas_Raw',
        'Maduras_Raw', 'PesoMaduras_Raw', 'Cosechables_Raw', 'PesoCosechables_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Evaluacion_Pesos'
        )
        df = proc.pre_limpiar_duplicados_batch(df, ['Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 'DNI_Raw'])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_EvaluacionPesos')

        return proc.finalizar_proceso(contexto)
