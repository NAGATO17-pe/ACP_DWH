# Bridge global Geografía × Campaña × Condición

**Fecha**: 2026-05-18
**Script**: `ETL/sql_migrations/fase38_bridge_geo_campana_condicion.sql`

## Qué resuelve

Antes de fase38 cada fact resolvía sus FKs por su cuenta:
- `ID_Geografia`: en Python contra `MDM.Catalogo_Geografia` + reglas `MDM.Regla_Modulo_*`.
- `Campana` y `Condicion`: guardadas como texto crudo en `Silver.Fact_Tasa_Crecimiento_Brotes`, sin FK ni validación.

Fase38 introduce una tabla bridge **materializada global** que cualquier fact Silver puede joinar para obtener `(ID_Geografia, ID_Campana, ID_Condicion)` en una pasada, alimentada por un SP central idempotente.

## Objetos creados

| Objeto | Tipo | Propósito |
|---|---|---|
| `Silver.Bridge_Geografia_Campana_Condicion` | Tabla | Grano `(ID_Geografia, ID_Campana, ID_Condicion, Vigencia_Inicio, Vigencia_Fin)`. PK `ID_Bridge`, UNIQUE `Hash_Llave`, IX `(ID_Geografia, Vigencia_Inicio, Vigencia_Fin)`. |
| `MDM.usp_Popular_Bridge_Geo_Campana_Condicion` | SP | Lee `DISTINCT` desde `Silver.Fact_Tasa_Crecimiento_Brotes`, resuelve `ID_Campana` (match por `Nombre_Campana` o por año extraído del string contra `Anio_Cosecha`) y `ID_Condicion` (split `Sustrato/Certificacion`). MERGE idempotente; combinaciones no resueltas a `MDM.Cuarentena` con `Tipo_Regla='CATALOGO'`. Devuelve `(Filas_Insertadas, Filas_Actualizadas, Filas_Cuarentena)`. |
| `Silver.Fact_Tasa_Crecimiento_Brotes` | ALTER | Agrega columnas nullable `ID_Campana INT`, `ID_Condicion INT` + FKs `FK_Fact_TasaCrec_Campana`, `FK_Fact_TasaCrec_Condicion`. Mantiene `Campana`/`Condicion` (texto) como legacy. |
| `MDM.usp_Backfill_FK_Fact_Tasa_Crecimiento` | SP | UPDATE de la fact joineando al bridge por `ID_Geografia` y rango de vigencia. Llena `ID_Campana` / `ID_Condicion` donde estén NULL. Devuelve `Filas_Backfill`. |

## Flujo operativo

1. Cargar/actualizar la fact (loader Python actual — sin cambios).
2. `EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion;` — refresca el bridge.
3. `EXEC MDM.usp_Backfill_FK_Fact_Tasa_Crecimiento;` — propaga FKs a la fact.
4. Revisar `MDM.Cuarentena WHERE Campo_Origen = 'Bridge_GCC'` para combinaciones huérfanas.

Ambos SPs son idempotentes y re-ejecutables.

## Verificación

```sql
-- 1. Smoke DDL
SELECT name FROM sys.tables WHERE name = 'Bridge_Geografia_Campana_Condicion';
SELECT name FROM sys.procedures WHERE name IN
    ('usp_Popular_Bridge_Geo_Campana_Condicion', 'usp_Backfill_FK_Fact_Tasa_Crecimiento');

-- 2. Populación
EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion;

-- 3. Cobertura: filas de la fact sin bridge resuelto
SELECT COUNT(*) AS sin_bridge
FROM Silver.Fact_Tasa_Crecimiento_Brotes f
LEFT JOIN Silver.Bridge_Geografia_Campana_Condicion b
       ON b.ID_Geografia = f.ID_Geografia
      AND f.Fecha_Evento BETWEEN b.Vigencia_Inicio AND ISNULL(b.Vigencia_Fin,'9999-12-31')
WHERE b.ID_Bridge IS NULL;

-- 4. Backfill
EXEC MDM.usp_Backfill_FK_Fact_Tasa_Crecimiento;

-- 5. % de cobertura post-backfill
SELECT
    COUNT(*)                              AS total,
    SUM(CASE WHEN ID_Campana   IS NULL THEN 1 ELSE 0 END) AS sin_campana,
    SUM(CASE WHEN ID_Condicion IS NULL THEN 1 ELSE 0 END) AS sin_condicion
FROM Silver.Fact_Tasa_Crecimiento_Brotes
WHERE Estado_DQ = 'OK';

-- 6. Cuarentena
SELECT TOP 50 *
FROM MDM.Cuarentena
WHERE Campo_Origen = 'Bridge_GCC'
ORDER BY Fecha_Ingreso DESC;
```

Meta de cuarentena: < 5% del total. Si se excede, revisar valores raw de `Condicion` y `Campana` y ajustar `Dim_Condicion_Cultivo` o `Dim_Campana` antes de re-ejecutar.

## Extensión a otras facts

El SP poblador hoy lee solo de `Silver.Fact_Tasa_Crecimiento_Brotes`. Para incorporar otra fact (cuando tenga `ID_Geografia`, `Campana` y `Condicion` o equivalentes):

1. Agregar `UNION ALL` al CTE `Combinaciones` dentro de `MDM.usp_Popular_Bridge_Geo_Campana_Condicion`.
2. Crear su propio `usp_Backfill_FK_<Fact>` con el mismo patrón de UPDATE.

## Decisiones / riesgos

- **Grano del bridge = Geografía completa** (no solo Módulo). Multiplica filas vs. `Bridge_Modulo_Campana` legacy; mantener vigilado el tamaño.
- **Parsing de `Condicion_Raw`** asume separador `/` (ej. `COCO/ORGANICO`). Strings sin `/` o sin match en `Dim_Condicion_Cultivo` → cuarentena.
- **`Dim_Condicion_Cultivo` debe estar poblada** antes de correr el SP. fase38 no la siembra (decisión del usuario).
- **No se toca `Bridge_Modulo_Campana`** (poblado por `Silver.sp_Sincronizar_Periodos_Campana` desde `Fact_Ciclo_Poda`). Coexiste sin conflicto.
- **Loader Python sin cambios**: la propagación de FKs ocurre 100% server-side vía el SP de backfill. Si en el futuro se quiere resolución en tiempo de carga, se puede agregar un `_cargar_bridge_geo_campana_condicion` en `ETL/mdm/lookup.py` siguiendo el patrón de `_cargar_bridge_campanas`.
