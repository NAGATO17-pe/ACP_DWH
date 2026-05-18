"""
cargador.py
===========
Lee archivos Excel de campo e inserta en Bronce como NVARCHAR raw.
Aplica validacion de layout critico cuando la operacion lo exige.
"""

import json
import shutil
import tempfile
import re
import unicodedata
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from bronce.rutas import (
    CARPETA_PROCESADOS,
    CARPETA_RECHAZADOS,
    listar_carpetas_con_archivos,
)
from config.conexion import obtener_engine
from auditoria.log import registrar_inicio, registrar_fin


_CACHE_COLUMNAS_BRONCE: dict[str, set[str]] = {}


_FIRMAS_LAYOUT_CRITICO: dict[str, dict[str, Any]] = {
    'Bronce.Evaluacion_Vegetativa': {
        'ruta_canonica': 'evaluacion_vegetativa',
        'columnas_obligatorias': {
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
        'columnas_incompatibles': {
            'Altura_Raw',
            'Tallos_basales_Raw',
            'Tallos_basales_nuevos_Raw',
            'Brotes_Generales_1_Raw',
            'Brotes_Generales_2_Raw',
            'Brotes_Generales_3_Raw',
            'Brotes_Generales_4_Raw',
            'Brotes_Productivos_Totales_Raw',
            'Brotes_Productivos_1_Raw',
            'Brotes_Productivos_2_Raw',
            'Brotes_Productivos_3_Raw',
            'Brotes_Productivos_4_Raw',
            'Diametro_brote1_Raw',
            'Diametro_brote2_Raw',
        },
        'motivo': (
            'El layout recibido no corresponde al fact actual de Evaluacion Vegetativa. '
            'Faltan columnas de plantas y aparecen metricas de brotes/altura/diametro.'
        ),
    },
    'Bronce.Fisiologia': {
        'ruta_canonica': 'fisiologia',
        'columnas_obligatorias': {
            'Fecha_Raw',
            'Modulo_Raw',
            'Variedad_Raw',
            'Tercio_Raw',
            'Hinchadas_Raw',
            'Productivas_Raw',
            'Total_Org_Raw',
        },
        'columnas_geo_alternativas': (
            {'Fundo_Raw'},
            {'Turno_Raw', 'Valvula_Raw'},
        ),
        'columnas_brote_alternativas': (
            {'Brote_Raw'},
            {'BrotesProd_Raw'},
        ),
        'columnas_incompatibles': {
            'DNI_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
            'Altura_Raw',
            'Tallos_basales_Raw',
            'Tallos_basales_nuevos_Raw',
            'Brotes_Generales_1_Raw',
            'Brotes_Generales_2_Raw',
            'Brotes_Generales_3_Raw',
            'Brotes_Generales_4_Raw',
            'Brotes_Productivos_Totales_Raw',
            'Brotes_Productivos_1_Raw',
            'Brotes_Productivos_2_Raw',
            'Brotes_Productivos_3_Raw',
            'Brotes_Productivos_4_Raw',
            'Diametro_brote1_Raw',
            'Diametro_brote2_Raw',
        },
        'motivo': (
            'El layout recibido no corresponde al fact actual de Fisiologia. '
            'Se detectaron columnas incompatibles o faltan componentes minimos de geografia/biologia para el fact.'
        ),
        'rechazar_por_faltantes': True,
    },
}

_FIRMAS_RUTA_SUGERIDA: dict[str, dict[str, Any]] = {
    'peladas': {
        'tabla_destino': 'Bronce.Peladas',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Tipo_Evaluacion_Raw',
            'Punto_Raw',
            'Variedad_Raw',
            'BotonesFlorales_Raw',
            'Flores_Raw',
            'BayasPequenas_Raw',
            'BayasGrandes_Raw',
            'Fase1_Raw',
            'Fase2_Raw',
            'BayasCremas_Raw',
            'BayasMaduras_Raw',
            'BayasCosechables_Raw',
            'PlantasProductivas_Raw',
            'PlantasNoProductivas_Raw',
            'Muestras_Raw',
        },
    },
    'induccion_floral': {
        'tabla_destino': 'Bronce.Induccion_Floral',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Tipo_Evaluacion_Raw',
            'PlantasPorCama_Raw',
            'PlantasConInduccion_Raw',
            'BrotesConInduccion_Raw',
            'BrotesTotales_Raw',
            'BrotesConFlor_Raw',
        },
    },
    'tasa_crecimiento_brotes': {
        'tabla_destino': 'Bronce.Tasa_Crecimiento_Brotes',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Condicion_Raw',
            'Estado_Vegetativo_Raw',
            'Tipo_Tallo_Raw',
            'Ensayo_Raw',
            'Medida_Raw',
            'Fecha_Poda_Aux_Raw',
            'Campana_Raw',
            'Tipo_Evaluacion_Raw',
        },
    },
    'evaluacion_vegetativa': {
        'tabla_destino': 'Bronce.Evaluacion_Vegetativa',
        'columnas_clave': {
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
    },
    'evaluacion_pesos': {
        'tabla_destino': 'Bronce.Evaluacion_Pesos',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Variedad_Raw',
            'BayasPequenas_Raw',
            'PesoBayasPequenas_Raw',
            'Cosechables_Raw',
            'PesoCosechables_Raw',
        },
    },
    'evaluacion_calidad_poda': {
        'tabla_destino': 'Bronce.Evaluacion_Calidad_Poda',
        'columnas_clave': {
            'Fecha_Raw',
            'Fundo_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Variedad_Raw',
            'Tipo_Evaluacion_Raw',
            'TallosPlanta_Raw',
            'LongitudTallo_Raw',
            'DiametroTallo_Raw',
            'RamillaPlanta_Raw',
            'ToconesPlanta_Raw',
            'CortesDefectuosos_Raw',
            'AlturaPoda_Raw',
        },
    },
}


