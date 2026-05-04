# PLAN DE NORMALIZACIÓN — MÓDULO ERRORES OPERATIVOS

## ACP DWH Geographic Phenology | Investigación Completada

---

## 1. TIPOS DE ERROR: ANÁLISIS Y DECISIÓN

### 1.1 Estado Actual (12 variantes)

| Tipo de Error | Registros | Evaluación Dominante | Punto Medio | ACCIÓN |
|---|---|---|---|---|
| **Digitación** | 1,229 | Fenología (43%) + Conteo (41%) | 2.4 | ✓ MANTENER |
| **Fuera de fecha** | 301 | Conteo (40%) + Ciclos (31%) | 9.7 | ✓ MANTENER |
| **Tipo de evaluación** | 141 | Conteo (54%) + Floración (40%) | 6.2 | ✓ MANTENER |
| **Consumidor** | 125 | Conteo (57%) + Fenología (30%) | 4.3 | ✓ MANTENER |
| **Muestra** | 87 | Conteo (97%) | 8.5 | ✓ MANTENER |
| **Incorrecta evaluación** | 32 | Conteo (50%) + Floración (25%) | 3.9 | 🔄 ANALIZAR vs "Digitación" |
| **Dato duplicado** | 31 | Conteo (90%) | 2.8 | 🔄 COMBINAR |
| **Dato vacio** | 25 | Fenología (92%) | 2.8 | 🔄 COMBINAR |
| **Dato Vacio** | 24 | Conteo (88%) | 2.4 | 🔴 **DUPLICADO** (merge con "Dato vacio") |
| **Duplicado** | 12 | Ciclos Fenológicos (100%) | 4.2 | 🔴 **DUPLICADO** (merge con "Dato duplicado") |
| **App desactualizada** | 11 | Conteo (91%) | 7.5 | ✓ MANTENER |
| **Sin corregir** | 10 | Fenología (100%) | 1.5 | ❓ INDEFINIDO (clarificar con ops) |

### 1.2 Decisión Técnica: Catálogo Normalizado en MDM

**Estrategia**: Emplear el patrón *Get or Create* de la capa `mdm` y una validación manual con el área operativa para el catálogo base.

```text
Paso 1: Clustering automático (similitud strings)
- "Dato vacio" + "Dato Vacio" → grupo DATO_VACIO (49 registros)
- "Dato duplicado" + "Duplicado" → grupo DATO_DUPLICADO (43 registros)
- "Incorrecta evaluación" + "Tipo de evaluación" → revisar semántica

Paso 2: Validación manual con equipo operativo
- ¿"Incorrecta evaluación" ≠ "Tipo de evaluación"?
  → "Tipo de evaluación" = elegiste el tipo de evaluación equivocado
  → "Incorrecta evaluación" = hiciste bien la evaluación pero con lógica incorrecta
  → Si son conceptos distintos: MANTENER ambos
  → Si son lo mismo: COMBINAR

Paso 3: Decisión sobre "Sin corregir"
- ¿Es un estado (PENDIENTE/CORREGIDO)?
- ¿Es un tipo de error por sí mismo?
- Necesita clarificación operativa
```

### 1.3 Catálogo Recomendado (8-10 tipos)

Se creará en la capa MDM para gobernar las entradas:

```sql
CREATE TABLE mdm.Catalogo_Tipo_Error (
    ID_Tipo_Error INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Error VARCHAR(50) UNIQUE,
    Descripcion VARCHAR(255),
    Severidad_Base INT -- Peso por defecto (Puntos)
);

-- Ejemplos propuestos:
-- 1. DIGITACION_NUMERICA (Error al ingresar un número)
-- 2. DATO_VACIO (Campo obligatorio sin valor)
-- 3. DATO_DUPLICADO (Registro repetido en BD)
-- 4. FUERA_DE_FECHA (Evaluación fuera del período permitido)
-- 5. TIPO_EVALUACION_INCORRECTO (Se eligió tipo de evaluación equivocado)
-- 6. CONSUMIDOR_INVALIDO (Consumidor no existe o es inválido)
-- 7. MUESTRA_INVALIDA (Muestra vencida, dañada o no identificable)
-- 8. INCORRECTA_EVALUACION (Lógica de evaluación aplicada incorrectamente)
-- 9. APP_DESACTUALIZADA (Versión de app no soporta evaluación)
-- 10. ESTADO_PENDIENTE_REVISION (Para los "Sin corregir")


### 1.4 Migración del Histórico: `mdm.homologador`

**Enfoque**: Mapping manual incorporado en las utilidades de limpieza (o tablas de homologación) antes de insertar a `Silver.Fact_Error_Operativo`.

```python
# Diccionario de normalización a integrar en ETL/mdm/homologador.py
MAPA_NORMALIZACION_ERRORES = {
    "digitación": "DIGITACION_NUMERICA",
    "dato vacio": "DATO_VACIO",
    "dato duplicado": "DATO_DUPLICADO",
    "duplicado": "DATO_DUPLICADO",
    "fuera de fecha": "FUERA_DE_FECHA",
    "tipo de evaluación": "TIPO_EVALUACION_INCORRECTO",
    "consumidor": "CONSUMIDOR_INVALIDO",
    "muestra": "MUESTRA_INVALIDA",
    "incorrecta evaluación": "INCORRECTA_EVALUACION",
    "app desactualizada": "APP_DESACTUALIZADA",
    "sin corregir": "ESTADO_PENDIENTE_REVISION",
}

