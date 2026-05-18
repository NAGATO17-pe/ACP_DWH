import sys
import os
import json
import pandas as pd
import numpy as np
import copy
from datetime import datetime

from utils.db import ejecutar_query
from utils.motor_proyecciones import ejecutar_proyeccion, obtener_fechas_disponibles, MATRIZ_INPUTS_DEFAULT

def phase_2():
    tables = [
        "Silver.Fact_Conteo_Fenologico",
        "Silver.Fact_Peladas",
        "Silver.Fact_Evaluacion_Pesos",
        "Silver.Fact_Cosecha_SAP",
        "Silver.Fact_Proyecciones",
        "Silver.Fact_Maduracion"
    ]
    
    results = {}
    
    for tbl in tables:
        try:
            df = ejecutar_query(f"SELECT TOP 10000 * FROM {tbl}")
            if len(df) == 0:
                results[tbl] = "Empty table"
                continue
                
            num_rows = len(df)
            num_cols = len(df.columns)
            
            nulls = df.isnull().sum()
            completeness_score = 1.0 - float(nulls.sum() / (num_rows * num_cols))
            
            numeric_cols = df.select_dtypes(include=['number']).columns
            negatives = 0
            for col in numeric_cols:
                if col not in ['ID_Tiempo', 'ID_Geografia']:
                    negatives += (df[col] < 0).sum()
                    
            consistency_score = 1.0 - float(negatives / (num_rows * len(numeric_cols))) if len(numeric_cols) > 0 else 1.0
            
            results[tbl] = {
                'rows_sample': num_rows,
                'cols': num_cols,
                'completeness_score': float(completeness_score),
                'consistency_score': float(consistency_score),
                'null_pct_by_col': {str(k): float(v) for k, v in (nulls / num_rows).items()}
            }
        except Exception as e:
            results[tbl] = {'error': str(e)}
            
    with open('C:/Users/chernandez/.gemini/antigravity/brain/e4cc7ae7-763e-4965-a9b7-e3d8891de95e/scratch/fase2_results.json', 'w') as f:
        json.dump(results, f, indent=2)

def phase_3():
    fechas = obtener_fechas_disponibles()
    if not fechas:
        return
    id_t = fechas[0]
    
    # Base
    base_res = ejecutar_proyeccion(id_t)
    base_kg = float(base_res['kpis']['total_base']) if 'kpis' in base_res and base_res['kpis'] else 0.0
    
    # +5%
    mat_plus_5 = copy.deepcopy(MATRIZ_INPUTS_DEFAULT)
    for est, wks in mat_plus_5.items():
        for w, val in wks.items():
            if val is not None:
                mat_plus_5[est][w] = min(1.0, val * 1.05)
                
    plus_5_res = ejecutar_proyeccion(id_t, matriz_inputs=mat_plus_5)
    plus_5_kg = float(plus_5_res['kpis']['total_base']) if 'kpis' in plus_5_res and plus_5_res['kpis'] else 0.0
    
    # -5%
    mat_minus_5 = copy.deepcopy(MATRIZ_INPUTS_DEFAULT)
    for est, wks in mat_minus_5.items():
        for w, val in wks.items():
            if val is not None:
                mat_minus_5[est][w] = max(0.0, val * 0.95)
                
    minus_5_res = ejecutar_proyeccion(id_t, matriz_inputs=mat_minus_5)
    minus_5_kg = float(minus_5_res['kpis']['total_base']) if 'kpis' in minus_5_res and minus_5_res['kpis'] else 0.0
    
    res = {
        'id_tiempo': int(id_t),
        'base_kg': base_kg,
        'plus_5_kg': plus_5_kg,
        'minus_5_kg': minus_5_kg,
        'impact_plus_5': (plus_5_kg - base_kg) / base_kg if base_kg else 0,
        'impact_minus_5': (minus_5_kg - base_kg) / base_kg if base_kg else 0,
    }
    with open('C:/Users/chernandez/.gemini/antigravity/brain/e4cc7ae7-763e-4965-a9b7-e3d8891de95e/scratch/fase3_results.json', 'w') as f:
        json.dump(res, f, indent=2)

def phase_4():
    try:
        # We fetch the latest projections that have an actual harvest reported
        query = """
        SELECT TOP 100 
            p.ID_Tiempo as id_tiempo_proy,
            p.Kg_Proyectados,
            c.Cantidad_Kg as Kg_Reales
        FROM Silver.Fact_Proyecciones p
        JOIN Silver.Fact_Cosecha_SAP c ON p.ID_Geografia = c.ID_Geografia AND p.ID_Variedad = c.ID_Variedad AND p.ID_Tiempo = c.ID_Tiempo
        WHERE p.ID_Escenario = 4
        """
        df = ejecutar_query(query)
        if len(df) == 0:
            # fallback
            res = {"error": "No matching actuals found for projections"}
        else:
            mae = float(np.mean(np.abs(df['Kg_Proyectados'] - df['Kg_Reales'])))
            mape = float(np.mean(np.abs((df['Kg_Proyectados'] - df['Kg_Reales']) / df['Kg_Reales'])))
            rmse = float(np.sqrt(np.mean((df['Kg_Proyectados'] - df['Kg_Reales'])**2)))
            bias = float(np.mean((df['Kg_Proyectados'] - df['Kg_Reales']) / df['Kg_Reales']))
            
            res = {
                "MAE": mae,
                "MAPE": mape,
                "RMSE": rmse,
                "Bias": bias,
                "Forecast_Accuracy": 1.0 - mape,
                "Sample_Size": len(df)
            }
    except Exception as e:
        res = {"error": str(e)}

    with open('C:/Users/chernandez/.gemini/antigravity/brain/e4cc7ae7-763e-4965-a9b7-e3d8891de95e/scratch/fase4_results.json', 'w') as f:
        json.dump(res, f, indent=2)

if __name__ == '__main__':
    phase_2()
    phase_3()
    phase_4()