# Mapeo de nombres de columnas comunes del Excel a nombres estándar del ETL.
# Se aplica DESPUÉS de reemplazar espacios por _ y eliminar acentos.
# Clave : nombre ya sin acentos/espacios (sin _Raw)
# Valor : nombre esperado por los scripts Silver (sin _Raw)
_ALIAS_COLUMNAS: dict[str, str] = {
    # Fechas
    'Fecha_de_evaluacion':        'Fecha',
    'Fecha_de_evaluaci_n':        'Fecha',
    'Fecha_evaluacion':           'Fecha',
    'Fecha':                      'Fecha',
    'fecha':                      'Fecha',
    'FECHA':                      'Fecha',
    'FECHAEVALUACION':            'Fecha',
    # Fecha de subida
    'Fecha_de_subida':            'Fecha_Subida',
    'FechaSubida':                'Fecha_Subida',
    'FECHASUBIDA':                'Fecha_Subida',
    'FECHAREGISTRO':              'Fecha_Registro',
    # Timestamp del evento de campo en "Conteo frutos" (columna "Registro")
    'Registro':                   'Fecha_Registro_Raw',
    'REGISTRO':                   'Fecha_Registro_Raw',
    'registro':                   'Fecha_Registro_Raw',
    # Fundo
    'Fundo':                      'Fundo',
    'fundo':                      'Fundo',
    # Modulo
    'Modulo':                     'Modulo',
    'modulo':                     'Modulo',
    'MODULO':                     'Modulo',
    # Valvula
    'Valvula':                    'Valvula',
    'valvula':                    'Valvula',
    'VALVULA':                    'Valvula',
    'NROVALVULA':                 'Valvula',
    'Cama':                       'Cama',
    'N_cama':                     'Cama',
    'N_de_cama':                  'Cama',
    # Turno
    'Turno':                      'Turno',
    'turno':                      'Turno',
    'TURNO':                      'Turno',
    # Variedad
    'Variedad':                   'Variedad',
    'variedad':                   'Variedad',
    'VARIEDAD':                   'Variedad',
    # Evaluacion
    'Evaluacion':                 'Evaluacion',
    'evaluacion':                 'Evaluacion',
    'Tipo_de_Evaluacion':         'Tipo_Evaluacion',
    # DNI / Personal
    'DNI':                        'DNI',
    'dni':                        'DNI',
    'USUARIO':                    'Evaluador',
    'USUARIOEVALUADOR':           'Evaluador',
    'EVALUADOR':                  'Evaluador',
    'Nombres':                    'Nombres',
    'Nombre':                     'Nombres',
    'Evaluador':                  'Evaluador',
    # Hora
    'Hora':                       'Hora',
    'HORA':                       'Hora',
    # Sector
    'Sector':                     'Sector',
    'sector':                     'Sector',
    'SECTOR':                     'Sector',
    # Clima
    'T_Max':                      'TempMax',
    'T_Min':                      'TempMin',
    'HUMEDAD_RELATIVA':           'Humedad',
    'RADIACION_SOLAR':            'Radiacion',
    'DVP_Real':                   'VPD',
    'DVP_PROMETEO':               'VPD',
    # Tareos
    'DNIRESPONSABLE':             'DNIResponsable',
    'DNI_RESPONSABLE':            'DNIResponsable',
    'IDPERSONALGENERAL':          'IDPersonalGeneral',
    'ID_PERSONAL_GENERAL':        'IDPersonalGeneral',
    'IDPLANILLA':                 'IDPlanilla',
    'ID_PLANILLA':                'IDPlanilla',
    'IDACTIVIDAD':                'IDActividad',
    'ID_ACTIVIDAD':               'IDActividad',
    'ACTIVIDAD':                  'Actividad',
    'IDLABOR':                    'IDLabor',
    'ID_LABOR':                   'IDLabor',
    'LABOR':                      'Labor',
    'IDTURNO':                    'Turno',
    'ID_TURNO':                   'Turno',
    'HORAS':                      'HorasTrabajadas',
    'HORASTRABAJADAS':            'HorasTrabajadas',
    'AREA':                       'Area',
    # Pesos bayas (Reporte_evaluacion_peso.xlsx) - post normalizacion de acentos
    'Bayas_pequenas':             'BayasPequenas',
    'Peso_bayas_pequenas':        'PesoBayasPequenas',
    'Peso_bayas_pequenas1':       'PesoBayasPequenas2',
    'Peso_bayas_pequenas2':       'PesoBayasPequenas2',
    'Bayas_grandes':              'BayasGrandes',
    'Peso_bayas_grandes':         'PesoBayasGrandes',
    'Bayas_fase_1':               'BayasFase1',
    'Peso_bayas_fase_1':          'PesoBayasFase1',
    'Bayas_fase_2':               'BayasFase2',
    'Peso_bayas_fase_2':          'PesoBayasFase2',
    'Cremas':                     'Cremas',
    'Peso_cremas':                'PesoCremas',
    'Maduras':                    'Maduras',
    'Peso_maduras':               'PesoMaduras',
    'Cosechables':                'Cosechables',
    'Peso_cosechables':           'PesoCosechables',
    'PesoBaya':                   'PesoBaya',
    'CantMuestra':                'CantMuestra',
    # Peladas / Conteos
    'Botones_Florales':           'BotonesFlorales',
    'Flores':                     'Flores',
    'Bayas_Pequenas':             'BayasPequenas',
    'Bayas_Grandes_Verdes':       'BayasGrandes',
    'Bayas_Cremas':               'BayasCremas',
    'Bayas_Maduras':              'BayasMaduras',
    'Bayas_Cosechables':          'BayasCosechables',
    'Plantas_Productivas':        'PlantasProductivas',
    'Plantas_No_Productivas':     'PlantasNoProductivas',
    'Muestra':                    'Muestras',
    'Yemas_Activadas':            'YemasActivadas',
    'TOTAL_ORGANOS':              'Total_Organos',
    'Total_plantas':              'TotalPlantas',
    'Plantas_Proy':               'PlantasProy',
    # Fisiologia
    'TERCIO':                     'Tercio',
    'HINCHADAS':                  'Hinchadas',
    'PRODUCTIVAS':                'Productivas',
    'TOTAL_ORG':                  'Total_Org',
    'BROTE':                      'Brote',
    'BROTESPROD':                 'BrotesProd',
    'BROTESVEG':                  'BrotesVeg',
}

_ALIAS_COLUMNAS_CASEFOLD: dict[str, str] = {
    str(clave).casefold(): valor
    for clave, valor in _ALIAS_COLUMNAS.items()
}


def _alias(col_snake: str) -> str:
    """Retorna el alias estandar si existe, o la misma col_snake."""
    if col_snake in _ALIAS_COLUMNAS:
        return _ALIAS_COLUMNAS[col_snake]
    return _ALIAS_COLUMNAS_CASEFOLD.get(str(col_snake).casefold(), col_snake)


