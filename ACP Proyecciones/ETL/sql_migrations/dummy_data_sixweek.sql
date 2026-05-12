-- Poblar con datos ficticios para probar el Six-Week Projection
-- Ventana: Abril 2026

DECLARE @ID_Campana INT = 3;
DECLARE @Fecha_Sistema DATETIME2 = SYSDATETIME();

-- 1. Silver.Fact_Cosecha_SAP (para kg_base)
INSERT INTO Silver.Fact_Cosecha_SAP (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Condicion_Cultivo, Kg_Brutos, Kg_Neto_MP, Cantidad_Jabas, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
VALUES 
(1, 20260410, 89, 1, 1500, 1400, 50, '2026-04-10', @Fecha_Sistema, 'OK', @ID_Campana),
(1, 20260417, 89, 1, 1600, 1500, 55, '2026-04-17', @Fecha_Sistema, 'OK', @ID_Campana),
(2, 20260410, 7, 1, 2000, 1900, 70, '2026-04-10', @Fecha_Sistema, 'OK', @ID_Campana),
(2, 20260417, 7, 1, 2100, 2000, 75, '2026-04-17', @Fecha_Sistema, 'OK', @ID_Campana),
(3, 20260410, 32, 1, 1200, 1100, 40, '2026-04-10', @Fecha_Sistema, 'OK', @ID_Campana);

-- 2. Silver.Fact_Maduracion (para pct_maduracion)
-- Necesitamos varios organos por combinacion para que el porcentaje sea significativo
INSERT INTO Silver.Fact_Maduracion (ID_Personal, ID_Geografia, ID_Tiempo, ID_Variedad, ID_Estado_Fenologico, ID_Cinta, ID_Organo, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
SELECT 1, G, T, V, E, 1, O, CAST(CAST(T AS NVARCHAR) AS DATE), @Fecha_Sistema, 'OK', @ID_Campana
FROM (VALUES (1, 20260420, 89), (2, 20260420, 7), (3, 20260420, 32)) AS Base(G, T, V)
CROSS JOIN (VALUES (8), (8), (9), (4)) AS Est(E) -- 3 maduros/cosechables de 4 = 75%
CROSS JOIN (VALUES (1), (2), (3), (4), (5)) AS Org(O);

-- 3. Silver.Fact_Peladas (para pct_productivas)
INSERT INTO Silver.Fact_Peladas (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Punto, Plantas_Productivas, Plantas_No_Productivas, Muestras, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
VALUES 
(1, 20260420, 89, 1, 1, 45, 5, 50, '2026-04-20', @Fecha_Sistema, 'OK', @ID_Campana),
(2, 20260420, 7, 1, 1, 48, 2, 50, '2026-04-20', @Fecha_Sistema, 'OK', @ID_Campana),
(3, 20260420, 32, 1, 1, 40, 10, 50, '2026-04-20', @Fecha_Sistema, 'OK', @ID_Campana);
