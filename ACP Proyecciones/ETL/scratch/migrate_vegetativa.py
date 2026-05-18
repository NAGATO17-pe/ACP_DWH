import sys
from pathlib import Path

# Add project root to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.conexion import obtener_engine
from sqlalchemy import text

def run_migration():
    engine = obtener_engine()
    print("Database connection successfully obtained.")
    
    with engine.begin() as conn:
        # 1. Check if the table Silver.Fact_Evaluacion_Vegetativa already exists and if it hasn't been renamed yet
        table_exists = conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa'
        """)).fetchone()
        
        has_floracion_table = conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa_Floracion'
        """)).fetchone()
        
        if table_exists and not has_floracion_table:
            # Let's double check if it is the flowering table (contains Cantidad_Plantas_en_Floracion)
            has_floracion_col = conn.execute(text("""
                SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa' 
                  AND COLUMN_NAME = 'Cantidad_Plantas_en_Floracion'
            """)).fetchone()
            
            if has_floracion_col:
                print("Renaming existing Fact_Evaluacion_Vegetativa to Fact_Evaluacion_Vegetativa_Floracion...")
                conn.execute(text("EXEC sp_rename 'Silver.Fact_Evaluacion_Vegetativa', 'Fact_Evaluacion_Vegetativa_Floracion'"))
                print("Table renamed successfully.")
                
                # Now rename the primary key column ID_Fact_Evaluacion_Vegetativa to ID_Fact_Evaluacion_Vegetativa_Floracion
                print("Renaming primary key column...")
                conn.execute(text("EXEC sp_rename 'Silver.Fact_Evaluacion_Vegetativa_Floracion.ID_Fact_Evaluacion_Vegetativa', 'ID_Fact_Evaluacion_Vegetativa_Floracion', 'COLUMN'"))
                print("Primary key column renamed successfully.")
                
                # Re-create index or drop old one if exists
                conn.execute(text("""
                    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Fact_EvalVeg_Grain' AND object_id = OBJECT_ID('Silver.Fact_Evaluacion_Vegetativa_Floracion'))
                        DROP INDEX UX_Fact_EvalVeg_Grain ON Silver.Fact_Evaluacion_Vegetativa_Floracion;
                """))
                conn.execute(text("""
                    CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_EvalVegFloracion_Grain
                        ON Silver.Fact_Evaluacion_Vegetativa_Floracion (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion);
                """))
                print("Unique index on Fact_Evaluacion_Vegetativa_Floracion created successfully.")
        else:
            print("Existing Fact_Evaluacion_Vegetativa has already been renamed or does not exist.")

        # 2. Create the new physical Silver.Fact_Evaluacion_Vegetativa table
        if not conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa'
        """)).fetchone():
            print("Creating new physical Fact_Evaluacion_Vegetativa table...")
            conn.execute(text("""
                CREATE TABLE Silver.Fact_Evaluacion_Vegetativa (
                    ID_Fact_Evaluacion_Vegetativa BIGINT IDENTITY(1,1) PRIMARY KEY,
                    ID_Geografia            INT             NOT NULL REFERENCES Silver.Dim_Geografia(ID_Geografia),
                    ID_Tiempo               INT             NOT NULL REFERENCES Silver.Dim_Tiempo(ID_Tiempo),
                    ID_Variedad             INT             NOT NULL REFERENCES Silver.Dim_Variedad(ID_Variedad),
                    Semanas_Despues_Poda    INT             NULL,
                    Promedio_Altura         DECIMAL(8,2)    NULL,
                    Promedio_Tallos_Basales DECIMAL(8,2)    NULL,
                    Promedio_Tallos_Basales_Nuevos DECIMAL(8,2) NULL,
                    Promedio_Brotes_Generales   DECIMAL(8,2) NULL,
                    Promedio_Brotes_Productivos DECIMAL(8,2) NULL,
                    Promedio_Diametro_Brote DECIMAL(8,2)    NULL,
                    Fecha_Evento            DATETIME2       NOT NULL,
                    Fecha_Sistema           DATETIME2       NOT NULL DEFAULT GETDATE(),
                    Estado_DQ               NVARCHAR(20)    NOT NULL DEFAULT 'Aprobado',
                    ID_Campana              INT             NULL REFERENCES Silver.Dim_Campana(ID_Campana)
                );
            """))
            conn.execute(text("""
                CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_EvalVeg_Grain
                    ON Silver.Fact_Evaluacion_Vegetativa (ID_Geografia, ID_Tiempo, ID_Variedad);
            """))
            print("Physical Fact_Evaluacion_Vegetativa table created successfully with unique index.")
        else:
            print("Physical Fact_Evaluacion_Vegetativa table already exists.")

        # 3. Alter Fisiologia tables to add Valores_Raw and Aux
        print("Checking Fisiologia tables...")
        # Bronce.Fisiologia Valores_Raw
        has_valores_raw = conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'Bronce' AND TABLE_NAME = 'Fisiologia' AND COLUMN_NAME = 'Valores_Raw'
        """)).fetchone()
        if not has_valores_raw:
            print("Adding Valores_Raw to Bronce.Fisiologia...")
            conn.execute(text("ALTER TABLE Bronce.Fisiologia ADD Valores_Raw NVARCHAR(MAX) NULL;"))
            print("Added Valores_Raw to Bronce.Fisiologia successfully.")
        else:
            print("Valores_Raw already exists in Bronce.Fisiologia.")

        # Silver.Fact_Fisiologia Aux
        has_aux = conn.execute(text("""
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Fisiologia' AND COLUMN_NAME = 'Aux'
        """)).fetchone()
        if not has_aux:
            print("Adding Aux to Silver.Fact_Fisiologia...")
            conn.execute(text("ALTER TABLE Silver.Fact_Fisiologia ADD Aux NVARCHAR(255) NULL;"))
            print("Added Aux to Silver.Fact_Fisiologia successfully.")
        else:
            print("Aux already exists in Silver.Fact_Fisiologia.")
            
    print("Migration finished successfully.")

if __name__ == "__main__":
    run_migration()
