"""
fact_tasa_crecimiento_brotes.py
===============================
Carga Silver.Fact_Tasa_Crecimiento_Brotes desde Bronce.Tasa_Crecimiento_Brotes.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from mdm.homologador import homologar_columna
from mdm.bridges_tasa_crecimiento import (
    garantizar_bridge_geografia_cama,
    resolver_id_cama,
    resolver_id_condicion,
    sincronizar_bridge_modulo_campana_condicion,
)
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo, procesar_fecha
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    texto_nulo as _texto_nulo,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN = 'Bronce.Tasa_Crecimiento_Brotes'
TABLA_DESTINO = 'Silver.Fact_Tasa_Crecimiento_Brotes'

SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Tasa_Crecimiento_Brotes (
        ID_Geografia, ID_Cama_Catalogo, ID_Tiempo, ID_Variedad, ID_Personal,
        ID_Condicion,
        Tipo_Evaluacion, Estado_Vegetativo,
        Tipo_Tallo, Codigo_Ensayo, Codigo_Origen,
        Observacion,
        Fecha_Poda_Aux, Dias_Desde_Poda, Medida_Crecimiento,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_cama, :id_tiempo, :id_variedad, :id_personal,
        :id_condicion,
        :tipo_evaluacion, :estado_vegetativo,
        :tipo_tallo, :codigo_ensayo, :codigo_origen,
        :observacion,
        :fecha_poda_aux, :dias_desde_poda, :medida_crecimiento,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _a_decimal_nulo(valor) -> float | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip().replace(',', '.')
        if texto in ('', 'None', 'nan'):
            return None
        return float(texto)
    except (ValueError, TypeError):
        return None


def _validar_layout_migrado(engine: Engine) -> str:
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Tasa_Crecimiento',
        columnas_bronce_requeridas={
            'ID_Tasa_Crecimiento',
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Condicion_Raw',
            'Estado_Vegetativo_Raw',
            'Variedad_Raw',
            'Tipo_Tallo_Raw',
            'Ensayo_Raw',
            'Medida_Raw',
            'Fecha_Poda_Aux_Raw',
            'Campana_Raw',
            'Tipo_Evaluacion_Raw',
            'Estado_Carga',
        },
        columnas_silver_requeridas={
            'ID_Geografia',
            'ID_Cama_Catalogo',
            'ID_Tiempo',
            'ID_Variedad',
            'ID_Personal',
            'ID_Condicion',
            'Codigo_Ensayo',
            'Codigo_Origen',
            'Fecha_Poda_Aux',
            'Dias_Desde_Poda',
            'Medida_Crecimiento',
        },
        nombre_layout='Tasa_Crecimiento_Brotes',
    )


def _leer_bronce(engine: Engine, columna_id: str) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                {columna_id} AS ID_Registro_Origen,
                Codigo_Origen_Raw,
                Semana_Raw,
                Dia_Raw,
                Fecha_Raw,
                DNI_Raw,
                Evaluador_Raw,
                Modulo_Raw,
                Turno_Raw,
                Valvula_Raw,
                Condicion_Raw,
                Estado_Vegetativo_Raw,
                Variedad_Raw,
                Cama_Raw,
                Tipo_Tallo_Raw,
                Ensayo_Raw,
                Medida_Raw,
                Fecha_Poda_Aux_Raw,
                Campana_Raw,
                Observacion_Raw,
                Tipo_Evaluacion_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


class ProcesadorTasaCrecimientoBrotes(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        # Grain: Geo + Cama + Tiempo + Variedad + Tipo_Evaluacion + Tipo_Tallo + Ensayo + Medida + Codigo_Origen
        self.columnas_clave_unica = [
            'ID_Geografia', 'ID_Cama_Catalogo', 'ID_Tiempo', 'ID_Variedad',
            'Tipo_Evaluacion', 'Tipo_Tallo', 'Codigo_Ensayo', 'Codigo_Origen', 'Medida_Crecimiento'
        ]
        self._columna_id = columna_id
        # Cache para fecha_poda_aux (dominio historico, sin rechazo)
        self._cache_fecha_poda: dict[str, tuple] = {}
        # Pares (id_geografia, id_cama, fecha_evento) que requieren upsert al Bridge_Geografia_Cama.
        # Se procesan post-insercion para no impactar el path caliente.
        self._pares_geo_cama: dict[tuple[int, int], object] = {}

    def _resolver_fecha_poda(self, valor) -> tuple:
        clave = str(valor).strip() if valor is not None else ''
        if clave not in self._cache_fecha_poda:
            self._cache_fecha_poda[clave] = procesar_fecha(valor, dominio='historico')
        return self._cache_fecha_poda[clave]

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = _a_entero_nulo(fila.get('ID_Registro_Origen'))

            fecha_evento = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'tasa_crecimiento_brotes')
            if fecha_evento is None:
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
                fila.get('Variedad_Raw'),
            )
            if id_var is None:
                continue

            codigo_ensayo = _texto_nulo(fila.get('Ensayo_Raw'))
            if codigo_ensayo is None:
                self.registrar_rechazo(id_origen, 'Ensayo_Raw', fila.get('Ensayo_Raw'), 'Codigo de ensayo vacio o invalido')
                continue

            medida_crecimiento = _a_decimal_nulo(fila.get('Medida_Raw'))
            if medida_crecimiento is None or medida_crecimiento < 0:
                self.registrar_rechazo(id_origen, 'Medida_Raw', fila.get('Medida_Raw'), 'Medida de crecimiento invalida o negativa')
                continue

            fecha_poda_aux = None
            dias_desde_poda = None
            valor_fecha_poda = _texto_nulo(fila.get('Fecha_Poda_Aux_Raw'))
            if valor_fecha_poda is not None:
                fecha_poda_aux, valida_poda = self._resolver_fecha_poda(valor_fecha_poda)
                if not valida_poda:
                    self.registrar_rechazo(id_origen, 'Fecha_Poda_Aux_Raw', fila.get('Fecha_Poda_Aux_Raw'), 'Fecha de poda auxiliar invalida')
                    continue
                dias_desde_poda = (fecha_evento.date() - fecha_poda_aux.date()).days
                if dias_desde_poda < 0:
                    self.registrar_rechazo(id_origen, 'Fecha_Poda_Aux_Raw', fila.get('Fecha_Poda_Aux_Raw'), 'Fecha de poda auxiliar posterior a la fecha de evaluacion')
                    continue

            id_personal = self._validar_y_resolver_personal(fila.get('DNI_Raw'))

            id_cama = resolver_id_cama(fila.get('Cama_Raw'), self.engine)
            id_condicion = resolver_id_condicion(fila.get('Condicion_Raw'), self.engine)

            id_geo = resultado_geo['id_geografia']
            if id_geo is not None and id_cama is not None:
                # Memoriza el par geo+cama (con la fecha mas antigua vista) para
                # registrarlo en Bridge_Geografia_Cama tras la insercion masiva.
                clave_par = (int(id_geo), int(id_cama))
                fecha_actual = fecha_evento.date() if hasattr(fecha_evento, 'date') else fecha_evento
                fecha_existente = self._pares_geo_cama.get(clave_par)
                if fecha_existente is None or fecha_actual < fecha_existente:
                    self._pares_geo_cama[clave_par] = fecha_actual

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':       id_geo,
                'ID_Cama_Catalogo':   id_cama,
                '_id_modulo_catalogo': resultado_geo.get('id_modulo_catalogo'),
                'ID_Tiempo':          obtener_id_tiempo(fecha_evento),
                'ID_Variedad':        id_var,
                'ID_Personal':        id_personal,
                'ID_Condicion':       id_condicion,
                'Tipo_Evaluacion':    _texto_nulo(fila.get('Tipo_Evaluacion_Raw')),
                'Estado_Vegetativo':  _texto_nulo(fila.get('Estado_Vegetativo_Raw')),
                'Tipo_Tallo':         _texto_nulo(fila.get('Tipo_Tallo_Raw')),
                'Codigo_Ensayo':      codigo_ensayo,
                'Codigo_Origen':      _texto_nulo(fila.get('Codigo_Origen_Raw')),
                'Observacion':        _texto_nulo(fila.get('Observacion_Raw')),
                'Fecha_Poda_Aux':     None if fecha_poda_aux is None else fecha_poda_aux.date(),
                'Dias_Desde_Poda':    dias_desde_poda,
                'Medida_Crecimiento': medida_crecimiento,
                'Fecha_Evento':       fecha_evento,
                'Estado_DQ':          'OK',
                'id_origen_rastreo':  id_origen,
            })
        return payload

    def _sincronizar_bridges(self, contexto: ContextoTransaccionalETL) -> None:
        """
        Post-insercion:
        1. Garantiza filas en Bridge_Geografia_Cama para cada (geo, cama) usado.
        2. Rellena ID_Condicion en Bridge_Modulo_Campana cuando aun es NULL,
           tomando la condicion mayoritaria observada en el fact por
           (modulo, variedad, campana).
        """
        if not self._pares_geo_cama:
            return

        conexion = contexto._conexion_activa()

        for (id_geo, id_cama), fecha_inicio in self._pares_geo_cama.items():
            garantizar_bridge_geografia_cama(conexion, id_geo, id_cama, fecha_inicio)

        # Backfill puntual del bridge modulo-campana: rellena solo filas con
        # ID_Condicion NULL usando la condicion mayoritaria del fact. Idempotente.
        conexion.execute(text("""
            WITH condicion_mayoritaria AS (
                SELECT
                    g.ID_Modulo_Catalogo,
                    f.ID_Variedad,
                    f.ID_Campana,
                    f.ID_Condicion,
                    ROW_NUMBER() OVER (
                        PARTITION BY g.ID_Modulo_Catalogo, f.ID_Variedad, f.ID_Campana
                        ORDER BY COUNT(*) DESC
                    ) AS rk
                FROM Silver.Fact_Tasa_Crecimiento_Brotes f
                JOIN Silver.Dim_Geografia g ON g.ID_Geografia = f.ID_Geografia
                WHERE f.ID_Condicion IS NOT NULL
                  AND f.ID_Campana   IS NOT NULL
                GROUP BY g.ID_Modulo_Catalogo, f.ID_Variedad, f.ID_Campana, f.ID_Condicion
            )
            UPDATE bmc
            SET bmc.ID_Condicion = cm.ID_Condicion
            FROM Silver.Bridge_Modulo_Campana bmc
            JOIN condicion_mayoritaria cm
              ON cm.rk = 1
             AND cm.ID_Modulo_Catalogo = bmc.ID_Modulo_Catalogo
             AND cm.ID_Variedad        = bmc.ID_Variedad
             AND cm.ID_Campana         = bmc.ID_Campana
            WHERE bmc.ID_Condicion IS NULL
        """))


def cargar_fact_tasa_crecimiento_brotes(engine: Engine) -> dict:
    proc = ProcesadorTasaCrecimientoBrotes(engine, columna_id='ID_Tasa_Crecimiento')

    cols_raw = [
        'Codigo_Origen_Raw', 'Semana_Raw', 'Dia_Raw', 'Fecha_Raw', 'DNI_Raw',
        'Evaluador_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Condicion_Raw',
        'Estado_Vegetativo_Raw', 'Variedad_Raw', 'Cama_Raw', 'Tipo_Tallo_Raw',
        'Ensayo_Raw', 'Medida_Raw', 'Fecha_Poda_Aux_Raw', 'Campana_Raw',
        'Observacion_Raw', 'Tipo_Evaluacion_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Tasa_Crecimiento',
        )
        df = proc.pre_limpiar_duplicados_batch(df, [
            'Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 
            'Tipo_Evaluacion_Raw', 'Tipo_Tallo_Raw', 'Ensayo_Raw', 'Medida_Raw', 'Codigo_Origen_Raw'
        ])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_TasaCrecimientoBrotes')
        proc._sincronizar_bridges(contexto)

        return proc.finalizar_proceso(contexto)