def _normalizar_nombre_columna_base(columna) -> str:
    """
    Canoniza encabezados reales del Excel a una forma estable:
    - quita tildes y variantes Unicode
    - elimina simbolos como °, º, #, /, (), .
    - colapsa separadores repetidos
    - normaliza sufijos numericos tipo ".1" -> "1"
    """
    texto = str(columna).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace('°', '').replace('º', '').replace('#', 'N')
    texto = re.sub(r'[^0-9A-Za-z]+', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    texto = re.sub(r'_(\d+)$', r'\1', texto)
    return texto


def _consolidar_columnas_duplicadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Si varios encabezados del Excel terminan en el mismo nombre normalizado,
    conserva una sola columna usando el primer valor no nulo por fila.
    """
    nombres_ordenados = list(dict.fromkeys(str(col) for col in df.columns))
    if len(nombres_ordenados) == len(df.columns):
        return df

    df_consolidado = pd.DataFrame(index=df.index)
    for nombre in nombres_ordenados:
        bloque = df.loc[:, df.columns == nombre]
        if isinstance(bloque, pd.Series):
            df_consolidado[nombre] = bloque
            continue

        bloque = bloque.replace(r'^\s*$', np.nan, regex=True)
        if bloque.shape[1] == 1:
            df_consolidado[nombre] = bloque.iloc[:, 0]
        else:
            df_consolidado[nombre] = bloque.bfill(axis=1).iloc[:, 0]

    return df_consolidado


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas del Excel:
    - Quita espacios / caracteres especiales
    - Aplica alias estándares (Fecha de evaluación → Fecha_Raw)
    - Agrega sufijo _Raw si no lo tiene
    """
    columnas_nuevas = {}
    for col in df.columns:
        col_snake = _normalizar_nombre_columna_base(col)
        col_snake = _alias(col_snake)
        if not col_snake.endswith('_Raw'):
            col_snake = f'{col_snake}_Raw'
        columnas_nuevas[col] = col_snake
    df = df.rename(columns=columnas_nuevas)
    return _consolidar_columnas_duplicadas(df)


def castear_todo_a_texto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte todas las columnas a string (vectorizado).
    None y NaN se convierten a None (NULL en SQL).
    Bronce nunca tipifica — todo es NVARCHAR.
    """
    for col in df.columns:
        mask_nulo = df[col].isna()
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
        )
        df[col] = np.where(mask_nulo, None, df[col])
    return df


def agregar_columnas_sistema(df: pd.DataFrame,
                              nombre_archivo: str) -> pd.DataFrame:
    """
    Agrega columnas de infraestructura que no vienen del Excel:
    - Fecha_Sistema  : timestamp de carga
    - Nombre_Archivo : nombre del archivo fuente
    - Estado_Carga   : estado inicial
    """
    ahora = datetime.now()
    df['Fecha_Sistema'] = ahora
    df['Nombre_Archivo'] = nombre_archivo
    df['Estado_Carga'] = 'CARGADO'
    return df


def insertar_en_bronce(df: pd.DataFrame,
                        tabla: str,
                        engine) -> int:
    """
    Inserta el DataFrame en la tabla Bronce indicada.
    Retorna el número de filas insertadas.

    Usa cursor.fast_executemany directo en vez de pandas.to_sql() para
    garantizar que fast_executemany se aplique efectivamente: to_sql()
    usa su propia ruta de ejecución interna que puede ignorar el flag
    del engine según la versión de pandas/SQLAlchemy.
    """
    if df.empty:
        return 0

    esquema, nombre_tabla = tabla.split('.')
    columnas = list(df.columns)
    placeholders = ', '.join(['?' for _ in columnas])
    cols_quoted   = ', '.join([f'[{c}]' for c in columnas])
    sql = f'INSERT INTO [{esquema}].[{nombre_tabla}] ({cols_quoted}) VALUES ({placeholders})'

    # Convertir a lista de tuplas; sustituir NaN/NaT por None para que
    # pyodbc los envíe como NULL sin lanzar "Invalid parameter type"
    datos: list[tuple] = [
        tuple(None if (v != v or v is None) else v for v in fila)
        for fila in df.itertuples(index=False, name=None)
    ]

    with engine.begin() as conn:
        cursor = conn.connection.cursor()
        cursor.fast_executemany = True
        cursor.executemany(sql, datos)
        cursor.close()

    return len(df)


def _crear_copia_temporal_excel(ruta_archivo: Path) -> Path:
    sufijo = f'_{ruta_archivo.name}'
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as temporal:
        ruta_temporal = Path(temporal.name)
    shutil.copy2(str(ruta_archivo), str(ruta_temporal))
    return ruta_temporal


def _ruta_marca_archivo(ruta_archivo: Path) -> Path:
    return ruta_archivo.with_name(f'{ruta_archivo.name}.procesado.json')


def _marcar_archivo_local(ruta_archivo: Path,
                          estado: str,
                          *,
                          destino: Path | None = None,
                          codigo_rechazo: str | None = None) -> Path:
    stat_archivo = ruta_archivo.stat()
    payload = {
        'archivo': ruta_archivo.name,
        'estado': str(estado).upper(),
        'fecha_marca': datetime.now().isoformat(timespec='seconds'),
        'tamano_bytes': int(stat_archivo.st_size),
        'mtime_ns': int(stat_archivo.st_mtime_ns),
    }
    if destino is not None:
        payload['destino'] = str(destino)
    if codigo_rechazo:
        payload['codigo_rechazo'] = str(codigo_rechazo)

    ruta_marca = _ruta_marca_archivo(ruta_archivo)
    ruta_marca.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding='utf-8',
    )
    return ruta_marca


def _archivar_o_marcar(ruta_archivo: Path,
                       destino: Path,
                       *,
                       estado_marca: str,
                       codigo_rechazo: str | None = None) -> tuple[Path, bool]:
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(ruta_archivo), str(destino))
        return destino, False
    except PermissionError:
        shutil.copy2(str(ruta_archivo), str(destino))
        _marcar_archivo_local(
            ruta_archivo,
            estado_marca,
            destino=destino,
            codigo_rechazo=codigo_rechazo,
        )
        return destino, True


def archivar_archivo(ruta_archivo: Path, nombre_carpeta: str) -> tuple[Path, bool]:
    """
    Mueve el archivo procesado a data/procesados/nombre_carpeta/
    con timestamp en el nombre para no sobrescribir.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_nuevo = f'{ruta_archivo.stem}_{timestamp}{ruta_archivo.suffix}'
    destino = CARPETA_PROCESADOS / nombre_carpeta / nombre_nuevo
    return _archivar_o_marcar(
        ruta_archivo,
        destino,
        estado_marca='PROCESADO',
    )


def archivar_archivo_rechazado(ruta_archivo: Path,
                               nombre_carpeta: str,
                               codigo_rechazo: str) -> tuple[Path, bool]:
    """
    Mueve el archivo rechazado a data/rechazados/nombre_carpeta/
    preservando trazabilidad del motivo en el nombre.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sufijo = str(codigo_rechazo or 'RECHAZADO').strip().replace(' ', '_')
    nombre_nuevo = f'{ruta_archivo.stem}_{sufijo}_{timestamp}{ruta_archivo.suffix}'
    destino = CARPETA_RECHAZADOS / nombre_carpeta / nombre_nuevo
    return _archivar_o_marcar(
        ruta_archivo,
        destino,
        estado_marca='RECHAZADO',
        codigo_rechazo=codigo_rechazo,
    )


def _obtener_columnas_bronce(tabla_destino: str, engine) -> set[str]:
    """
    Devuelve columnas fisicas de la tabla Bronce destino.
    Usa cache en memoria para evitar query repetida en cada archivo.
    """
    if tabla_destino in _CACHE_COLUMNAS_BRONCE:
        return _CACHE_COLUMNAS_BRONCE[tabla_destino]

    esquema, tabla = tabla_destino.split('.')
    consulta = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :esquema
          AND TABLE_NAME = :tabla
    """)
    with engine.connect() as conexion:
        filas = conexion.execute(
            consulta,
            {'esquema': esquema, 'tabla': tabla},
        ).fetchall()

    columnas = {str(fila[0]) for fila in filas}
    _CACHE_COLUMNAS_BRONCE[tabla_destino] = columnas
    return columnas


