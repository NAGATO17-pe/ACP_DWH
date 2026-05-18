import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    conn.execute(text("""
    IF OBJECT_ID('Silver.Fact_Censo_Plantas', 'U') IS NULL
    BEGIN
        CREATE TABLE Silver.Fact_Censo_Plantas (
            ID_Censo INT IDENTITY(1,1) PRIMARY KEY,
            ID_Geografia INT NOT NULL,
            ID_Variedad INT NOT NULL,
            ID_Tiempo INT NOT NULL,
            Cantidad_Plantas FLOAT,
            Area_ha FLOAT,
            Fecha_Sistema DATETIME2 DEFAULT SYSDATETIME(),
            Estado_DQ NVARCHAR(50) DEFAULT 'OK'
        )
    END
    """))
    conn.commit()
print("Tabla Silver.Fact_Censo_Plantas verificada/creada.")
