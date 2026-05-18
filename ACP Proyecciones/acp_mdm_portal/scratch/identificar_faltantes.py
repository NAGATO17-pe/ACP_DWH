import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db import ejecutar_query

def identificar_faltantes():
    print("Cargando datos históricos desde Excel...")
    df_excel = pd.read_excel(r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica\fact_Fenologia.xlsx')
    
    # Filtrar por 2025-W24
    # Usando iloc para evitar problemas de encoding en los nombres de columna
    mask = (df_excel.iloc[:, 1] == 2025) & (df_excel.iloc[:, 2] == 24)
    df_h = df_excel[mask].copy()
    
    # Normalizar nombres para comparación
    df_h['M'] = df_h['Modulo'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_h['T'] = df_h['Turno'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_h['V'] = df_h['Valvula'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_h['Var'] = df_h['Variedad'].astype(str).str.strip().str.upper()
    
    unidades_excel = set(df_h.apply(lambda r: f"{r['M']}-{r['T']}-{r['V']}-{r['Var']}", axis=1))
    print(f"Unidades en Excel (W24): {len(unidades_excel)}")
    
    print("Cargando datos desde la Base de Datos (W24)...")
    sql_db = """
    SELECT DISTINCT
        m.Modulo, t.Turno, v.Valvula, var.Nombre_Variedad
    FROM Silver.Fact_Conteo_Fenologico f
    JOIN Silver.Dim_Geografia g ON f.ID_Geografia = g.ID_Geografia
    JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
    JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
    JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
    JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
    JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
    WHERE dt.Anio = 2025 AND dt.Semana_ISO = 24
    """
    df_db = ejecutar_query(sql_db)
    
    df_db['M'] = df_db['Modulo'].astype(str).str.strip()
    df_db['T'] = df_db['Turno'].astype(str).str.strip()
    df_db['V'] = df_db['Valvula'].astype(str).str.strip()
    df_db['Var'] = df_db['Nombre_Variedad'].astype(str).str.strip().str.upper()
    
    unidades_db = set(df_db.apply(lambda r: f"{r['M']}-{r['T']}-{r['V']}-{r['Var']}", axis=1))
    print(f"Unidades en DB (W24): {len(unidades_db)}")
    
    faltantes = unidades_excel - unidades_db
    print(f"\nUnidades faltantes en DB: {len(faltantes)}")
    
    if faltantes:
        print("\nEjemplos de unidades faltantes:")
        for f in list(faltantes)[:20]:
            print(f" - {f}")
            
        # Analizar por variedad
        variedades_faltantes = {}
        for f in faltantes:
            v = f.split('-')[-1]
            variedades_faltantes[v] = variedades_faltantes.get(v, 0) + 1
        
        print("\nConteo de faltantes por Variedad:")
        for v, c in variedades_faltantes.items():
            print(f" - {v}: {c}")

if __name__ == "__main__":
    identificar_faltantes()
