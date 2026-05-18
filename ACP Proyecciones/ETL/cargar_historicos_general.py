import sys
import os
import pandas as pd
import numpy as np
import datetime
import json
import re
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Añadir el path base para importar utilidades del ETL
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from config.conexion import obtener_engine
from utils.contexto_transaccional import ContextoTransaccionalETL
from bronce.cargador import normalizar_columnas, castear_todo_a_texto
from mdm.homologador import homologar_columna

# Importar Procesadores Oficiales
from silver.facts.fact_conteo_fenologico import ProcesadorConteoFenologico
from silver.facts.fact_floracion import ProcesadorFloracion as ProcesadorEvaluacionVegetativa
from silver.facts.fact_evaluacion_pesos import ProcesadorEvaluacionPesos
from silver.facts.fact_cosecha_sap import ProcesadorCosechaSAP

def derives_date_from_week(df):
    """Genera una columna Fecha_Raw a partir de Año y Semana si no existe."""
    if 'Fecha_Raw' in df.columns and df['Fecha_Raw'].notna().any():
        return df
    
    def get_date(row):
        try:
            year_val = row.get('Ano_Raw') or row.get('Anio_Raw') or row.get('A_o_Raw') or 2026
            year = int(float(str(year_val).strip()))
            
            week_val = row.get('Semana_Raw') or '1'
            # Limpiar "Sem 31" -> "31"
            week_str = re.sub(r'[^0-9]', '', str(week_val))
            week = int(week_str) if week_str else 1
            
            # Lunes de esa semana (ISO)
            return datetime.datetime.strptime(f'{year}-W{week:02d}-1', "%G-W%V-%u").strftime('%Y-%m-%d')
        except:
            return None
            
    df['Fecha_Raw'] = df.apply(get_date, axis=1)
    return df

def pack_valores_raw_pipe(df, cols_to_pack):
    """Empaqueta columnas en formato Key=Value | Key2=Value2."""
    def row_to_pipe(row):
        parts = []
        for c in cols_to_pack:
            val = row.get(c)
            if val is not None and str(val).strip() not in ('', 'None', 'nan'):
                parts.append(f"{c}={val}")
        return " | ".join(parts)
    
    df['Valores_Raw'] = df.apply(row_to_pipe, axis=1)
    return df

def ejecutar_carga_directa(nombre_tarea, ruta_excel, procesador_init_func, tabla_bronce_ref, mapping_adicional=None, pack_cols=None):
    engine = obtener_engine()
    print(f"\n>>> Procesando {nombre_tarea}...")
    
    # 1. Leer Archivo
    if ruta_excel.endswith('.csv'):
        df = pd.read_csv(ruta_excel, encoding='latin1')
    else:
        df = pd.read_excel(ruta_excel)
    
    # 2. Normalizar Columnas
    df = normalizar_columnas(df)
    
    if mapping_adicional:
        df = df.rename(columns=mapping_adicional)
    
    df = derives_date_from_week(df)
    
    if pack_cols:
        df = pack_valores_raw_pipe(df, pack_cols)

    # Alias comunes para geografía
    if 'M_Raw' in df.columns and 'Modulo_Raw' not in df.columns:
        df['Modulo_Raw'] = df['M_Raw']

    # Forzar CantMuestra para Pesos
    if nombre_tarea == 'Pesos':
        df['CantMuestra_Raw'] = '1'

    df = castear_todo_a_texto(df)
    
    id_bronce_name = f"ID_{tabla_bronce_ref.split('.')[-1]}"
    df['ID_Registro_Origen'] = range(1, len(df) + 1)
    df[id_bronce_name] = df['ID_Registro_Origen']
    
    # 3. Inicializar Procesador
    try:
        proc = procesador_init_func(engine)
    except TypeError:
        proc = procesador_init_func(engine, id_bronce_name)

    proc.resumen['leidos'] = len(df)
    
    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        
        # 4. Homologar Variedades
        col_var = 'Variedad_Raw' if 'Variedad_Raw' in df.columns else 'Descripcion_Raw'
        if col_var in df.columns:
            df, cuarentenas = homologar_columna(
                df, col_var, 'Variedad_Canonica', tabla_bronce_ref, conexion,
                columna_id_origen=id_bronce_name
            )
            proc.resumen['cuarentena'].extend(cuarentenas)
        
        # 5. Construir Payload
        if 'Fundo_Raw' not in df.columns:
            df['Fundo_Raw'] = 'AGROCAPITAL'
            
        payload = proc._construir_payload(df)
        
        if not payload:
            print(f"    AVISO: Payload vacio. Debug: Col={df.columns.tolist()[:10]}... Row1={df.iloc[0].to_dict() if not df.empty else 'Empty'}")
            return

        print(f"    Insertando {len(payload)} registros en {proc.tabla_destino}...")
        proc._ejecutar_insercion_masiva_segura(contexto, payload, f'#Temp_Hist_{nombre_tarea}')
        print(f"    ¡EXITO! {nombre_tarea} cargado.")

