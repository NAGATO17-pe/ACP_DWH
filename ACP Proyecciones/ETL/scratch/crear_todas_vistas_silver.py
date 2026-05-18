import sys
from pathlib import Path

# Add project root to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.conexion import obtener_engine
from sqlalchemy import text

views_ddl = {
    # 1. Conteo Fenológico
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
            f.Plantas_Productivas,
            f.Plantas_No_Productivas,
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
    # 2. Evaluación de Floración
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
    # 2b. Evaluación Vegetativa (Física)
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
    # 3. Evaluación de Pesos
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
    # 4. Tasa Crecimiento Brotes
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
    # 5. Inducción Floral
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
    """,
    # 6. Ciclo Poda
    "Silver.vFact_Ciclo_Poda": """
        CREATE OR ALTER VIEW Silver.vFact_Ciclo_Poda AS
        SELECT 
            f.ID_Poda,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            f.Punto,
            var.Nombre_Variedad AS Variedad,
            f.Tipo_Evaluacion,
            f.Tallos_Planta,
            f.Longitud_Tallo,
            f.Diametro_Tallo,
            f.Ramilla_Planta,
            f.Tocones_Planta,
            f.Cortes_Defectuosos,
            f.Altura_Poda,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Ciclo_Poda f
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
    # 7. Cosecha SAP
    "Silver.vFact_Cosecha_SAP": """
        CREATE OR ALTER VIEW Silver.vFact_Cosecha_SAP AS
        SELECT 
            f.ID_Cosecha_SAP,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            cond.Sustrato AS Condicion_Sustrato,
            cond.Certificacion AS Condicion_Certificacion,
            f.Kg_Brutos,
            f.Kg_Neto_MP,
            f.Cantidad_Jabas,
            f.Lote,
            f.Almacen,
            f.Doc_Remision,
            f.Codigo_Cliente,
            f.Responsable,
            f.Descripcion_Material,
            f.Codigo_SAP_Material,
            f.Fecha_Recepcion,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Cosecha_SAP f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cond ON f.ID_Condicion_Cultivo = cond.ID_Condicion
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    # 8. Maduración
    "Silver.vFact_Maduracion": """
        CREATE OR ALTER VIEW Silver.vFact_Maduracion AS
        SELECT 
            f.ID_Maduracion,
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
            est.Nombre_Estado AS Estado_Fenologico,
            cinta.Color_Cinta AS Color_Cinta,
            f.ID_Organo,
            f.Dias_Pasados_Del_Marcado,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Maduracion f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Estado_Fenologico est ON f.ID_Estado_Fenologico = est.ID_Estado_Fenologico
        LEFT JOIN Silver.Dim_Cinta cinta ON f.ID_Cinta = cinta.ID_Cinta
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    # 9. Peladas
    "Silver.vFact_Peladas": """
        CREATE OR ALTER VIEW Silver.vFact_Peladas AS
        SELECT 
            f.ID_Peladas,
            f.Fecha_Evento,
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
            f.Botones_Florales,
            f.Flores,
            f.Bayas_Pequenas,
            f.Bayas_Grandes,
            f.Fase_1,
            f.Fase_2,
            f.Bayas_Cremas,
            f.Bayas_Maduras,
            f.Bayas_Cosechables,
            f.Plantas_Productivas,
            f.Plantas_No_Productivas,
            f.Muestras,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Peladas f
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
    # 10. Telemetría Clima
    "Silver.vFact_Telemetria_Clima": """
        CREATE OR ALTER VIEW Silver.vFact_Telemetria_Clima AS
        SELECT 
            f.ID_Telemetria_Clima,
            f.Fecha_Evento,
            f.Sector_Climatico,
            f.Temperatura_Max_C,
            f.Temperatura_Min_C,
            f.Humedad_Relativa_Pct,
            f.Precipitacion_mm,
            f.VPD,
            f.Radiacion_Solar,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Telemetria_Clima f
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    # 11. Tareo
    "Silver.vFact_Tareo": """
        CREATE OR ALTER VIEW Silver.vFact_Tareo AS
        SELECT 
            f.ID_Tareo,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            per.Nombre_Completo AS Colaborador,
            per.DNI AS Colaborador_DNI,
            sup.Nombre_Completo AS Supervisor,
            sup.DNI AS Supervisor_DNI,
            act.Nombre_Actividad AS Actividad_Operativa,
            f.Horas_Trabajadas,
            f.ID_Planilla,
            f.Es_Observado_SAP,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Tareo f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Personal sup ON f.ID_Personal_Supervisor = sup.ID_Personal
        LEFT JOIN Silver.Dim_Actividad_Operativa act ON f.ID_Actividad_Operativa = act.ID_Actividad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    # 12. Fisiología
    "Silver.vFact_Fisiologia": """
        CREATE OR ALTER VIEW Silver.vFact_Fisiologia AS
        SELECT 
            f.ID_Fisiologia,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Tercio,
            f.Brotes_Productivos,
            f.Brotes_Vegetativos,
            f.Hinchadas,
            f.Productivas,
            f.Total_Organos,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Fisiologia f
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
    # 13. Áreas Plantas
    "Silver.vFact_areas_plantas": """
        CREATE OR ALTER VIEW Silver.vFact_areas_plantas AS
        SELECT 
            f.ID_Censo,
            t.Fecha AS Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            cond.Sustrato AS Condicion_Sustrato,
            cond.Certificacion AS Condicion_Certificacion,
            f.Cantidad_Plantas,
            f.Area_ha,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_areas_plantas f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cond ON f.ID_Condicion = cond.ID_Condicion
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """,
    # 14. Censo Plantas
    "Silver.vFact_Censo_Plantas": """
        CREATE OR ALTER VIEW Silver.vFact_Censo_Plantas AS
        SELECT 
            f.ID_Censo,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Plantas_Buenas,
            f.Plantas_Regulares,
            f.Plantas_Malas,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Censo_Plantas f
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
    # 15. Proyecciones
    "Silver.vFact_Proyecciones": """
        CREATE OR ALTER VIEW Silver.vFact_Proyecciones AS
        SELECT 
            f.ID_Proyeccion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            esc.Tipo_Escenario AS Escenario_Proyeccion,
            esc.Descripcion AS Escenario_Descripcion,
            wk.Estado AS Estado_Workflow,
            f.Kg_Proyectados,
            f.Kg_Pesimista,
            f.Kg_Optimista,
            f.Pct_Maduracion,
            f.Pct_Productivas,
            f.MAPE,
            f.Version_Modelo,
            f.Fecha_Cutoff,
            f.ID_Version_Datos,
            f.Flag_Override,
            f.Motivo_Override,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Proyecciones f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Escenario_Proyeccion esc ON f.ID_Escenario = esc.ID_Escenario
        LEFT JOIN Silver.Dim_Estado_Workflow wk ON f.ID_Estado_Workflow = wk.ID_Workflow
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
    """
}

def crear_todas_vistas():
    engine = obtener_engine()
    with engine.begin() as conn:
        for nombre, ddl in views_ddl.items():
            print(f"Creating/updating View: {nombre}...")
            try:
                conn.execute(text(ddl))
                print(f"View {nombre} created successfully.")
            except Exception as e:
                print(f"FAILED on {nombre}: {e}")
                raise e
    print("\nAll 15 Silver analytical views have been created and verified successfully!")

if __name__ == "__main__":
    crear_todas_vistas()