def _columnas_normalizadas_excel(ruta_archivo: Path, header_idx: int) -> list[str]:
    """
    Lee solo encabezados del Excel y devuelve nombres normalizados (con _Raw).
    """
    df = pd.read_excel(
        str(ruta_archivo),
        header=header_idx,
        dtype=str,
        nrows=0,
        engine='openpyxl',
    )
    df = normalizar_columnas(df)
    return [str(col) for col in df.columns]


def _extraer_sector_climatico_desde_archivo(ruta_archivo: Path) -> str | None:
    coincidencia = re.search(r'\b([A-Z]\d{2})\b', ruta_archivo.stem.upper())
    return coincidencia.group(1) if coincidencia else None


def _leer_excel_especial(
    ruta_archivo: Path,
    *,
    header_idx: int,
    sheet_name: str | int | None = 0,
) -> pd.DataFrame:
    """
    Lee un Excel con layout conocido, elimina filas/columnas totalmente vacias
    y normaliza encabezados a la convención _Raw del ETL.
    """
    df = pd.read_excel(
        str(ruta_archivo),
        sheet_name=sheet_name,
        header=header_idx,
        dtype=str,
        engine='openpyxl',
    )
    if df.empty:
        return df

    df = df.dropna(how='all')
    df = df.loc[:, ~df.columns.isna()]
    return normalizar_columnas(df)


def _leer_excel_clima_bd(ruta_archivo: Path) -> pd.DataFrame:
    """
    Lee el layout analitico de clima desde la hoja BD.
    El header real esta en la fila 3 del Excel (header=2).
    """
    df = _leer_excel_especial(ruta_archivo, sheet_name='BD', header_idx=2)
    if df.empty:
        return df

    sector = _extraer_sector_climatico_desde_archivo(ruta_archivo)
    if sector:
        df['Sector_Raw'] = sector

    return df


def _leer_excel_peladas_bd(ruta_archivo: Path) -> pd.DataFrame:
    """
    Lee el layout formal de Peladas.
    Prioriza la hoja BD_LT, que representa el subconjunto operativo de Peladas.
    Si no existe, intenta hoja BD y filtra solo registros con Tipo_Evaluacion = PELADAS.
    """
    with pd.ExcelFile(str(ruta_archivo), engine='openpyxl') as libro:
        hojas = set(libro.sheet_names)

        if 'BD_LT' in hojas:
            return _leer_excel_especial(ruta_archivo, sheet_name='BD_LT', header_idx=0)

        if 'BD' in hojas:
            df = _leer_excel_especial(ruta_archivo, sheet_name='BD', header_idx=0)
            if df.empty:
                return df

            if 'Tipo_Evaluacion_Raw' in df.columns:
                mascara_peladas = (
                    df['Tipo_Evaluacion_Raw']
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .eq('PELADAS')
                )
                df = df[mascara_peladas].copy()

            return df

    raise ValueError(
        'Layout de Peladas sin hoja compatible. '
        'Se esperaba BD_LT o BD.'
    )


