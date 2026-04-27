-- =============================================================
-- ROLLBACK DE EMERGENCIA (solo si fuera necesario revertir)
-- Revierte el batch BATCH_VIVERO_2026 ejecutado el 2026-04-27 12:06
-- =============================================================
BEGIN TRAN;

DECLARE @firma NVARCHAR(20) = 'BATCH_VIVERO_2026';

-- R.1 Volver Bronce a RECHAZADO (cuidado: solo si aun NO se ejecuto el ETL Bronce->Silver)
UPDATE b SET b.Estado_Carga='RECHAZADO'
FROM Bronce.Tasa_Crecimiento_Brotes b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Tasa_Crecimiento
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Tasa_Crecimiento_Brotes'
  AND b.Estado_Carga='CARGADO';

UPDATE b SET b.Estado_Carga='RECHAZADO'
FROM Bronce.Evaluacion_Vegetativa b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Evaluacion_Vegetativa
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Evaluacion_Vegetativa'
  AND b.Estado_Carga='CARGADO';

UPDATE b SET b.Estado_Carga='RECHAZADO'
FROM Bronce.Evaluacion_Pesos b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Evaluacion_Pesos
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Evaluacion_Pesos'
  AND b.Estado_Carga='CARGADO';

UPDATE b SET b.Estado_Carga='RECHAZADO'
FROM Bronce.Conteo_Fruta b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Conteo_Fruta
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Conteo_Fruta'
  AND b.Estado_Carga='CARGADO';

-- R.2 Revertir cuarentena a PENDIENTE
UPDATE MDM.Cuarentena
SET Estado='PENDIENTE',
    Valor_Corregido=NULL,
    Aprobado_Por=NULL,
    Fecha_Resolucion=NULL
WHERE Aprobado_Por=@firma;

-- R.3 Revertir reglas
DELETE FROM MDM.Regla_Modulo_Raw WHERE Modulo_Raw='VIVERO';
UPDATE MDM.Regla_Modulo_Raw
SET Modulo_Int=NULL, Fecha_Modificacion=GETDATE(),
    Observacion='Canonica Fase 15: VI => TEST_BLOCK'
WHERE Modulo_Raw='VI';

-- COMMIT solo si verificas que todo se revirtio correctamente
-- COMMIT;
ROLLBACK;  -- por defecto rollback, descomentar COMMIT si realmente quieres revertir
