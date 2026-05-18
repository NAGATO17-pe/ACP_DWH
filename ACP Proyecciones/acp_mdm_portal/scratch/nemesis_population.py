"""
NEMESIS: Generador de Datos (Version Infalible v2)
"""
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from utils.db import obtener_engine

def poblar_nemesis():
    engine = obtener_engine()
    print("--- Nemesis: Version Infalible ---")
    ahora = datetime.now()

    with engine.begin() as conn:
        print("Limpiando...")
        conn.execute(text("DELETE FROM Silver.Fact_Conteo_Fenologico WHERE ID_Tiempo >= 20260101"))
        conn.execute(text("DELETE FROM Silver.Fact_Cosecha_SAP WHERE ID_Tiempo = 20260101"))
        
        # Obtener geografias para modulo 1 (Convencional) y modulo 11 (Organico)
        geo = pd.read_sql(text("""
            SELECT TOP 20 g.ID_Geografia, m.Modulo 
            FROM Silver.Dim_Geografia g WITH (NOLOCK)
            JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE m.Modulo IN (1, 11)
        """), conn)
        
        var = pd.read_sql(text("SELECT TOP 5 ID_Variedad FROM Silver.Dim_Variedad WITH (NOLOCK)"), conn)

    # 1. Cosecha (Condicion)
    cosecha = []
    for _, g in geo.iterrows():
        id_cond = 2 if g['Modulo'] == 11 else 1
        for _, v in var.iterrows():
            cosecha.append({
                'ID_Geografia': g['ID_Geografia'], 
                'ID_Tiempo': 20260101, 
                'ID_Variedad': v['ID_Variedad'], 
                'ID_Condicion_Cultivo': id_cond, 
                'Kg_Brutos': 0, 'Kg_Neto_MP': 0, 'Cantidad_Jabas': 0, 
                'Estado_DQ': 'OK',
                'Fecha_Evento': ahora # Faltaba esta columna
            })
    
    pd.DataFrame(cosecha).to_sql('Fact_Cosecha_SAP', schema='Silver', con=engine, if_exists='append', index=False)
    print(f"Cosecha poblada: {len(cosecha)} filas.")

    # 2. Conteo
    conteo = []
    for _, g in geo.iterrows():
        for _, v in var.iterrows():
            for e in range(1, 10):
                conteo.append({
                    'ID_Geografia': g['ID_Geografia'], 
                    'ID_Tiempo': 20260511, 
                    'ID_Variedad': v['ID_Variedad'], 
                    'ID_Estado_Fenologico': e, 
                    'Cantidad_Organos': 500, 
                    'Punto': 1, 
                    'Fecha_Evento': ahora, 
                    'Estado_DQ': 'OK'
                })

    pd.DataFrame(conteo).to_sql('Fact_Conteo_Fenologico', schema='Silver', con=engine, if_exists='append', index=False)
    print(f"Conteos poblados: {len(conteo)} filas.")
    print("--- Nemesis Terminado ---")

if __name__ == "__main__":
    poblar_nemesis()
