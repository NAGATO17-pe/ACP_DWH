import pandas as pd
import sys
import os
from datetime import datetime

# Rutas
backend_path = r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend"
sys.path.insert(0, backend_path)
from nucleo.conexion import obtener_engine
from sqlalchemy import text

def cargar_historico():
    engine = obtener_engine()
    csv_path = r"C:\Users\chernandez\Desktop\Historico Podas.csv"
    
    print(f"Leyendo {csv_path}...")
    df = pd.read_csv(csv_path, sep=';', encoding='latin1', skiprows=1, header=None)
    df.columns = ['Año', 'Variedad', 'Modulo', 'Sem Poda']
    
    # Asegurar tipos de datos correctos
    df = df.dropna(subset=['Año', 'Sem Poda', 'Modulo'])
    df['Año'] = df['Año'].astype(int)
    df['Sem Poda'] = df['Sem Poda'].astype(int)
    
    # Modulo: si es numérico, quitar el .0 convirtiendo a int -> str
    def normalizar_mod(val):
        try:
            return str(int(float(val)))
        except:
            return str(val).strip()
    df['Modulo'] = df['Modulo'].apply(normalizar_mod)
    
    # 1. Obtener mapeos
    with engine.connect() as conn:
        df_modulos = pd.read_sql("SELECT ID_Modulo_Catalogo, Modulo FROM Silver.Dim_Modulo_Catalogo WHERE Es_Activa = 1", conn)
        df_variedades = pd.read_sql("SELECT ID_Variedad, Nombre_Variedad FROM Silver.Dim_Variedad", conn)
        df_geo = pd.read_sql("SELECT MIN(ID_Geografia) as ID_Geografia, ID_Modulo_Catalogo FROM Silver.Dim_Geografia GROUP BY ID_Modulo_Catalogo", conn)
        df_tiempo = pd.read_sql("SELECT ID_Tiempo, Fecha FROM Silver.Dim_Tiempo", conn)
        df_tiempo['Fecha'] = pd.to_datetime(df_tiempo['Fecha'])

    # 2. Procesar
    payload = []
    for _, row in df.iterrows():
        try:
            # Año y Semana a Fecha (Lunes de esa semana)
            fecha_poda = datetime.fromisocalendar(int(row['Año']), int(row['Sem Poda']), 1)
            
            # Buscar Variedad
            var_match = df_variedades[df_variedades['Nombre_Variedad'].str.upper() == str(row['Variedad']).upper()]
            if var_match.empty:
                print(f"Variedad no encontrada: {row['Variedad']}")
                continue
            id_var = int(var_match.iloc[0]['ID_Variedad'])
            
            # Buscar Modulo
            mod_match = df_modulos[df_modulos['Modulo'].astype(str) == str(row['Modulo'])]
            if mod_match.empty:
                # Intentar con "MODULO X" si solo viene el numero
                mod_match = df_modulos[df_modulos['Modulo'].astype(str).str.contains(str(row['Modulo']))]
                if mod_match.empty:
                    print(f"Modulo no encontrado: {row['Modulo']}")
                    continue
            id_mod_cat = int(mod_match.iloc[0]['ID_Modulo_Catalogo'])
            
            # Buscar Geografia representativa
            geo_match = df_geo[df_geo['ID_Modulo_Catalogo'] == id_mod_cat]
            if geo_match.empty:
                print(f"Sin geografia para Modulo {id_mod_cat}")
                continue
            id_geo = int(geo_match.iloc[0]['ID_Geografia'])
            
            # Buscar Tiempo
            tiempo_match = df_tiempo[df_tiempo['Fecha'] == pd.Timestamp(fecha_poda)]
            if tiempo_match.empty:
                print(f"Fecha fuera de Dim_Tiempo: {fecha_poda}")
                continue
            id_tiempo = int(tiempo_match.iloc[0]['ID_Tiempo'])
            
            payload.append({
                'ID_Geografia': id_geo,
                'ID_Tiempo': id_tiempo,
                'ID_Variedad': id_var,
                'Tipo_Evaluacion': 'HISTORICO_CSV',
                'Fecha_Evento': fecha_poda,
                'Fecha_Sistema': datetime.now(),
                'Estado_DQ': 'OK'
            })
        except Exception as e:
            print(f"Error procesando fila {row}: {e}")

    if not payload:
        print("No hay datos para cargar.")
        return

    # 3. Cargar a Silver.Fact_Ciclo_Poda
    df_payload = pd.DataFrame(payload)
    if df_payload.empty:
        print("No hay datos para cargar.")
        return
        
    # Deduplicar por grano (Geo, Tiempo, Variedad, Tipo)
    df_payload = df_payload.drop_duplicates(subset=['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Tipo_Evaluacion'])
    
    print(f"Cargando {len(df_payload)} registros a Silver.Fact_Ciclo_Poda...")
    
    with engine.begin() as conn:
        # Evitar duplicados exactos (Mismo Modulo, Variedad, Fecha)
        # Para simplificar, insertamos en temporal y MERGE
        conn.execute(text("CREATE TABLE #TmpPodaHist (ID_Geografia INT, ID_Tiempo INT, ID_Variedad INT, Tipo_Evaluacion VARCHAR(50), Fecha_Evento DATE, Fecha_Sistema DATETIME, Estado_DQ VARCHAR(10))"))
        
        # Inserción por lotes
        df_payload.to_sql('#TmpPodaHist', conn, if_exists='append', index=False)
        
        conn.execute(text("""
            INSERT INTO Silver.Fact_Ciclo_Poda (ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion, Fecha_Evento, Fecha_Sistema, Estado_DQ)
            SELECT tmp.* FROM #TmpPodaHist tmp
            WHERE NOT EXISTS (
                SELECT 1 FROM Silver.Fact_Ciclo_Poda dest
                WHERE dest.ID_Geografia = tmp.ID_Geografia
                  AND dest.ID_Variedad = tmp.ID_Variedad
                  AND dest.Fecha_Evento = tmp.Fecha_Evento
            )
        """))
    
    print("Carga completada.")

    # 4. Sincronizar Campañas
    print("Sincronizando periodos de campaña...")
    with engine.begin() as conn:
        conn.execute(text("EXEC Silver.sp_Sincronizar_Periodos_Campana"))
    print("Sincronización finalizada.")

if __name__ == "__main__":
    cargar_historico()