if __name__ == "__main__":
    base_path = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica'
    
    feno_pack = [
        'Botones_Florales_Raw', 'Flores_Raw', 'Bayas_Pequenas_Raw',
        'Bayas_Grandes_Verdes_Raw', 'Fase1_Raw', 'Fase2_Raw',
        'Bayas_Cremas_Raw', 'Bayas_Maduras_Raw', 'Bayas_Cosechables_Raw',
        # Yema Hinchada: Excel normaliza "Yema Hinchada" → "Yema_Hinchada_Raw"
        'Yema_Hinchada_Raw',
        # Plantas: presentes en hojas de campo más recientes
        'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw',
    ]
    
    tareas = [
        {
            'nombre': 'Fenologia',
            'archivo': 'fact_Fenologia.xlsx',
            'proc_init': lambda eng: ProcesadorConteoFenologico(eng),
            'bronce': 'Bronce.Conteo_Fruta',
            'map': {
                'Boton_Raw': 'Botones_Florales_Raw',
                'Flor_Raw': 'Flores_Raw',
                'Peque_a_Raw': 'Bayas_Pequenas_Raw',
                'Pequena_Raw': 'Bayas_Pequenas_Raw',
                'Verde_Raw': 'Bayas_Grandes_Verdes_Raw',
                'Fase_1_Raw': 'Fase1_Raw',
                'Fase_2_Raw': 'Fase2_Raw',
                'Crema_Raw': 'Bayas_Cremas_Raw',
                'Madura_Raw': 'Bayas_Maduras_Raw',
                'Cosechable_Raw': 'Bayas_Cosechables_Raw'
            },
            'pack': feno_pack
        },
        {
            'nombre': 'Vegetativa',
            'archivo': 'fact_Evaluacion_vegetativa.xlsx',
            'proc_init': lambda eng, cid: ProcesadorEvaluacionVegetativa(eng, cid),
            'bronce': 'Bronce.Floracion',
            'map': {
                'Evaluaci_n_Raw': 'Evaluacion_Raw',
                'N_de_cama_Raw': 'Cama_Raw',
                'Altura_Raw': 'N_Plantas_Evaluadas_Raw',
                'Tallos_basales_Raw': 'N_Plantas_en_Floracion_Raw'
            }
        },
        {
            'nombre': 'Pesos',
            'archivo': 'Fact_pesos.xlsx',
            'proc_init': lambda eng: ProcesadorEvaluacionPesos(eng),
            'bronce': 'Bronce.Evaluacion_Pesos',
            'map': {
                'M_Raw': 'Modulo_Raw',
                'Peso_Promedio_Raw': 'PesoBaya_Raw',
                'Campa_a_Raw': 'Campana_Raw'
            }
        },
        {
            'nombre': 'Cosecha',
            'archivo': 'historico_BI_Cosecha3.xlsx',
            'proc_init': lambda eng: ProcesadorCosechaSAP(eng, id_condicion_default=1),
            'bronce': 'Bronce.Data_SAP',
            'map': {'Kg_Total_Raw': 'Peso_Neto_Raw'}
        }
    ]
    
    for t in tareas:
        ruta = os.path.join(base_path, t['archivo'])
        if os.path.exists(ruta):
            ejecutar_carga_directa(t['nombre'], ruta, t['proc_init'], t['bronce'], t.get('map'), t.get('pack'))
        else:
            print(f"Archivo no encontrado: {t['archivo']}")
