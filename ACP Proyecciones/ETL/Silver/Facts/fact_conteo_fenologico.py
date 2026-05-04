"""
fact_conteo_fenologico.py
=========================
Carga Silver.Fact_Conteo_Fenologico desde Bronce.Conteo_Fruta.

Soporta dos layouts de origen:
1) Layout largo: Estado_Raw + Cantidad_Organos_Raw poblados.
2) Layout ancho: valores en Valores_Raw (Botones/Flores/Fases/etc.) y Punto_Raw.
"""

import re
import unicodedata
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo, parsear_fecha
from mdm.lookup import obtener_id_estado_fenologico
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    parsear_valores_raw as _parsear_valores_raw,
)


TABLA_ORIGEN = 'Bronce.Conteo_Fruta'
TABLA_DESTINO = 'Silver.Fact_Conteo_Fenologico'

MAPA_ESTADOS_WIDE = {
    'Botones_Florales_Raw': 'Boton Floral',
    'Flores_Raw': 'Flor',
    'Bayas_Pequenas_Raw': 'Pequena',
    'Bayas_Grandes_Verdes_Raw': 'Verde',
    'Fase1_Raw': 'Inicio F1',
    'Fase2_Raw': 'Inicio F2',
    'Bayas_Cremas_Raw': 'Crema',
    'Bayas_Maduras_Raw': 'Madura',
    'Bayas_Cosechables_Raw': 'Cosechable',
}

SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Conteo_Fenologico (
        ID_Geografia, ID_Tiempo, ID_Variedad,
        ID_Personal, ID_Estado_Fenologico,
        Cantidad_Organos,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad,
        :id_personal, :id_estado,
        :cantidad,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _normalizar_tipo_evaluacion(valor) -> str:
    texto = str(valor or '').strip()
    if not texto:
        return ''
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.casefold()
    texto = re.sub(r'[^a-z0-9]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _es_evaluacion_compatible_con_conteo(valor) -> bool:
    """
    Acepta filas del layout real de conteo de flores, incluyendo variantes
    operativas observadas en el Excel de campo.

    Casos validados:
    - CONTEO DE FLORES
    - ENSAYO DE CONTEO
    - PODA GENERAL

    Si la fuente no trae evaluacion, conserva compatibilidad hacia atras.
    """
    normalizado = _normalizar_tipo_evaluacion(valor)
    if not normalizado:
        return True
    if 'conteo' in normalizado or 'fenolog' in normalizado:
        return True
    if normalizado == 'poda general':
        return True
    return False


def _leer_bronce(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Conteo_Fruta,
                Fecha_Raw,
                Fundo_Raw,
                Sector_Raw,
                Modulo_Raw,
                Turno_Raw,
                Valvula_Raw,
                Variedad_Raw,
                Evaluador_Raw,
                Color_Cinta_Raw,
                Estado_Raw,
                Cantidad_Organos_Raw,
                Tipo_Evaluacion_Raw,
                Valores_Raw,
                Fecha_Registro_Raw
            FROM {TABLA_ORIGEN}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _normalizar_cantidad(valor) -> int:
    try:
        return int(float(str(valor)))
    except (ValueError, TypeError):
        return 0


def _extraer_estados_desde_fila(fila: pd.Series) -> list[tuple[str, int]]:
    estado_raw = fila.get('Estado_Raw')
    cantidad_raw = fila.get('Cantidad_Organos_Raw')

    if estado_raw is not None and str(estado_raw).strip() and cantidad_raw is not None and str(cantidad_raw).strip():
        return [(str(estado_raw).strip(), _normalizar_cantidad(cantidad_raw))]

    valores = _parsear_valores_raw(fila.get('Valores_Raw'))
    estados: list[tuple[str, int]] = []
    for clave_wide, nombre_estado in MAPA_ESTADOS_WIDE.items():
        if clave_wide not in valores:
            continue
        cantidad = _normalizar_cantidad(valores.get(clave_wide))
        estados.append((nombre_estado, cantidad))
    return estados


class ProcesadorConteoFenologico(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Conteo_Fruta')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Estado_Fenologico', 'Punto']
        self.columna_tiebreaker_timestamp = 'Fecha_Registro'

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        payload = []
        for _, fila in df.iterrows():
            id_origen = int(fila['ID_Conteo_Fruta'])
            tipo_evaluacion_raw = fila.get('Tipo_Evaluacion_Raw')

            if not _es_evaluacion_compatible_con_conteo(tipo_evaluacion_raw):
                self.registrar_rechazo(id_origen, 'Tipo_Evaluacion_Raw', tipo_evaluacion_raw, 'Evaluacion no compatible con Fact_Conteo_Fenologico')
                continue

            fecha = self._validar_y_resolver_fecha(id_origen, fila.get('Fecha_Raw'), 'conteo_fenologico')
            if fecha is None:
                continue

            resultado_geo = self._validar_y_resolver_geografia(
                id_origen,
                fila.get('Fundo_Raw'),
                fila.get('Modulo_Raw'),
                turno=fila.get('Turno_Raw'),
                valvula=fila.get('Valvula_Raw'),
            )
            if resultado_geo is None:
                continue

            id_var = self._validar_y_resolver_variedad(id_origen, fila.get('Variedad_Canonica'), fila.get('Variedad_Raw'))
            if id_var is None:
                continue

            id_personal = self._validar_y_resolver_personal(fila.get('Evaluador_Raw'))

            estados_cantidades = _extraer_estados_desde_fila(fila)
            if not estados_cantidades:
                self.registrar_rechazo(id_origen, 'Valores_Raw', fila.get('Valores_Raw'), 'No se encontraron estados fenologicos/cantidades en fila')
                continue

            filas_expandidas = 0
            for estado_raw, cantidad in estados_cantidades:
                id_estado = obtener_id_estado_fenologico(estado_raw, self.engine)
                if not id_estado:
                    self.resumen['cuarentena'].append({
                        'columna': 'Estado_Raw',
                        'valor': estado_raw,
                        'motivo': 'Estado fenologico no reconocido',
                        'severidad': 'ALTO',
                        'id_registro_origen': id_origen,
                    })
                    continue

                # Extracción robusta del Punto (limpiando espacios)
                valores_dict = _parsear_valores_raw(fila.get('Valores_Raw'))
                punto_val = str(valores_dict.get('Punto_Raw') or valores_dict.get('Punto') or '0').strip()

                fecha_registro = parsear_fecha(fila.get('Fecha_Registro_Raw'))

                payload.append({
                    'ID_Geografia':        resultado_geo['id_geografia'],
                    '_id_modulo_catalogo': resultado_geo.get('id_modulo_catalogo'),
                    'ID_Tiempo':           obtener_id_tiempo(fecha),
                    'ID_Variedad':         id_var,
                    'ID_Personal':         id_personal,
                    'ID_Estado_Fenologico': id_estado,
                    'Cantidad_Organos':    cantidad,
                    'Punto':               punto_val,
                    'Fecha_Evento':        fecha,
                    'Fecha_Registro':      fecha_registro,
                    'Estado_DQ':           'OK',
                    'id_origen_rastreo':   id_origen,
                })
                filas_expandidas += 1

            if filas_expandidas > 0:
                self.ids_procesados.append(id_origen)
            else:
                self.registrar_rechazo(id_origen, 'Estado_Raw', None, 'Ningún estado fenologico reconocido en la fila')

        return payload


def cargar_fact_conteo_fenologico(engine: Engine) -> dict:
    proc = ProcesadorConteoFenologico(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Sector_Raw', 'Modulo_Raw', 'Turno_Raw',
        'Valvula_Raw', 'Variedad_Raw', 'Evaluador_Raw', 'Color_Cinta_Raw',
        'Estado_Raw', 'Cantidad_Organos_Raw', 'Tipo_Evaluacion_Raw',
        'Valores_Raw', 'Fecha_Registro_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuarentenas_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Conteo_Fruta',
        )
        proc.resumen['cuarentena'].extend(cuarentenas_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_ConteoFenologico')

        return proc.finalizar_proceso(contexto)
