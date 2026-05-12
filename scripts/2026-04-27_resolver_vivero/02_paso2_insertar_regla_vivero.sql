-- =============================================================
-- Fase 16 / 2026-04-27 12:06 — Resolver cuarentena VIVERO/VI
-- PASO 2: Insertar regla VIVERO (no existia)
-- Ejecutado por agente Claude Code contra LCP-PAG-PRACTIC
-- =============================================================
INSERT INTO MDM.Regla_Modulo_Raw
  (Modulo_Raw, Modulo_Int, SubModulo_Int, Tipo_Conduccion, Es_Test_Block, Es_Activa, Fecha_Creacion, Observacion)
VALUES
  ('VIVERO', -1, NULL, 'TEST_BLOCK', 1, 1, GETDATE(), 'Fase 16: VIVERO -> Modulo=-1 (TEST_BLOCK)');
-- Filas afectadas: 1, ID_Regla_Modulo asignado: 17
