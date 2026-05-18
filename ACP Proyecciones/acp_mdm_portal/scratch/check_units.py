import os
from sqlalchemy import text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.abspath("."))

try:
    from utils.db import obtener_engine
    engine = obtener_engine()
    with engine.connect() as conn:
        # Get the latest date
        date_res = conn.execute(text("SELECT MAX(ID_Tiempo) FROM Silver.Fact_Conteo_Fenologico")).fetchone()
        latest_date = date_res[0]
        
        # Count units
        query = f"""
        SELECT COUNT(DISTINCT CONCAT(g.ID_Modulo_Catalogo, t.Turno, v_val.Valvula, f.ID_Variedad))
        FROM Silver.Fact_Conteo_Fenologico f
        JOIN Silver.Dim_Geografia g ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v_val ON g.ID_Valvula_Catalogo = v_val.ID_Valvula_Catalogo
        WHERE f.ID_Tiempo = {latest_date}
        """
        count_res = conn.execute(text(query)).fetchone()
        print(f"Latest Date: {latest_date}")
        print(f"Number of units: {count_res[0]}")
except Exception as e:
    print(f"Error: {e}")
