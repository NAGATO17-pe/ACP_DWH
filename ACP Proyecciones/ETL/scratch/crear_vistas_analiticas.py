import sys
from pathlib import Path

# Add project root to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.conexion import obtener_engine
from sqlalchemy import text

# DDL queries for the analytical views
views_ddl = {
    "Silver.vFact_Conteo_Fenologico": """
        CREATE OR ALTER VIEW Silver.vFact_Conteo_Fenologico AS
        SELECT 
            f.ID_Conteo_Fenologico,
            f.Fecha_Evento,
            f.Fecha_Registro,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            f.Punto,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            est.Nombre_Estado AS Estado_Fenologico,
            f.Cantidad_Organos,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Conteo_Fenologico f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana
        LEFT JOIN Silver.Dim_Estado_Fenologico est ON f.ID_Estado_Fenologico = est.ID_Estado_Fenologico;
    """,
    "Silver.vFact_Floracion": """
        CREATE OR ALTER VIEW Silver.vFact_Floracion AS
        SELECT 
            f.ID_Fact_Floracion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Cantidad_Plantas_Evaluadas,
            f.Cantidad_Plantas_en_Floracion,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Floracion f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    "Silver.vFact_Evaluacion_Vegetativa": """
        CREATE OR ALTER VIEW Silver.vFact_Evaluacion_Vegetativa AS
        SELECT 
            f.ID_Fact_Evaluacion_Vegetativa,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Semanas_Despues_Poda,
            f.Promedio_Altura,
            f.Promedio_Tallos_Basales,
            f.Promedio_Tallos_Basales_Nuevos,
            f.Promedio_Brotes_Generales,
            f.Promedio_Brotes_Productivos,
            f.Promedio_Diametro_Brote,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Evaluacion_Vegetativa f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    "Silver.vFact_Evaluacion_Pesos": """
        CREATE OR ALTER VIEW Silver.vFact_Evaluacion_Pesos AS
        SELECT 
            f.ID_Evaluacion_Pesos,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Peso_Promedio_Baya_g,
            f.Cantidad_Bayas_Muestra,
            f.Peso_Proyectado_Baya_g,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Evaluacion_Pesos f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    "Silver.vFact_Tasa_Crecimiento_Brotes": """
        CREATE OR ALTER VIEW Silver.vFact_Tasa_Crecimiento_Brotes AS
        SELECT 
            f.ID_Tasa_Crecimiento_Brotes,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Condicion,
            f.Estado_Vegetativo,
            f.Tipo_Tallo,
            f.Codigo_Ensayo,
            f.Codigo_Origen,
            f.Campana AS Campana_Origen,
            f.Observacion,
            f.Fecha_Poda_Aux,
            f.Dias_Desde_Poda,
            f.Medida_Crecimiento,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    "Silver.vFact_Induccion_Floral": """
        CREATE OR ALTER VIEW Silver.vFact_Induccion_Floral AS
        SELECT 
            f.ID_Induccion_Floral,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Codigo_Consumidor,
            f.Cantidad_Plantas_Por_Cama,
            f.Cantidad_Plantas_Con_Induccion,
            f.Cantidad_Brotes_Con_Induccion,
            f.Cantidad_Brotes_Totales,
            f.Cantidad_Brotes_Con_Flor,
            f.Pct_Plantas_Con_Induccion,
            f.Pct_Brotes_Con_Induccion,
            f.Pct_Brotes_Con_Flor,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Induccion_Floral f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """
}

def crear_vistas():
    engine = obtener_engine()
    with engine.begin() as conn:
        for nombre, ddl in views_ddl.items():
            print(f"Creating/updating View: {nombre}...")
            conn.execute(text(ddl))
            print(f"View {nombre} created successfully.")

if __name__ == "__main__":
    crear_vistas()
