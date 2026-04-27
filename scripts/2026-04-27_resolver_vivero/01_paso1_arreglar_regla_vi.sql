-- =============================================================
-- Fase 16 / 2026-04-27 12:05 — Resolver cuarentena VIVERO/VI
-- PASO 1: Arreglar regla VI (Modulo_Int=NULL -> -1)
-- Ejecutado por agente Claude Code contra LCP-PAG-PRACTIC
-- =============================================================
UPDATE MDM.Regla_Modulo_Raw
SET Modulo_Int = -1,
    Tipo_Conduccion = 'TEST_BLOCK',
    Es_Test_Block = 1,
    Es_Activa = 1,
    Fecha_Modificacion = GETDATE(),
    Observacion = 'Fase 16: VI -> Modulo=-1 (TEST_BLOCK canonico)'
WHERE Modulo_Raw = 'VI';
-- Filas afectadas: 1