def _proyectar_dataframe_peladas_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta el layout real de Peladas a las columnas fisicas esperadas en Bronce.
    Conserva metadatos adicionales en Valores_Raw para no perder trazabilidad.
    """
    df = _leer_excel_peladas_bd(ruta_archivo)
    if df.empty:
        return df

    columnas_salida = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'Fundo_Raw': _serie_o_nulos(df, 'Fundo_Raw'),
        'DNI_Raw': _serie_o_nulos(df, 'DNI_Raw'),
        'Nombres_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Evaluador_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Modulo_Raw': _serie_o_nulos(df, 'Modulo_Raw'),
        'Turno_Raw': _serie_o_nulos(df, 'Turno_Raw'),
        'Valvula_Raw': _serie_o_nulos(df, 'Valvula_Raw'),
        'Tipo_Evaluacion_Raw': _serie_o_nulos(df, 'Tipo_Evaluacion_Raw'),
        'Punto_Raw': _serie_o_nulos(df, 'Punto_Raw'),
        'Variedad_Raw': _serie_o_nulos(df, 'Variedad_Raw'),
        'Muestras_Raw': _serie_o_nulos(df, 'Muestras_Raw'),
        'BotonesFlorales_Raw': _serie_o_nulos(df, 'BotonesFlorales_Raw'),
        'Flores_Raw': _serie_o_nulos(df, 'Flores_Raw'),
        'BayasPequenas_Raw': _serie_o_nulos(df, 'BayasPequenas_Raw'),
        'BayasGrandes_Raw': _serie_o_nulos(df, 'BayasGrandes_Raw'),
        'Fase1_Raw': _serie_o_nulos(df, 'Fase1_Raw'),
        'Fase2_Raw': _serie_o_nulos(df, 'Fase2_Raw'),
        'BayasCremas_Raw': _serie_o_nulos(df, 'BayasCremas_Raw'),
        'BayasMaduras_Raw': _serie_o_nulos(df, 'BayasMaduras_Raw'),
        'BayasCosechables_Raw': _serie_o_nulos(df, 'BayasCosechables_Raw'),
        'PlantasProductivas_Raw': _serie_o_nulos(df, 'PlantasProductivas_Raw'),
        'PlantasNoProductivas_Raw': _serie_o_nulos(df, 'PlantasNoProductivas_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = {
        'Fecha_Raw',
        'Fundo_Raw',
        'DNI_Raw',
        'Nombres_Raw',
        'Modulo_Raw',
        'Turno_Raw',
        'Valvula_Raw',
        'Tipo_Evaluacion_Raw',
        'Punto_Raw',
        'Variedad_Raw',
        'Muestras_Raw',
        'BotonesFlorales_Raw',
        'Flores_Raw',
        'BayasPequenas_Raw',
        'BayasGrandes_Raw',
        'Fase1_Raw',
        'Fase2_Raw',
        'BayasCremas_Raw',
        'BayasMaduras_Raw',
        'BayasCosechables_Raw',
        'PlantasProductivas_Raw',
        'PlantasNoProductivas_Raw',
    }
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _serie_o_nulos(df: pd.DataFrame, columna: str) -> pd.Series:
    if columna in df.columns:
        return df[columna]
    return pd.Series([None] * len(df), index=df.index)


def _proyectar_dataframe_clima_bronce(
    ruta_archivo: Path,
    tabla_destino: str,
) -> pd.DataFrame:
    """
    Proyecta el layout BD de clima a las columnas fisicas esperadas en Bronce.
    No depende del alineador generico porque el libro trae muchas metricas analiticas.
    """
    df = _leer_excel_clima_bd(ruta_archivo)
    if df.empty:
        return df

    columnas_base = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'Sector_Raw': _serie_o_nulos(df, 'Sector_Raw'),
        'TempMax_Raw': _serie_o_nulos(df, 'TempMax_Raw'),
        'TempMin_Raw': _serie_o_nulos(df, 'TempMin_Raw'),
        'Humedad_Raw': _serie_o_nulos(df, 'Humedad_Raw'),
    }

    if tabla_destino == 'Bronce.Reporte_Clima':
        columnas_base.update({
            'Hora_Raw': _serie_o_nulos(df, 'Hora_Raw'),
            'Precipitacion_Raw': _serie_o_nulos(df, 'Precipitacion_Raw'),
        })
    elif tabla_destino == 'Bronce.Variables_Meteorologicas':
        columnas_base.update({
            'VPD_Raw': _serie_o_nulos(df, 'VPD_Raw'),
            'Radiacion_Raw': _serie_o_nulos(df, 'Radiacion_Raw'),
        })

    df_salida = pd.DataFrame(columnas_base, index=df.index)

    columnas_usadas = set(df_salida.columns)
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _proyectar_dataframe_induccion_floral_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta el layout real de Induccion Floral a columnas fisicas de Bronce.
    El archivo trae titulo en fila 1 y encabezado real en fila 2.
    """
    df = _leer_excel_especial(ruta_archivo, header_idx=1)
    if df.empty:
        return df

    columnas_salida = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'DNI_Raw': _serie_o_nulos(df, 'DNI_Raw'),
        'Fecha_Subida_Raw': _serie_o_nulos(df, 'Fecha_Subida_Raw'),
        'Nombres_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Evaluador_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Consumidor_Raw': _serie_o_nulos(df, 'Consumidor_Raw'),
        'Modulo_Raw': _serie_o_nulos(df, 'Modulo_Raw'),
        'Turno_Raw': _serie_o_nulos(df, 'Turno_Raw'),
        'Valvula_Raw': _serie_o_nulos(df, 'Valvula_Raw'),
        'Tipo_Evaluacion_Raw': _serie_o_nulos(df, 'Evaluacion_Raw'),
        'Cama_Raw': _serie_o_nulos(df, 'Cama_Raw'),
        'Descripcion_Raw': _serie_o_nulos(df, 'Descripcion_Raw'),
        'Variedad_Raw': _serie_o_nulos(df, 'Descripcion_Raw'),
        'PlantasPorCama_Raw': _serie_o_nulos(df, 'Plantas_por_Cama_Raw'),
        'PlantasConInduccion_Raw': _serie_o_nulos(df, 'Plantas_con_Induccion_Raw'),
        'BrotesConInduccion_Raw': _serie_o_nulos(df, 'Brotes_con_Induccion_Raw'),
        'BrotesTotales_Raw': _serie_o_nulos(df, 'Brotes_Totales_Raw'),
        'BrotesConFlor_Raw': _serie_o_nulos(df, 'Brotes_con_Flor_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = {
        'Fecha_Raw',
        'DNI_Raw',
        'Fecha_Subida_Raw',
        'Nombres_Raw',
        'Consumidor_Raw',
        'Modulo_Raw',
        'Turno_Raw',
        'Valvula_Raw',
        'Evaluacion_Raw',
        'Cama_Raw',
        'Descripcion_Raw',
        'Plantas_por_Cama_Raw',
        'Plantas_con_Induccion_Raw',
        'Brotes_con_Induccion_Raw',
        'Brotes_Totales_Raw',
        'Brotes_con_Flor_Raw',
    }
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _proyectar_dataframe_tasa_crecimiento_brotes_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta Tasa de Crecimiento desde la hoja BD_General.
    Solo esta hoja representa el grano raw util para ETL.
    """
    df = _leer_excel_especial(ruta_archivo, sheet_name='BD_General', header_idx=1)
    if df.empty:
        return df

    columnas_salida = {
        'Codigo_Origen_Raw': _serie_o_nulos(df, 'Unnamed0_Raw'),
        'Semana_Raw': _serie_o_nulos(df, 'Semana_Raw'),
        'Dia_Raw': _serie_o_nulos(df, 'Dia_Raw'),
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'DNI_Raw': _serie_o_nulos(df, 'DNI_Raw'),
        'Evaluador_Raw': _serie_o_nulos(df, 'EVALUADOR_A_Raw'),
        'Modulo_Raw': _serie_o_nulos(df, 'Mod_Raw'),
        'Turno_Raw': _serie_o_nulos(df, 'Tur_Raw'),
        'Valvula_Raw': _serie_o_nulos(df, 'Val_Raw'),
        'Condicion_Raw': _serie_o_nulos(df, 'Condicion_Raw'),
        'Estado_Vegetativo_Raw': _serie_o_nulos(df, 'Estado_Vegetativo_Raw'),
        'Variedad_Raw': _serie_o_nulos(df, 'Variedad_Raw'),
        'Cama_Raw': _serie_o_nulos(df, 'Cama_Raw'),
        'Tipo_Tallo_Raw': _serie_o_nulos(df, 'Tipo_de_Tallo_Raw'),
        'Ensayo_Raw': _serie_o_nulos(df, 'Ensayo_Raw'),
        'Medida_Raw': _serie_o_nulos(df, 'Medida_Raw'),
        'Fecha_Poda_Aux_Raw': _serie_o_nulos(df, 'Fecha_Poda_Aux_Raw'),
        'Campana_Raw': _serie_o_nulos(df, 'CAMPANA_Raw'),
        'Observacion_Raw': _serie_o_nulos(df, 'Observacion_Raw'),
        'Tipo_Evaluacion_Raw': _serie_o_nulos(df, 'Evaluacion_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = {
        'Unnamed0_Raw',
        'Semana_Raw',
        'Dia_Raw',
        'Fecha_Raw',
        'DNI_Raw',
        'EVALUADOR_A_Raw',
        'Mod_Raw',
        'Tur_Raw',
        'Val_Raw',
        'Condicion_Raw',
        'Estado_Vegetativo_Raw',
        'Variedad_Raw',
        'Cama_Raw',
        'Tipo_de_Tallo_Raw',
        'Ensayo_Raw',
        'Medida_Raw',
        'Fecha_Poda_Aux_Raw',
        'CAMPANA_Raw',
        'Observacion_Raw',
        'Evaluacion_Raw',
    }
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _detectar_header_idx(ruta_archivo: Path, tabla_destino: str, engine) -> int:
    """
    Detecta si encabezado real esta en fila 0 o fila 1 comparando
    columnas del Excel vs columnas reales de la tabla Bronce.
    """
    columnas_bronce = _obtener_columnas_bronce(tabla_destino, engine)
    columnas_raw = {col for col in columnas_bronce if str(col).endswith('_Raw')}

    if not columnas_raw:
        return 0

    candidatos = {}
    for idx in (0, 1):
        try:
            cols = _columnas_normalizadas_excel(ruta_archivo, idx)
        except Exception:
            continue
        candidatos[idx] = cols

    if not candidatos:
        return 0

    mejor_idx = 0
    mejor_score = (-1, -1, -1)

    for idx, cols in candidatos.items():
        set_cols = set(cols)
        match = len(set_cols & columnas_raw)
        unnamed = sum(1 for col in cols if str(col).lower().startswith('unnamed'))
        desconocidas = len(set_cols - columnas_raw)
        score = (match, -unnamed, -desconocidas)
        if score > mejor_score:
            mejor_idx = idx
            mejor_score = score

    return mejor_idx


def _serializar_valores_extra(df: pd.DataFrame, columnas_extra: list[str]) -> pd.Series:
    """
    Serializa columnas no mapeadas en formato "col=valor | col2=valor2".
    Versión vectorizada para alta performance en archivos grandes.
    """
    if not columnas_extra:
        return pd.Series([None] * len(df), index=df.index)

    # Inicializar con serie de strings vacíos
    res = pd.Series("", index=df.index, dtype=str)
    
    for col in columnas_extra:
        # Extraer, convertir a string y limpiar
        val = df[col].astype(str).str.strip()
        # Máscara de valores que ignoraremos (vacíos, None, nan)
        mask = (val == "") | (val.str.lower() == "none") | (df[col].isna())
        
        # Preparar fragmento "NombreColumna=Valor"
        fragmento = col + "=" + val
        fragmento[mask] = ""
        
        # Concatenar usando separador. str.cat con na_rep="" maneja la unión eficientemente
        res = res.str.cat(fragmento, sep=" | ", na_rep="").str.strip(" | ")
        
    return res.replace("", None)


def _formatear_columnas_extra(columnas_extra: list[str], max_columnas: int = 12) -> str:
    """
    Devuelve una version legible de las columnas extra detectadas.
    Limita la salida para no romper el log de consola.
    """
    if not columnas_extra:
        return ''

    columnas_ordenadas = sorted(str(col) for col in columnas_extra)
    if len(columnas_ordenadas) <= max_columnas:
        return ', '.join(columnas_ordenadas)

    visibles = ', '.join(columnas_ordenadas[:max_columnas])
    restantes = len(columnas_ordenadas) - max_columnas
    return f'{visibles}, ... (+{restantes} mas)'


def _alinear_dataframe_a_tabla(
    df: pd.DataFrame,
    tabla_destino: str,
    engine,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Alinea columnas del DataFrame con columnas fisicas de la tabla SQL.
    - Aplica mapeos de compatibilidad entre layouts de Excel.
    - Descarta columnas no existentes en SQL.
    - Si existe Valores_Raw, serializa columnas descartadas para no perder dato.
    """
    columnas_tabla = _obtener_columnas_bronce(tabla_destino, engine)
    if not columnas_tabla:
        return df, []

    if 'Evaluador_Raw' in columnas_tabla and 'Evaluador_Raw' not in df.columns and 'Nombres_Raw' in df.columns:
        df['Evaluador_Raw'] = df['Nombres_Raw']
    if 'Variedad_Raw' in columnas_tabla and 'Variedad_Raw' not in df.columns and 'Descripcion_Raw' in df.columns:
        df['Variedad_Raw'] = df['Descripcion_Raw']
    if 'Tipo_Evaluacion_Raw' in columnas_tabla and 'Tipo_Evaluacion_Raw' not in df.columns and 'Evaluacion_Raw' in df.columns:
        df['Tipo_Evaluacion_Raw'] = df['Evaluacion_Raw']
    if 'TallosPlanta_Raw' in columnas_tabla and 'TallosPlanta_Raw' not in df.columns and 'Tallos_Planta_Raw' in df.columns:
        df['TallosPlanta_Raw'] = df['Tallos_Planta_Raw']
    if 'LongitudTallo_Raw' in columnas_tabla and 'LongitudTallo_Raw' not in df.columns and 'Longitud_de_Tallo_Raw' in df.columns:
        df['LongitudTallo_Raw'] = df['Longitud_de_Tallo_Raw']
    if 'DiametroTallo_Raw' in columnas_tabla and 'DiametroTallo_Raw' not in df.columns and 'Diametro_de_Tallo_Raw' in df.columns:
        df['DiametroTallo_Raw'] = df['Diametro_de_Tallo_Raw']
    if 'RamillaPlanta_Raw' in columnas_tabla and 'RamillaPlanta_Raw' not in df.columns and 'Ramilla_Planta_Raw' in df.columns:
        df['RamillaPlanta_Raw'] = df['Ramilla_Planta_Raw']
    if 'ToconesPlanta_Raw' in columnas_tabla and 'ToconesPlanta_Raw' not in df.columns and 'Tocones_Planta_Raw' in df.columns:
        df['ToconesPlanta_Raw'] = df['Tocones_Planta_Raw']
    if 'CortesDefectuosos_Raw' in columnas_tabla and 'CortesDefectuosos_Raw' not in df.columns and 'N_Cortes_Defect_Planta_Raw' in df.columns:
        df['CortesDefectuosos_Raw'] = df['N_Cortes_Defect_Planta_Raw']
    if 'AlturaPoda_Raw' in columnas_tabla and 'AlturaPoda_Raw' not in df.columns and 'Altura_de_Planta_Raw' in df.columns:
        df['AlturaPoda_Raw'] = df['Altura_de_Planta_Raw']
    if 'Semanas_Poda_Raw' in columnas_tabla and 'Semanas_Poda_Raw' not in df.columns and 'N_de_cama_Raw' in df.columns:
        df['Semanas_Poda_Raw'] = df['N_de_cama_Raw']

    columnas_extra = [col for col in df.columns if col not in columnas_tabla]

    if columnas_extra and 'Valores_Raw' in columnas_tabla:
        extras_serializados = _serializar_valores_extra(df, columnas_extra)
        if 'Valores_Raw' in df.columns:
            base = df['Valores_Raw'].astype(str).replace({'None': ''}).fillna('')
            extra = extras_serializados.astype(str).replace({'None': ''}).fillna('')
            combinado = (base.str.strip() + ' | ' + extra.str.strip()).str.strip(' |')
            df['Valores_Raw'] = combinado.replace('', None)
        else:
            df['Valores_Raw'] = extras_serializados

    columnas_insertables = [col for col in df.columns if col in columnas_tabla]
    if not columnas_insertables:
        return df.iloc[:, 0:0], columnas_extra

    return df[columnas_insertables], columnas_extra


