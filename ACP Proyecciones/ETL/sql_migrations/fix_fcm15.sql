-- =============================================================================
-- Arreglo de Homologación para FCM15-005
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

PRINT 'Actualizando diccionario de homologación para FCM15-005 (2022) y (2023)...';

UPDATE MDM.Diccionario_Homologacion
SET Valor_Canonico = 'FCM15 - 005',
    Aprobado_Por = 'AUTOMATICO_ETL'
WHERE Texto_Crudo LIKE '%FCM15-005%';

PRINT 'Registros actualizados: ' + CAST(@@ROWCOUNT AS VARCHAR(10));
GO
