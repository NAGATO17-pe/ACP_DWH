-- ============================================================
-- Parámetros Six-Week Projection
-- ACP DWH — Config.Parametros_Pipeline
-- Ejecutar una sola vez para registrar los parámetros.
-- MERGE garantiza idempotencia.
-- ============================================================

MERGE Config.Parametros_Pipeline AS dest
USING (VALUES
    ('PROY_SIXWEEK_MARGEN_PESIMISTA',  '0.9906',  'Factor de ajuste pesimista para proyección Six-Week',  'sixweek', 'DECIMAL'),
    ('PROY_SIXWEEK_MARGEN_OPTIMISTA',  '1.0107',  'Factor de ajuste optimista para proyección Six-Week',  'sixweek', 'DECIMAL'),
    ('PROY_SIXWEEK_ID_ESCENARIO_BASE', '4',        'ID del escenario base en Silver.Dim_Escenario_Proyeccion', 'sixweek', 'INT'),
    ('PROY_SIXWEEK_SEMANAS_HISTORICO', '4',        'Ventana de semanas históricas para calcular kg_base', 'sixweek', 'INT')
) AS src (Clave, Valor, Descripcion, Modulo, Tipo_Dato)
ON dest.Clave = src.Clave
WHEN MATCHED THEN
    UPDATE SET
        dest.Valor       = src.Valor,
        dest.Descripcion = src.Descripcion
WHEN NOT MATCHED BY TARGET THEN
    INSERT (Clave, Valor, Descripcion, Modulo, Tipo_Dato)
    VALUES (src.Clave, src.Valor, src.Descripcion, src.Modulo, src.Tipo_Dato);

SELECT Clave, Valor, Descripcion, Modulo
FROM Config.Parametros_Pipeline
WHERE Modulo = 'sixweek'
ORDER BY Clave;
