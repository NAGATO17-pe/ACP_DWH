"""
fact_evaluacion_vegetativa.py
==============================
Carga Silver.Fact_Evaluacion_Vegetativa desde Bronce.Evaluacion_Vegetativa.

Layout definitivo:
- DNI / evaluador
- modulo / turno / valvula / cama
- descripcion como variedad fuente
- plantas evaluadas / plantas en floracion
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.sql_lotes import ejecutar_en_lotes
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    a_entero_no_negativo as _a_entero_positivo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN  = 'Bronce.Evaluacion_Vegetativa'
TABLA_DESTINO = 'Silver.Fact_Evaluacion_Vegetativa'

SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Evaluacion_Vegetativa (
        ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal,
        Tipo_Evaluacion,
        Cantidad_Plantas_Evaluadas, Cantidad_Plantas_en_Floracion,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad, :id_personal,
        :tipo_evaluacion,
        :plantas_evaluadas, :plantas_en_floracion,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _validar_layout_migrado(engine: Engine) -> str:
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Evaluacion_Vegetativa',
        columnas_bronce_requeridas={
            'ID_Evaluacion_Vegetativa',
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
            'N_Plantas_Evaluadas_Raw',
            'N_Plantas_en_Floracion_Raw',
        },
        columnas_silver_requeridas={
            'ID_Personal',
            'Tipo_Evaluacion',
            'Cantidad_Plantas_Evaluadas',
            'Cantidad_Plantas_en_Floracion',
        },
        nombre_layout='Evaluacion_Vegetativa',
    )


def _leer_bronce(engine: Engine, columna_id: str) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                {columna_id} AS ID_Registro_Origen,
                Fecha_Raw,
                DNI_Raw,
                Fecha_Subida_Raw,
                Nombres_Raw,
                Consumidor_Raw,
                Modulo_Raw,
                Turno_Raw,
                Valvula_Raw,
                Evaluacion_Raw,
                Cama_Raw,
                Descripcion_Raw,
                N_Plantas_Evaluadas_Raw,
                N_Plantas_en_Floracion_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _marcar_estado_por_firma(recurso_db, claves: list[dict], estado: str) -> None:
    if not claves:
        return

    sentencia = text(f"""
        UPDATE TOP (1) {TABLA_ORIGEN}
        SET Estado_Carga = :estado_carga
        WHERE Estado_Carga IN ('CARGADO', 'RECHAZADO', 'PROCESADO')
          AND ISNULL(Fecha_Raw, '') = ISNULL(:fecha_raw, '')
          AND ISNULL(DNI_Raw, '') = ISNULL(:dni_raw, '')
          AND ISNULL(Modulo_Raw, '') = ISNULL(:modulo_raw, '')
          AND ISNULL(Turno_Raw, '') = ISNULL(:turno_raw, '')
          AND ISNULL(Valvula_Raw, '') = ISNULL(:valvula_raw, '')
          AND ISNULL(Cama_Raw, '') = ISNULL(:cama_raw, '')
          AND ISNULL(Descripcion_Raw, '') = ISNULL(:descripcion_raw, '')
          AND ISNULL(N_Plantas_Evaluadas_Raw, '') = ISNULL(:plantas_evaluadas_raw, '')
          AND ISNULL(N_Plantas_en_Floracion_Raw, '') = ISNULL(:plantas_floracion_raw, '')
    """)
    payload = [
        {
            **clave,
            'estado_carga': estado,
        }
        for clave in claves
    ]
    ejecutar_en_lotes(recurso_db, sentencia, payload)


class ProcesadorEvaluacionVegetativa(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal', 'Tipo_Evaluacion']
        self._columna_id = columna_id
        self._claves_procesadas: list[dict] = []
        self._claves_rechazadas: list[dict] = []

    def _firma_fila(self, fila) -> dict:
        return {
            'fecha_raw':             fila.get('Fecha_Raw'),
            'dni_raw':               fila.get('DNI_Raw'),
            'modulo_raw':            fila.get('Modulo_Raw'),
            'turno_raw':             fila.get('Turno_Raw'),
            'valvula_raw':           fila.get('Valvula_Raw'),
            'cama_raw':              fila.get('Cama_Raw'),
            'descripcion_raw':       fila.get('Descripcion_Raw'),
            'plantas_evaluadas_raw': fila.get('N_Plantas_Evaluadas_Raw'),
            'plantas_floracion_raw': fila.get('N_Plantas_en_Floracion_Raw'),
        }

    def _rechazar_fila(self, id_origen, columna, valor, motivo, fila, tipo_regla='DQ') -> None:
        self.registrar_rechazo(id_origen or 0, columna, valor, motivo, tipo_regla=tipo_regla)
        if id_origen is None:
            self._claves_rechazadas.append(self._firma_fila(fila))

    def _construir_payload(self, df) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = _a_entero_nulo(fila.get('ID_Registro_Origen'))

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'evaluacion_vegetativa')
            if fecha is None:
                if id_origen is None:
                    self._claves_rechazadas.append(self._firma_fila(fila))
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
                if id_origen is None:
                    self._claves_rechazadas.append(self._firma_fila(fila))
                continue

            id_var = self._validar_y_resolver_variedad(id_origen, fila.get('Variedad_Canonica'), fila.get('Descripcion_Raw'))
            if id_var is None:
                if id_origen is None:
                    self._claves_rechazadas.append(self._firma_fila(fila))
                continue

            id_tiempo = obtener_id_tiempo(fecha)
            if id_tiempo is None:
                self._rechazar_fila(id_origen, 'Fecha_Raw', fila.get('Fecha_Raw'), 'Fecha valida pero fuera de Dim_Tiempo', fila)
                continue

            plantas_evaluadas = _a_entero_positivo(fila.get('N_Plantas_Evaluadas_Raw'))
            if plantas_evaluadas is None or plantas_evaluadas == 0:
                self._rechazar_fila(id_origen, 'N_Plantas_Evaluadas_Raw', fila.get('N_Plantas_Evaluadas_Raw'), 'Cantidad de plantas evaluadas invalida', fila)
                continue

            plantas_floracion = _a_entero_positivo(fila.get('N_Plantas_en_Floracion_Raw'))
            if plantas_floracion is None or plantas_floracion > plantas_evaluadas:
                self._rechazar_fila(id_origen, 'N_Plantas_en_Floracion_Raw', fila.get('N_Plantas_en_Floracion_Raw'), 'Plantas en floracion invalida o mayor al total evaluado', fila)
                continue

            id_personal = self._validar_y_resolver_personal(fila.get('DNI_Raw'))

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            else:
                self._claves_procesadas.append(self._firma_fila(fila))

            payload.append({
                'ID_Geografia':                    resultado_geo['id_geografia'],
                '_id_modulo_catalogo':               resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':                       id_tiempo,
                'ID_Variedad':                     id_var,
                'ID_Personal':                     id_personal,
                'Tipo_Evaluacion':                 fila.get('Evaluacion_Raw') or 'SIN_TIPO',
                'Cantidad_Plantas_Evaluadas':      plantas_evaluadas,
                'Cantidad_Plantas_en_Floracion':   plantas_floracion,
                'Fecha_Evento':                    fecha,
                'Estado_DQ':                       'OK',
                'id_origen_rastreo':               id_origen or 0,
            })
        return payload

    def finalizar_proceso(self, contexto) -> dict:
        # Marca por firma compuesta los registros sin PK autonumérica
        conexion = contexto._conexion_activa()
        if self._claves_procesadas:
            _marcar_estado_por_firma(conexion, self._claves_procesadas, 'PROCESADO')
        if self._claves_rechazadas:
            _marcar_estado_por_firma(conexion, self._claves_rechazadas, 'RECHAZADO')
        return super().finalizar_proceso(contexto)


def cargar_fact_evaluacion_vegetativa(engine: Engine) -> dict:
    proc = ProcesadorEvaluacionVegetativa(engine, columna_id='ID_Evaluacion_Vegetativa')

    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Fecha_Subida_Raw', 'Nombres_Raw',
        'Consumidor_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Evaluacion_Raw', 'Cama_Raw', 'Descripcion_Raw',
        'N_Plantas_Evaluadas_Raw', 'N_Plantas_en_Floracion_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Descripcion_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Evaluacion_Vegetativa',
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_EvaluacionVegetativa')

        return proc.finalizar_proceso(contexto)
