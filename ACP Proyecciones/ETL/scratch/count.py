import os
import sys
sys.path.append(os.getcwd())
from config.conexion import obtener_engine
from sqlalchemy import text
engine = obtener_engine()
with engine.connect() as conn:
    print('Rows in Bronce.Tasa_Crecimiento_Brotes:', conn.execute(text("SELECT COUNT(*) FROM Bronce.Tasa_Crecimiento_Brotes WHERE Estado_Carga = 'CARGADO'")).scalar())