def _detectar_ruta_sugerida(
    columnas_detectadas: set[str],
    nombre_carpeta_actual: str,
) -> tuple[str | None, float]:
    mejor_ruta = None
    mejor_score = 0.0

    for ruta, firma in _FIRMAS_RUTA_SUGERIDA.items():
        if ruta == nombre_carpeta_actual:
            continue

        columnas_clave = set(firma.get('columnas_clave', set()))
        if not columnas_clave:
            continue

        coincidencias = len(columnas_detectadas & columnas_clave)
        score = coincidencias / len(columnas_clave)
        if score >= 0.8 and coincidencias >= 6 and score > mejor_score:
            mejor_ruta = ruta
            mejor_score = score

    return mejor_ruta, mejor_score


def _score_ruta_actual(
    columnas_detectadas: set[str],
    nombre_carpeta_actual: str,
) -> float:
    firma = _FIRMAS_RUTA_SUGERIDA.get(nombre_carpeta_actual)
    if not firma:
        return 0.0

    columnas_clave = set(firma.get('columnas_clave', set()))
    if not columnas_clave:
        return 0.0

    coincidencias = len(columnas_detectadas & columnas_clave)
    return coincidencias / len(columnas_clave)


def _validar_layout_critico(
    nombre_carpeta: str,
    tabla_destino: str,
    columnas_detectadas: set[str],
) -> dict | None:
    firma = _FIRMAS_LAYOUT_CRITICO.get(tabla_destino)
    if not firma:
        return None

    columnas_obligatorias = set(firma.get('columnas_obligatorias', set()))
    faltantes = sorted(columnas_obligatorias - columnas_detectadas)
    columnas_incompatibles = sorted(columnas_detectadas & set(firma.get('columnas_incompatibles', set())))

    columnas_geo_alternativas = tuple(
        set(grupo) for grupo in firma.get('columnas_geo_alternativas', tuple())
    )
    if columnas_geo_alternativas and not any(
        grupo.issubset(columnas_detectadas)
        for grupo in columnas_geo_alternativas
    ):
        faltantes.append('Fundo_Raw o Turno_Raw+Valvula_Raw')

    columnas_brote_alternativas = tuple(
        set(grupo) for grupo in firma.get('columnas_brote_alternativas', tuple())
    )
    if columnas_brote_alternativas and not any(
        grupo.issubset(columnas_detectadas)
        for grupo in columnas_brote_alternativas
    ):
        faltantes.append('Brote_Raw o BrotesProd_Raw')

    if not faltantes:
        return None

    if not columnas_incompatibles and not firma.get('rechazar_por_faltantes', False):
        return None

    ruta_sugerida, _ = _detectar_ruta_sugerida(columnas_detectadas, nombre_carpeta)
    columnas_clave = sorted(
        columnas_detectadas & (columnas_obligatorias | set(firma.get('columnas_incompatibles', set())))
    )
    detalle_ruta = (
        f'Ruta sugerida: {ruta_sugerida}'
        if ruta_sugerida
        else 'Ruta sugerida: sin ruta compatible conocida en el ETL actual'
    )

    return {
        'codigo': 'LAYOUT_INCOMPATIBLE',
        'tabla': tabla_destino,
        'ruta_recibida': nombre_carpeta,
        'faltantes': faltantes,
        'columnas_detectadas_clave': columnas_clave,
        'ruta_sugerida': ruta_sugerida,
        'mensaje': (
            f'LAYOUT_INCOMPATIBLE | archivo incompatible con {nombre_carpeta} -> {tabla_destino}. '
            f'Faltantes: {", ".join(faltantes)} | '
            f'Detectadas clave: {", ".join(columnas_clave) if columnas_clave else "ninguna"} | '
            f'Motivo: {firma["motivo"]} | {detalle_ruta}'
        ),
    }


