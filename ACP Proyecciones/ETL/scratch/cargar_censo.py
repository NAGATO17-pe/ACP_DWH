import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.conexion import obtener_engine
from utils.contexto_transaccional import ContextoTransaccionalETL
from bronce.cargador import normalizar_columnas
from mdm.homologador import homologar_columna

def cargar_censo():
    engine = obtener_engine()
    ruta = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica\fact_Censo_Plantas.xlsx'
    
    print("Cargando Censo...")
    df_raw = pd.read_excel(ruta)
    df_raw = normalizar_columnas(df_raw)
    
    # 1. Tomar el registro más reciente por cada combinación geográfica
    # (Modulo, Turno, Valvula, Variedad) tomando la campaña máxima
    sort_cols = ['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw', 'Campana_Raw']
    df = df_raw.sort_values(sort_cols, ascending=False).drop_duplicates(
        subset=['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw'],
        keep='first'
    )
    
    print(f"Filas únicas por unidad: {len(df)} (de {len(df_raw)} totales)")
    
    df['ID_Tiempo'] = 20260101
    df['ID_Registro_Origen'] = range(1, len(df) + 1)
    
    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, _ = homologar_columna(df, 'Variedad_Raw', 'Variedad_Canonica', 'Bronce.Censo', conexion, columna_id_origen='ID_Registro_Origen')
        
        payload = []
        for _, row in df.iterrows():
            def clean_int(v):
                try: return str(int(float(str(v))))
                except: return str(v)
            
            m_val = clean_int(row.get('Modulo_Raw'))
            t_val = clean_int(row.get('Turno_Raw'))
            v_val = clean_int(row.get('Valvula_Raw'))
            var_can = str(row.get('Variedad_Canonica', 'nan'))
            
            if 'nan' in [m_val, t_val, v_val, var_can] or not m_val:
                continue

            # Resolver Geografía
            sql_geo = text("""
                SELECT TOP 1 g.ID_Geografia 
                FROM Silver.Dim_Geografia g
                JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
                JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
                JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
                WHERE m.Modulo = :m AND t.Turno = :t AND v.Valvula = :v
            """)
            res_geo = conexion.execute(sql_geo, {"m": m_val, "t": t_val, "v": v_val}).fetchone()
            if not res_geo: continue
                
            sql_var = text("SELECT ID_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad = :v")
            res_var = conexion.execute(sql_var, {"v": var_can}).fetchone()
            if not res_var: continue
            
            payload.append({
                'ID_Geografia': res_geo[0],
                'ID_Variedad': res_var[0],
                'ID_Tiempo': 20260101,
                'Cantidad_Plantas': float(row.get('Plantas_Raw', 0)),
                'Area_ha': float(row.get('Area_Raw', 0))
            })
            
        if payload:
            print(f"Insertando {len(payload)} registros únicos de Censo...")
            conexion.execute(text("TRUNCATE TABLE Silver.Fact_Censo_Plantas"))
            for p in payload:
                conexion.execute(text("""
                    INSERT INTO Silver.Fact_Censo_Plantas (ID_Geografia, ID_Variedad, ID_Tiempo, Cantidad_Plantas, Area_ha)
                    VALUES (:ID_Geografia, :ID_Variedad, :ID_Tiempo, :Cantidad_Plantas, :Area_ha)
                """), p)
            print("Censo cargado con éxito.")

if __name__ == "__main__":
    cargar_censo()
