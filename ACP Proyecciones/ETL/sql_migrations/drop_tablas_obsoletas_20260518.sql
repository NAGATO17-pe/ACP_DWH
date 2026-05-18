-- =============================================================================
-- drop_tablas_obsoletas_20260518.sql
-- =============================================================================
-- DESTRUCTIVO. Revisar antes de ejecutar.
--
-- Borra:
--   - Silver.Dim_Geografia_Nueva  (+ vista y FK dependientes)
--   - Gold.Mart_Fenologia
--   - Gold.Mart_Maduracion
--   - Gold.Mart_Tasa_Crecimiento
--   - Gold.Mart_Peladas
--
-- NO toca: Silver.Dim_Geografia (legacy monolitica, sigue siendo el target de
-- las FKs de las facts segun fase28). Catalogos Dim_*_Catalogo se preservan.
-- =============================================================================

SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- -----------------------------------------------------------------------------
-- 1. Vista emuladora que depende de Dim_Geografia_Nueva
-- -----------------------------------------------------------------------------
IF OBJECT_ID('Silver.vDim_Geografia', 'V') IS NOT NULL
BEGIN
    DROP VIEW Silver.vDim_Geografia;
    PRINT 'DROP VIEW Silver.vDim_Geografia';
END;
GO

-- -----------------------------------------------------------------------------
-- 2. FK entrantes a Silver.Dim_Geografia_Nueva (Bridge_Geografia_Cama, etc.)
--    Genera y ejecuta los DROP CONSTRAINT dinamicamente para no fallar si
--    el nombre del FK cambia en el futuro.
-- -----------------------------------------------------------------------------
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql = @sql + N'ALTER TABLE ' + QUOTENAME(s.name) + N'.' + QUOTENAME(t.name)
                   + N' DROP CONSTRAINT ' + QUOTENAME(fk.name) + N';' + CHAR(10)
FROM sys.foreign_keys fk
JOIN sys.tables  t ON t.object_id = fk.parent_object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE fk.referenced_object_id = OBJECT_ID('Silver.Dim_Geografia_Nueva');

IF @sql <> N''
BEGIN
    PRINT 'Dropping FK entrantes a Dim_Geografia_Nueva:';
    PRINT @sql;
    EXEC sp_executesql @sql;
END;
GO

-- -----------------------------------------------------------------------------
-- 3. Tabla Silver.Dim_Geografia_Nueva
-- -----------------------------------------------------------------------------
IF OBJECT_ID('Silver.Dim_Geografia_Nueva', 'U') IS NOT NULL
BEGIN
    DROP TABLE Silver.Dim_Geografia_Nueva;
    PRINT 'DROP TABLE Silver.Dim_Geografia_Nueva';
END;
GO

-- -----------------------------------------------------------------------------
-- 4. Marts Gold
-- -----------------------------------------------------------------------------
IF OBJECT_ID('Gold.Mart_Fenologia',       'U') IS NOT NULL DROP TABLE Gold.Mart_Fenologia;
IF OBJECT_ID('Gold.Mart_Maduracion',      'U') IS NOT NULL DROP TABLE Gold.Mart_Maduracion;
IF OBJECT_ID('Gold.Mart_Tasa_Crecimiento','U') IS NOT NULL DROP TABLE Gold.Mart_Tasa_Crecimiento;
IF OBJECT_ID('Gold.Mart_Peladas',         'U') IS NOT NULL DROP TABLE Gold.Mart_Peladas;
PRINT 'DROP TABLE Gold.Mart_Fenologia / Maduracion / Tasa_Crecimiento / Peladas';
GO

COMMIT TRANSACTION;
PRINT 'OK: drop_tablas_obsoletas completado.';
GO
