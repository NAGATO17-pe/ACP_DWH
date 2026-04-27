-- =============================================================================
-- Reversión de Regla MDM para el Módulo 'VI'
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT 'Revirtiendo Regla MDM para el modulo VI a su estado original...';

UPDATE MDM.Regla_Modulo_Raw
SET Modulo_Int = NULL,
    Fecha_Modificacion = SYSDATETIME()
WHERE Modulo_Raw = 'VI';

PRINT 'Registros revertidos: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO
