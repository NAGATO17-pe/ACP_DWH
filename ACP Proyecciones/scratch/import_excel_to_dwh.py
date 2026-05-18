
import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import text
from datetime import date, timedelta

# Agregar ETL al path para usar lookups
sys.path.append(str(Path.cwd() / 'ETL'))
from config.conexion import obtener_engine
from mdm.lookup import obtener_id_geografia, obtener_id_variedad

def import_excel_data():
    engine = obtener_engine()
    excel_path = '39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx'
    
    print(f"Leyendo Excel: {excel_path}...")
    df = pd.read_excel(excel_path, sheet_name='Calculo', header=3)
    cols = df.columns.tolist()
    
    # Mapeo de columnas basado en el análisis previo
    # cols[1]: Sem, cols[2]: S, cols[3]: M, cols[4]: T, cols[5]: V, cols[6]: Variedad
    # cols[12]: Proyección (kg)
    # cols[85-90]: Kg Sem 1 a Kg Sem 6
    
    proyecciones_payload = []
    cosecha_payload = []
    
    fecha_base = date(2026, 5, 4) # Lunes Semana 19
    id_tiempo_w1 = 20260504 # ID_Tiempo para el inicio (Semana 19)
    
    seen_cosecha = set()
    seen_proy = set()
    
    print("Procesando filas...")
    for i, row in df.iterrows():
        fundo = str(row[cols[2]]).strip()
        modulo = str(row[cols[3]]).strip()
        turno = str(row[cols[4]]).strip()
        valvula = str(row[cols[5]]).strip()
        variedad_raw = str(row[cols[6]]).strip()
        
        if not fundo or fundo == 'nan': continue
        
        # Resolver Geografía (fundo, sector, modulo, engine, turno, valvula)
        id_geo = obtener_id_geografia(fundo, None, modulo, engine, turno, valvula)
        if id_geo is None or id_geo == -1: continue
        
        # Resolver Variedad
        id_var = obtener_id_variedad(variedad_raw, engine)
        if id_var is None or id_var == -1: continue
        
        # 1. Cosecha SAP (Simulada para kg_base)
        kg_base = float(row[cols[12]]) if pd.notnull(row[cols[12]]) else 0
        if kg_base > 0:
            id_t = 20260427
            key = (id_t, id_geo, id_var)
            if key not in seen_cosecha:
                cosecha_payload.append({
                    'ID_Tiempo': id_t,
                    'ID_Geografia': id_geo,
                    'ID_Variedad': id_var,
                    'Kg_Neto_MP': kg_base,
                    'Fecha_Evento': date(2026, 4, 27),
                    'Fecha_Sistema': pd.Timestamp.now(),
                    'Estado_DQ': 'OK'
                })
                seen_cosecha.add(key)
            
        # 2. Proyecciones Six-Week (Directas del Excel)
        for sem_idx in range(6): # Sem 1 a Sem 6
            col_kg = cols[85 + sem_idx]
            kg_proy = float(row[col_kg]) if pd.notnull(row[col_kg]) else 0
            
            if kg_proy > 0:
                fecha_proy = fecha_base + timedelta(weeks=sem_idx)
                id_t = int(fecha_proy.strftime('%Y%m%d'))
                key = (id_t, id_geo, id_var, 4) # 4 is Scenario Base
                
                if key not in seen_proy:
                    proyecciones_payload.append({
                        'ID_Tiempo': id_t,
                        'ID_Geografia': id_geo,
                        'ID_Variedad': id_var,
                        'ID_Escenario': 4,
                        'ID_Campana': -1,
                        'ID_Estado_Workflow': 1,
                        'Kg_Proyectados': kg_proy,
                        'Kg_Pesimista': kg_proy * 0.95,
                        'Kg_Optimista': kg_proy * 1.05,
                        'Pct_Maduracion': 0.5,
                        'Pct_Productivas': 1.0,
                        'Fecha_Cutoff': fecha_base,
                        'Fecha_Evento': fecha_proy,
                        'Fecha_Sistema': pd.Timestamp.now(),
                        'Version_Modelo': 'excel-import-test',
                        'Estado_DQ': 'OK'
                    })
                    seen_proy.add(key)

    print(f"Insertando {len(cosecha_payload)} registros en Silver.Fact_Cosecha_SAP...")
    c_ok, c_err = 0, 0
    for row_data in cosecha_payload:
        row_data['ID_Condicion_Cultivo'] = 1 # Suelo / GlobalGAP
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO Silver.Fact_Cosecha_SAP (
                        ID_Tiempo, ID_Geografia, ID_Variedad, ID_Condicion_Cultivo,
                        Kg_Neto_MP, Fecha_Evento, Fecha_Sistema, Estado_DQ
                    ) VALUES (
                        :ID_Tiempo, :ID_Geografia, :ID_Variedad, :ID_Condicion_Cultivo,
                        :Kg_Neto_MP, :Fecha_Evento, :Fecha_Sistema, :Estado_DQ
                    )
                """), row_data)
                c_ok += 1
        except Exception as e:
            c_err += 1
            if c_err == 1: print(f"Primer error Cosecha: {e}")
    print(f"Cosecha: {c_ok} OK, {c_err} ERR")
            
    print(f"Insertando {len(proyecciones_payload)} registros en Silver.Fact_Proyecciones...")
    p_ok, p_err = 0, 0
    for row_data in proyecciones_payload:
        row_data['ID_Campana'] = 4 # Campana default para test
        row_data['Flag_Override'] = False
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO Silver.Fact_Proyecciones (
                        ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, ID_Campana,
                        ID_Estado_Workflow, Kg_Proyectados, Kg_Pesimista, Kg_Optimista,
                        Pct_Maduracion, Pct_Productivas, Fecha_Cutoff, Fecha_Evento, 
                        Fecha_Sistema, Version_Modelo, Estado_DQ, Flag_Override
                    ) VALUES (
                        :ID_Tiempo, :ID_Geografia, :ID_Variedad, :ID_Escenario, :ID_Campana,
                        :ID_Estado_Workflow, :Kg_Proyectados, :Kg_Pesimista, :Kg_Optimista,
                        :Pct_Maduracion, :Pct_Productivas, :Fecha_Cutoff, :Fecha_Evento, 
                        :Fecha_Sistema, :Version_Modelo, :Estado_DQ, :Flag_Override
                    )
                """), row_data)
                p_ok += 1
        except Exception as e:
            p_err += 1
            if p_err == 1: print(f"Primer error Proyeccion: {e}")
    print(f"Proyecciones: {p_ok} OK, {p_err} ERR")
            
    print("Importación completada.")

if __name__ == "__main__":
    import_excel_data()
