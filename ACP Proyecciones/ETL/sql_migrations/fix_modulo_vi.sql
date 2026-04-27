-- =============================================================================
-- Arreglo de Regla MDM para el Módulo 'VI'
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

PRINT 'Actualizando Regla MDM para el modulo VI...';

UPDATE MDM.Regla_Modulo_Raw
SET Modulo_Int = 6,
    Fecha_Modificacion = SYSDATETIME()
WHERE Modulo_Raw = 'VI';

PRINT 'Registros actualizados: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO
