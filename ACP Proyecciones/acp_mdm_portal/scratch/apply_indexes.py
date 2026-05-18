import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.abspath("."))

try:
    from utils.db import obtener_engine
    engine = obtener_engine()
    
    indices = [
        """
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Fact_ConteoFen_Performance' AND object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico'))
        CREATE NONCLUSTERED INDEX IX_Fact_ConteoFen_Performance 
        ON Silver.Fact_Conteo_Fenologico (ID_Tiempo, ID_Geografia, ID_Variedad)
        INCLUDE (ID_Estado_Fenologico, Cantidad_Organos, Punto);
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Fact_Peladas_Performance' AND object_id = OBJECT_ID('Silver.Fact_Peladas'))
        CREATE NONCLUSTERED INDEX IX_Fact_Peladas_Performance 
        ON Silver.Fact_Peladas (ID_Tiempo, ID_Geografia)
        INCLUDE (Plantas_Productivas, Plantas_No_Productivas);
        """,
        """
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DimGeo_Catalogo_Performance' AND object_id = OBJECT_ID('Silver.Dim_Geografia'))
        CREATE NONCLUSTERED INDEX IX_DimGeo_Catalogo_Performance 
        ON Silver.Dim_Geografia (ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo, Es_Vigente);
        """
    ]
    
    with engine.begin() as conn:
        for sql in indices:
            print(f"Ejecutando: {sql.strip().splitlines()[1]}")
            conn.execute(text(sql))
            print("OK.")
            
    print("\n✅ Todos los índices han sido procesados.")
except Exception as e:
    print(f"❌ Error: {e}")