# Lógica general en fact_error_operativo.py:
# df['Observacion_Norm'] = df['Observación'].str.lower().str.strip()
# df['Codigo_Error'] = df['Observacion_Norm'].map(MAPA_NORMALIZACION_ERRORES)
# Luego, obtener ID desde mdm.Catalogo_Tipo_Error usando lookup.py
```

---

## 2. EVALUADORES: NORMALIZACIÓN DE NOMBRES Y DNI

### 2.1 Problema Identificado

Se han detectado **11 DNIs con 2 variantes cada uno** (orden invertido de nombre/apellido). En `ACP_DWH`, el control de personal está unificado en `Silver.Dim_Personal`.

### 2.2 Decisión: Norma de Nomenclatura

**Recomendación**: **APELLIDO, NOMBRE** (estándar en documentos formales peruanos). La dimensión `Dim_Personal` deberá ser la única fuente de la verdad.

### 2.3 Integración en Arquitectura ACP_DWH

**Fase 1: Corrección en Dim_Personal**
Antes de procesar la Fact, debemos asegurar que la `Dim_Personal` tenga un único registro válido por DNI y los nombres estén estandarizados.

```sql
-- Identificar duplicados y actualizar tabla origen (o la Dimensión)
WITH CTE AS (
    SELECT DNI, Nombre_Completo,
           ROW_NUMBER() OVER(PARTITION BY DNI ORDER BY Fecha_Actualizacion DESC) as rn
    FROM Silver.Dim_Personal
)
-- La lógica requerirá una limpieza o merge manual en el origen, 
-- o forzar la actualización de la dimensión con los nombres correctos.
```

**Fase 2: Uso de `obtener_id_personal`**
Al usar el orquestador ETL, el procesador de Silver llamará a `lookup.obtener_id_personal(dni, engine)`.
Si la dimensión ya está limpia, automáticamente absorberá ambas variantes del Excel a un único `ID_Personal`.

---

## 3. PUNTO: CONFIRMACIÓN DE SEMÁNTICA

### 3.1 Hallazgo Confirmado

**PUNTO = Contador acumulado de errores por evaluador** (Métrica de severidad)

No es geografía ni identificador.

- **Media:** 4.21 errores por registro.

### 3.2 Uso en Arquitectura del DWH

**En Silver (Capa de Factura Transaccional)**:
Se implementará un nuevo procesador `ETL/silver/facts/fact_error_operativo.py` heredando de `BaseProcessor`.

```sql
CREATE TABLE Silver.Fact_Error_Operativo (
    ID_Fact BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Personal INT NOT NULL, -- Evaluador
    ID_Tipo_Error INT NOT NULL,
    Puntos INT NOT NULL, -- Valor del error individual
    Comentarios VARCHAR(MAX),
    Fecha_Carga DATETIME DEFAULT GETDATE(),
    -- FKs a las dimensiones correspondientes
);
```

**En Gold (Capa de Datamart Analítico)**:

```sql
CREATE VIEW Gold.Mart_Calidad_Operativa AS
SELECT 
    p.DNI,
    p.Nombre_Completo AS Evaluador,
    t.Anio,
    t.Mes,
    t.Semana_Anio,
    COUNT(f.ID_Fact) as Cantidad_Errores,
    SUM(f.Puntos) as Suma_Puntos,
    AVG(CAST(f.Puntos AS FLOAT)) as Punto_Promedio,
    (SUM(f.Puntos) / NULLIF(COUNT(f.ID_Fact), 0)) as Tasa_Severidad
FROM Silver.Fact_Error_Operativo f
JOIN Silver.Dim_Personal p ON f.ID_Personal = p.ID_Personal
JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
GROUP BY p.DNI, p.Nombre_Completo, t.Anio, t.Mes, t.Semana_Anio;
```

---

## 4. ESTRATEGIA DE IMPLEMENTACIÓN DWH

### 4.1 Orden de Ejecución

```text
SEMANA 1: Validación Operativa (SIN código)
├─ Taller: confirmar catálogo de tipos de error y resolver "Sin corregir"
├─ Firmar diccionario de mapeo

SEMANA 2: Infraestructura y ETL
├─ Script SQL: Crear mdm.Catalogo_Tipo_Error y Silver.Fact_Error_Operativo
├─ Actualizar ETL/mdm/lookup.py para soportar obtener_id_tipo_error()
├─ Crear procesador: ETL/silver/facts/fact_error_operativo.py
└─ Desplegar al pipeline principal

SEMANA 3: Validación y Portal
├─ Verificar integridad referencial y métrica PUNTO
├─ Crear Gold.Mart_Calidad_Operativa
└─ Reflejar en Streamlit / FastAPI endpoint
```

### 4.2 Tareas de Desarrollo Específicas (`ACP_DWH`)

1. **Configuración MDM**: Añadir `mdm.Catalogo_Tipo_Error` y crear su función homóloga en `lookup.py`.
2. **Desarrollo del Procesador**: Desarrollar `fact_error_operativo.py` basado en `BaseProcessor`.
3. **Limpieza `Dim_Personal`**: Generar script SQL para hacer merge de los 11 DNIs invertidos en la BD de origen o directamente en Silver.

---

## 5. CHECKLIST ANTES DE DESARROLLO

- [ ] **Tipos de Error**: ¿Catálogo final aprobado por operaciones?
- [ ] **"Sin corregir"**: ¿Definido como estado o tipo de error?
- [ ] **11 DNIs duplicados**: ¿Acordado el formato estándar para `Dim_Personal`?
- [ ] **PUNTO**: ¿Validado por TI que este campo siempre tendrá un valor entero asignable a severidad?