def _validar_enrutamiento_global(
    nombre_carpeta: str,
    tabla_destino: str,
    columnas_detectadas: set[str],
) -> dict | None:
    if nombre_carpeta not in _FIRMAS_RUTA_SUGERIDA:
        return None

    ruta_sugerida, score_sugerida = _detectar_ruta_sugerida(columnas_detectadas, nombre_carpeta)
    if not ruta_sugerida:
        return None

    score_actual = _score_ruta_actual(columnas_detectadas, nombre_carpeta)
    if score_actual >= 0.5:
        return None

    columnas_clave_sugeridas = sorted(
        columnas_detectadas & set(_FIRMAS_RUTA_SUGERIDA[ruta_sugerida].get('columnas_clave', set()))
    )
    return {
        'codigo': 'RUTA_CONTENIDO_INCOMPATIBLE',
        'tabla': tabla_destino,
        'ruta_recibida': nombre_carpeta,
        'ruta_sugerida': ruta_sugerida,
        'mensaje': (
            f'RUTA_CONTENIDO_INCOMPATIBLE | archivo recibido en {nombre_carpeta} -> {tabla_destino}, '
            f'pero su contenido coincide con alta confianza con la ruta {ruta_sugerida}. '
            f'Score actual: {score_actual:.2f} | Score sugerido: {score_sugerida:.2f} | '
            f'Columnas clave detectadas: {", ".join(columnas_clave_sugeridas) if columnas_clave_sugeridas else "ninguna"}'
        ),
    }


