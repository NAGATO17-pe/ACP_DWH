-- =============================================================
-- Fase 16 / 2026-04-27 12:06 — Resolver cuarentena VIVERO/VI
-- PASO 4: Transaccion atomica (firma=BATCH_VIVERO_2026)
-- Resultado: 4410 cuarentena RESUELTA + 4410 Bronce CARGADO
-- =============================================================
BEGIN TRAN;

DECLARE @firma NVARCHAR(20) = 'BATCH_VIVERO_2026';

-- 4.1 Resolver cuarentena
UPDATE MDM.Cuarentena
SET Estado='RESUELTO',
    Valor_Corregido='VIVERO_M_-1_TESTBLOCK',
    Aprobado_Por=@firma,
    Fecha_Resolucion=GETDATE()
WHERE Estado='PENDIENTE' AND Tipo_Regla='MDM'
  AND (Valor_Recibido LIKE '%Modulo=VIVERO %'
    OR Valor_Recibido LIKE '%Modulo=VI %');
-- Esperado: 4410

-- 4.2 Reinyectar Bronce.Tasa_Crecimiento_Brotes (esperado: 3751)
UPDATE b SET b.Estado_Carga='CARGADO'
FROM Bronce.Tasa_Crecimiento_Brotes b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Tasa_Crecimiento
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Tasa_Crecimiento_Brotes'
  AND b.Estado_Carga='RECHAZADO';

-- 4.3 Reinyectar Bronce.Evaluacion_Vegetativa (esperado: 360)
UPDATE b SET b.Estado_Carga='CARGADO'
FROM Bronce.Evaluacion_Vegetativa b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Evaluacion_Vegetativa
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Evaluacion_Vegetativa'
  AND b.Estado_Carga='RECHAZADO';

-- 4.4 Reinyectar Bronce.Evaluacion_Pesos (esperado: 233)
UPDATE b SET b.Estado_Carga='CARGADO'
FROM Bronce.Evaluacion_Pesos b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Evaluacion_Pesos
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Evaluacion_Pesos'
  AND b.Estado_Carga='RECHAZADO';

-- 4.5 Reinyectar Bronce.Conteo_Fruta (esperado: 66)
UPDATE b SET b.Estado_Carga='CARGADO'
FROM Bronce.Conteo_Fruta b
INNER JOIN MDM.Cuarentena q ON CAST(q.ID_Registro_Origen AS BIGINT) = b.ID_Conteo_Fruta
WHERE q.Aprobado_Por=@firma
  AND q.Tabla_Origen='Bronce.Conteo_Fruta'
  AND b.Estado_Carga='RECHAZADO';

COMMIT;
