"""
fact_maduracion.py
==================
Carga Silver.Fact_Maduracion desde Bronce.Maduracion.

Grain: Geo + Tiempo + Variedad + ID_Cinta + ID_Organo
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from mdm.homologador import cargar_diccionario, cargar_catalogo_variedades, homologar_valor
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    motivo_cuarentena_geografia as _motivo_cuarentena_geografia,
)
from mdm.lookup import obtener_id_cinta, obtener_id_estado_fenologico
from utils.fechas import obtener_id_tiempo

TABLA_ORIGEN = 'Bronce.Maduracion'
TABLA_DESTINO = 'Silver.Fact_Maduracion'

# Fallback en caso de que MDM.Diccionario_Homologacion no tenga entradas para estado ciclo.
_MAPA_ESTADO_CICLO_FALLBACK: dict[str, str] = {
    'BOTON FLORAL': 'Boton Floral', 'BOTON': 'Boton Floral', 'FLOR': 'Flor',
    'PEQUENA': 'Pequena', 'PEQUENA FRUTA': 'Pequena', 'VERDE': 'Verde',
    'INICIO FASE 1': 'Inicio F1', 'INICIO F1': 'Inicio F1', 'FASE 1': 'Inicio F1',
    'INICIO FASE 2': 'Inicio F2', 'INICIO F2': 'Inicio F2', 'FASE 2': 'Inicio F2',
    'CREMA': 'Crema', 'MADURA': 'Madura', 'MADURO': 'Madura', 'PINTON': 'Crema',
    'PINTONA': 'Crema', 'COSECHABLE': 'Cosechable',
}

MAPA_ESTADO_POR_ID = {
    0: 'Boton Floral', 1: 'Flor', 2: 'Pequena', 3: 'Verde', 4: 'Inicio F1',
    5: 'Inicio F2', 6: 'Crema', 7: 'Madura', 8: 'Cosechable',
}





def _cargar_mapa_estado_desde_db(engine: Engine) -> dict[str, str]:
    try:
        with engine.connect() as conexion:
            resultado = conexion.execute(text("""
                SELECT Texto_Crudo, Valor_Canonico
                FROM MDM.Diccionario_Homologacion
                WHERE Tabla_Origen  = 'Bronce.Maduracion'
                  AND Campo_Origen  = 'DESCRIPCIONESTADOCICLO_Raw'
                  AND Aprobado_Por IS NOT NULL
                  AND Aprobado_Por != 'PENDIENTE'
            """)).fetchall()
        if resultado:
            return {str(fila[0]).strip().upper(): str(fila[1]).strip() for fila in resultado}
    except:
        pass
    return dict(_MAPA_ESTADO_CICLO_FALLBACK)


class ProcesadorMaduracion(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Maduracion')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Cinta', 'ID_Organo']
        self.columna_tiebreaker_timestamp = '_fecha_registro_dt'

    def _resolver_estado_canonico(self, fila: Any, v_raw: dict, mapa_estado: dict) -> str | None:
        """Resuelve el nombre del estado fenologico (ej. Madura, Crema) de forma robusta."""
        from utils.texto import normalizar_variedad_para_match
        
        # 1. Intentar por descripcion
        desc = self.get_raw_val(fila, 'DESCRIPCIONESTADOCICLO_Raw', v_raw) or \
               self.get_raw_val(fila, 'DESCRIPCION_ESTADO_CICLO_Raw', v_raw)
        
        if desc:
            desc_norm = normalizar_variedad_para_match(desc)
            if desc_norm and desc_norm in mapa_estado:
                return mapa_estado[desc_norm]

        # 2. Intentar por ID numerico
        id_estado_raw = self.get_raw_val(fila, 'IDESTADOCICLO_Raw', v_raw) or \
                        self.get_raw_val(fila, 'ID_ESTADO_CICLO_Raw', v_raw)
        try:
            id_estado = int(float(str(id_estado_raw)))
            return MAPA_ESTADO_POR_ID.get(id_estado)
        except:
            return None

    def _construir_payload(self, df: pd.DataFrame, mapa_estado: dict) -> list[dict]:
        payload_inserts = []
        cache_cinta = {}

        for fila in df.itertuples(index=False):
            fila_dict = fila._asdict()
            id_origen = int(fila_dict['ID_Maduracion'])
            v_raw = self.parsear_raw(fila_dict.get('Valores_Raw'))

            fecha = self._validar_y_resolver_fecha(id_origen, self.get_raw_val(fila_dict, 'Fecha_Raw', v_raw), 'maduracion')
            if not fecha:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                None,
                self.get_raw_val(fila_dict, 'Modulo_Raw', v_raw),
                turno=self.get_raw_val(fila_dict, 'Turno_Raw', v_raw),
                valvula=self.get_raw_val(fila_dict, 'Valvula_Raw', v_raw)
            )
            if not resultado_geo:
                continue

            id_var = self._validar_y_resolver_variedad(id_origen, fila_dict.get('Variedad_Canonica'), self.get_raw_val(fila_dict, 'Variedad_Raw', v_raw))
            if not id_var:
                continue

            # Cinta (COLOR_Raw en Maduracion)
            color_raw = self.get_raw_val(fila_dict, 'Color_Raw', v_raw)
            if color_raw not in cache_cinta:
                cache_cinta[color_raw] = obtener_id_cinta(color_raw, self.engine)
            id_cinta = cache_cinta[color_raw]
            
            if not id_cinta:
                self.registrar_rechazo(id_origen, 'Color_Raw', color_raw, 'Cinta no reconocida o ausente')
                continue

            # Organo (ORGANO_Raw en Maduracion)
            numero_organo = self.a_int(self.get_raw_val(fila_dict, 'Organo_Raw', v_raw))
            if numero_organo is None or numero_organo < 1:
                self.registrar_rechazo(id_origen, 'Organo_Raw', numero_organo, 'ID_Organo invalido')
                continue

            # Estado Fenologico
            estado_canonico = self._resolver_estado_canonico(fila_dict, v_raw, mapa_estado)
            id_estado = obtener_id_estado_fenologico(estado_canonico, self.engine)
            if not id_estado:
                self.registrar_rechazo(id_origen, 'Estado_Raw', estado_canonico, 'Estado fenologico no reconocido')
                continue

            id_personal = self._validar_y_resolver_personal(self.get_raw_val(fila_dict, 'Evaluador_Raw', v_raw))
            fecha_reg_raw = self.get_raw_val(fila_dict, 'Fecha_Registro_Raw', v_raw) or str(fecha)
            
            self.ids_procesados.append(id_origen)
            payload_inserts.append({
                "id_origen_rastreo": id_origen,
                "ID_Personal": id_personal,
                "ID_Geografia": resultado_geo['id_geografia'],
                "_id_modulo_catalogo": resultado_geo.get('id_modulo_catalogo'),
                "ID_Tiempo": obtener_id_tiempo(fecha),
                "ID_Variedad": id_var,
                "ID_Estado_Fenologico": id_estado,
                "ID_Cinta": id_cinta,
                "ID_Organo": numero_organo,
                "Dias_Pasados_Del_Marcado": None,
                "Fecha_Evento": fecha,
                "Fecha_Sistema": pd.Timestamp.now(),
                "Estado_DQ": "OK",
                "_fecha_registro_dt": pd.to_datetime(fecha_reg_raw, errors='coerce'),
            })
        return payload_inserts


def cargar_fact_maduracion(engine: Engine) -> dict:
    proc = ProcesadorMaduracion(engine)
    
    cols_raw = [
        'Fecha_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 
        'Variedad_Raw', 'Evaluador_Raw', 'Color_Raw', 'Organo_Raw', 
        'Valores_Raw', 'Nombre_Archivo'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    mapa_estado = _cargar_mapa_estado_desde_db(engine)
    
    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        
        # Homologacion de variedad
        df, cuar_var = homologar_valor_df(df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion)
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df, mapa_estado)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, "#Temp_Fact_Maduracion")

        return proc.finalizar_proceso(contexto)


def homologar_valor_df(df, col_raw, col_dest, tabla_origen, conexion):
    # Helper local mientras mdm.homologador no tenga version batch
    from mdm.homologador import homologar_columna
    return homologar_columna(df, col_raw, col_dest, tabla_origen, conexion)