def cargar_archivo(nombre_carpeta: str,
                   ruta_archivo: Path,
                   tabla_destino: str,
                   engine) -> dict:
    """
    Carga un archivo Excel a su tabla Bronce destino.
    Retorna resumen del resultado.
    """
    resultado = {
        'archivo':   ruta_archivo.name,
        'tabla':     tabla_destino,
        'filas':     0,
        'estado':    'ERROR',
        'mensaje':   '',
    }
    ruta_trabajo: Path | None = None

    try:
        ruta_trabajo = _crear_copia_temporal_excel(ruta_archivo)

        if nombre_carpeta in {'reporte_clima', 'variables_meteorologicas'}:
            df = _proyectar_dataframe_clima_bronce(ruta_trabajo, tabla_destino)
        elif nombre_carpeta == 'peladas':
            df = _proyectar_dataframe_peladas_bronce(ruta_trabajo)
        elif nombre_carpeta == 'induccion_floral':
            df = _proyectar_dataframe_induccion_floral_bronce(ruta_trabajo)
        elif nombre_carpeta == 'tasa_crecimiento_brotes':
            df = _proyectar_dataframe_tasa_crecimiento_brotes_bronce(ruta_trabajo)
        else:
            header_idx = _detectar_header_idx(ruta_trabajo, tabla_destino, engine)
            df = pd.read_excel(str(ruta_trabajo), header=header_idx, dtype=str, engine='openpyxl')
            if df.empty:
                resultado['mensaje'] = 'Archivo vacio - sin filas para cargar'
                resultado['estado'] = 'VACIO'
                return resultado
            df = normalizar_columnas(df)

        if df.empty:
            resultado['mensaje'] = 'Archivo vacio - sin filas para cargar'
            resultado['estado'] = 'VACIO'
            return resultado

        validacion_layout = _validar_layout_critico(
            nombre_carpeta,
            tabla_destino,
            {str(col) for col in df.columns},
        )
        if not validacion_layout:
            validacion_layout = _validar_enrutamiento_global(
                nombre_carpeta,
                tabla_destino,
                {str(col) for col in df.columns},
            )
        if validacion_layout:
            ruta_rechazada, archivo_bloqueado = archivar_archivo_rechazado(
                ruta_archivo,
                nombre_carpeta,
                validacion_layout['codigo'],
            )
            resultado['estado'] = 'ERROR'
            resultado['critico'] = True
            resultado['codigo'] = validacion_layout['codigo']
            resultado['ruta_sugerida'] = validacion_layout['ruta_sugerida']
            resultado['mensaje'] = (
                f'{validacion_layout["mensaje"]} | '
                f'Archivo movido a rechazados: {ruta_rechazada}'
            )
            if archivo_bloqueado:
                resultado['mensaje'] += ' | original bloqueado: se copio y se marco para omitir reproceso'
            return resultado

        df = castear_todo_a_texto(df)
        df = agregar_columnas_sistema(df, ruta_archivo.name)
        df, columnas_descartadas = _alinear_dataframe_a_tabla(df, tabla_destino, engine)
        if df.shape[1] == 0:
            resultado['estado'] = 'ERROR'
            resultado['mensaje'] = (
                'No hay columnas insertables en la tabla destino. '
                f'Columnas no mapeadas: {len(columnas_descartadas)}'
            )
            return resultado

        filas_insertadas = insertar_en_bronce(df, tabla_destino, engine)
        ruta_procesada, archivo_bloqueado = archivar_archivo(ruta_archivo, nombre_carpeta)

        resultado['filas'] = filas_insertadas
        resultado['estado'] = 'OK'
        resultado['mensaje'] = f'{filas_insertadas} filas insertadas en {tabla_destino}'
        if archivo_bloqueado:
            resultado['mensaje'] += (
                f' | archivo bloqueado: copia archivada en {ruta_procesada}'
                ' y original marcado para omitir reproceso'
            )
        if columnas_descartadas:
            detalle_columnas = _formatear_columnas_extra(columnas_descartadas)
            resultado['columnas_extras'] = sorted(str(col) for col in columnas_descartadas)
            resultado['mensaje'] += (
                f' | columnas extras: {len(columnas_descartadas)}'
                f' [{detalle_columnas}]'
            )

    except Exception as error:
        resultado['mensaje'] = str(error)
        resultado['estado'] = 'ERROR'
    finally:
        if ruta_trabajo is not None:
            try:
                ruta_trabajo.unlink(missing_ok=True)
            except Exception:
                pass

    return resultado


def ejecutar_carga_bronce() -> list[dict]:
    """
    Punto de entrada del modulo Bronce.
    Busca todos los archivos pendientes y los carga a sus tablas destino.
    Retorna lista de resultados por archivo.
    """
    import logging
    _log = logging.getLogger("ETL_Pipeline")
    engine = obtener_engine()
    pendientes = listar_carpetas_con_archivos()
    resultados = []

    if not pendientes:
        _log.info("Bronce: sin archivos pendientes.")
        return resultados

    _log.info(f"Bronce: {len(pendientes)} archivo(s) encontrado(s).")

    for nombre_carpeta, ruta_archivo, tabla_destino in pendientes:
        _log.info(f"Cargando {ruta_archivo.name} -> {tabla_destino}...")

        id_log = registrar_inicio(tabla_destino, ruta_archivo.name)
        resultado = cargar_archivo(
            nombre_carpeta, ruta_archivo, tabla_destino, engine
        )
        registrar_fin(id_log, resultado)

        estado_txt = "OK" if resultado["estado"] == "OK" else "ERROR"
        _log.info(f"[{estado_txt}] {resultado['mensaje']}")

        resultados.append(resultado)

    return resultados
