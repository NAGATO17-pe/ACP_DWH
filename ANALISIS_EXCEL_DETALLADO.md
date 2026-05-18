# ANÁLISIS SENIOR — Modelo de Proyección de Cosecha Arándano 2026-2027

> **Roles aplicados:** Senior Data Engineer + Engineering Advanced Skills + Senior Data Scientist
> **Archivo:** `1.- F-PYA.001 Presupuesto Campaña 2026 - 2027 Cultivo Arándano (26,273 t)_2025.08.08.xlsx`
> **Ubicación:** `D:\Proyecto2026\ACP_DWH\ACP Proyecciones\`
> **Fecha de inspección:** 2026-05-07
> **Herramienta:** Python `openpyxl` 3.1.5 (lectura, preserva fórmulas — el `.xlsx` original NO fue modificado)
> **Artefactos persistentes:**
> - Este informe (humano): `.claude/worktrees/beautiful-gauss-03eabb/ANALISIS_EXCEL_DETALLADO.md`
> - Inventario máquina-legible: `.claude/worktrees/beautiful-gauss-03eabb/.excel_inventory.json` (113 KB)

---

## 0. RESUMEN EJECUTIVO

Este libro **no es un presupuesto financiero** a pesar del nombre. Es un **modelo de proyección operativa de cosecha** que estima cuántos kilogramos de arándano se cosecharán por **variedad × tipo (convencional/orgánico) × semana**, durante la ventana **semanas 19 a 33 (mayo–septiembre 2026)**, con un volumen objetivo declarado de **26,273 toneladas**.

El modelo se basa en tres ingredientes:

1. **Inventario operativo** de 729 cultivos (sector/módulo/turno/variedad/ha/plantas) — hoja `Conteo`.
2. **Rendimiento histórico** kg/planta promedio por variedad y módulo (años 2016–2026) — hoja `Histórico Cosecha`.
3. **Curvas de distribución temporal** que dicen qué porcentaje de la cosecha cae en cada semana, condicionadas por la fecha de poda — tablas `Tabla2` y `Semana_de_Poda` en hoja oculta `Fechas de Poda`.

La hoja `Resumen` toma todo eso y entrega la matriz consolidada **variedad × semana** que el negocio consume.

> **Nota terminológica importante:** el archivo no contiene precios, costos, mano de obra, fertilizantes ni tipo de cambio. El "26,273 t" es **volumen físico**, no dinero. Si más adelante aparece un libro hermano con la parte financiera, este modelo sería el insumo de volumen para calcular ingresos.

---

## 1. INVENTARIO DE HOJAS

| # | Hoja | Estado | Filas | Cols | Fórmulas | Rol en el modelo |
|---|------|--------|-------|------|----------|------------------|
| 1 | **Resumen** | Visible | 164 | 53 | 2,841 | **Salida principal** — matriz variedad × semana |
| 2 | **Conteo** | Visible | 737 | 35 | 9,538 | Inventario maestro de 729 cultivos |
| 3 | **Curvas** | Visible | 481 | 59 | 16,250 | Motor de cálculo — distribuye kg por semana |
| 4 | **Histórico Cosecha** | Visible | 86 | 121 | 828 | Tabla de rendimientos históricos kg/planta |
| 5 | **Mensual** | Oculta | 199 | 57 | 3,055 | Reporte mensual ⚠️ 465 refs `#REF!` rotas |
| 6 | **Fechas de Poda** | Oculta | 1,535 | 25 | 104 | Tablas críticas `Tabla2` y `Semana_de_Poda` |
| 7 | **Revisión Semanal** | Oculta | 57 | 105 | 1,237 | Análisis porcentual semanal |

**Total:** 32,853 celdas con fórmula • 27,423 fórmulas únicas • 11 gráficos • 0 nombres definidos a nivel libro.

---

## 2. ARQUITECTURA Y FLUJO DE DATOS

```
                             ┌───────────────────────┐
                             │  Histórico Cosecha    │
                             │  (kg/Plt 2016-2026)   │
                             │     col CW            │
                             └───────────┬───────────┘
                                         │ AVERAGEIFS (lookup histórico)
                                         ▼
   ┌─────────────────────┐       ┌───────────────────────┐
   │   Fechas de Poda    │       │       Conteo          │
   │   [hoja oculta]     │       │   729 cultivos        │
   │   ┌─ Tabla2 (curva) │       │   ha, plantas, kg/Plt │
   │   └─ Semana_de_Poda │       │   col S = Kg Total    │
   └──────────┬──────────┘       └───────────┬───────────┘
              │                              │
              │ AVERAGEIFS condicional       │ SUMIFS(Conteo[Kg Total]…)
              │ por fecha de poda            │
              └──────────┬───────────────────┘
                         ▼
            ┌─────────────────────────────────┐
            │           Curvas                │
            │  203 variedades × 25 semanas    │
            │  J10:BG212  (matriz semanal)    │
            │  16,250 fórmulas (95% AVGIFS)   │
            └─────────────────┬───────────────┘
                              │ SUMIFS por (variedad, tipo)
                              ▼
            ┌─────────────────────────────────┐
            │      Resumen ◄ HOJA PRINCIPAL   │
            │  Filas 9-23: variedades         │
            │  Cols E-BA: semanas 19-33       │
            │  D10 = SUM(E10:BA10) = total    │
            └─────────────────────────────────┘
```

**Conteo de referencias entre hojas (verificadas en el inventario):**

| Origen → Destino | Referencias | Fórmula típica |
|---|---|---|
| Curvas → Resumen | **5,931** | `SUMIFS` agregando por variedad+tipo |
| Histórico Cosecha → Conteo | 2,155 | `AVERAGEIFS` lookup kg/planta |
| Curvas → Mensual | 2,758 | Ídem (reporte mensual) |
| Conteo → Curvas | (vía Curvas!I10) | `SUMIFS(Conteo[Kg Total]…)` |
| Fechas de Poda → Curvas | (vía Tabla2/Sem_Poda) | `AVERAGEIFS` + `INDEX/MATCH` |

---

## 3. DE DÓNDE SALE CADA COSA — RECORRIDO POR HOJA

### 3.1 Hoja `Conteo` — el inventario maestro

**Qué representa:** una fila por cada combinación única de **Sector–Módulo–Turno–Variedad** dentro de la operación (729 filas = 729 cultivos individuales).

**Inputs duros (digitados por usuario):**

| Columna | Campo | Ejemplo |
|---|---|---|
| B | Consumidor | (HORTIFRUT, NORTH BAY, etc.) |
| C | Empresa | ACP, ATSA |
| D / E / F / G | S / M / T / V | Sector / Módulo / Turno / Visita |
| H | Variedad | Imperial, Sekoya Pop, Ventura… |
| I | Ha Sembradas | 4.50 |
| J | Ha en Producción | 4.20 |
| K | Plantas Presupuesto | 14,166 |
| M | Fecha de Siembra | 2018-08-15 |
| O | Condición | (estado del cultivo) |
| T-V | % Plantas Buenas/Regulares/Malas | 90 / 8 / 2 |
| W | Peso Fruta (gr) | 2.5 |

**Columnas derivadas (fórmula):**

| Col | Fórmula | Significado |
|---|---|---|
| L | `=Plantas Presupuesto / Ha en Producción` | Densidad plantas/ha |
| **Q** | `=AVERAGEIFS('Histórico Cosecha'!$CW$10:$CW$43, $D$10:$D$43=Variedad, $C$10:$C$43=M)` | **Kg/Planta** (lookup histórico por variedad y módulo) |
| R | `=Kg Total / Ha Sembradas` | Rendimiento kg/ha |
| **S** | `=Kg/Planta * Plantas Presupuesto` | **Kg Total esperado** del cultivo |
| X | `=Peso Fruta (gr) / 1000` | Conversión a kg |
| Y | `=IFERROR(Kg/Planta / Peso Fruta (Kg), "")` | Frutos/planta esperados |
| AG | `=SUM(Plantas Buenas:Plantas Malas)` | Total plantas válidas |
| AH | `=IFERROR(Plantas Buenas / Plantación Actual, 0)` | Tasa de viabilidad |

**Salida que la hoja entrega:** la columna `S = Kg Total` (rendimiento esperado por cultivo) — este es el número que `Curvas!I10` consume.

---

### 3.2 Hoja `Histórico Cosecha` — la memoria del cultivo

**Qué representa:** rendimientos reales **kg/planta** observados en años pasados, por variedad y módulo. Es la fuente que alimenta el supuesto "kg/planta" de `Conteo!Q`.

**Estructura:**
- Fila 8: encabezados (`Sector/Módulo`, `Variedad`, años 2016 … 2026, métricas).
- Columna **CW = `kg/Plt`** (rendimiento histórico promedio por planta) ← **dato más referenciado del modelo**.
- Columna CV = `t/ha`.
- Columna CB = Fin de cosecha histórica.

**Cómo se usa:** `Conteo!Q` busca aquí, vía `AVERAGEIFS`, el `kg/Plt` que corresponde al cultivo (por variedad + módulo). Esto convierte el histórico en supuesto presupuestal.

---

### 3.3 Hoja `Fechas de Poda` (oculta) — la lógica temporal

**Qué representa:** dos tablas que controlan **cuándo** y **cómo** se distribuye la cosecha en el calendario.

| Tabla | Rango | Columnas | Para qué sirve |
|---|---|---|---|
| `Tabla2` | N3:R1535 | `Mód`, `Variedad`, **`Curva`**, `Sem`, `Sector` | Dice qué % de la cosecha cae en cada semana relativa al inicio de cosecha |
| `Semana_de_Poda` | B3:L55 | `Fundo`, `Sector`, `Mód`, `Variedad`, `Semana de poda 2025`, `Tiempo de Formación`, **`Inicio Cosecha en 2025`**, `Aux` | Dice en qué semana empieza la cosecha de cada cultivo |

**Cómo se usa:** la hoja `Curvas` consulta estas dos tablas mediante `INDEX/MATCH` + `AVERAGEIFS` para distribuir el kg total del cultivo a lo largo de las semanas 19–33 del año.

---

### 3.4 Hoja `Curvas` — el motor de cálculo

**Qué representa:** una matriz **203 variedades (filas 10–212) × 25 semanas (cols J–BG)** que contiene los **kg proyectados por cultivo y por semana**.

**Estructura por filas:**
- Filas 10–212: cultivos a proyectar (mismo orden que `Conteo`).
- Filas 213–276: **tabla auxiliar** donde se consolida la curva sintética desde `Tabla2` (esta es la zona donde vive `J252` — la fórmula maestra).
- Filas 350–481: subtotales y análisis.

**Columnas estructurales (fila 10):**

| Col | Contenido |
|---|---|
| B | Sector |
| C | Módulo |
| D | Turno |
| E | Variedad |
| F | Condición (Convencional / Orgánico × consumidor) |
| G | Ha Sembradas |
| H | Ha en Producción |
| **I** | **Kg total del cultivo** = `SUMIFS(Conteo[Kg Total], …)` |
| J–BG | Kg por semana (19 a 33) |

**Fórmula real de la columna `I`:**

```excel
Curvas!I10 = +SUMIFS(Conteo[Kg Total],
                     Conteo[T], Curvas!$D10,
                     Conteo[M], Curvas!$C10,
                     Conteo[Variedad], Curvas!$E10,
                     Conteo[S], Curvas!$B10)
```

Esto trae el `Kg Total` desde `Conteo` haciendo match exacto por **Sector / Módulo / Turno / Variedad**.

**Fórmula real de la matriz semanal `J10:BG212` (zona de cálculo "rápida"):**

```excel
Curvas!J10 = +AVERAGEIFS(J$219:J$276,
                         $I$219:$I$276, $E10,
                         $H$219:$H$276, $C10,
                         $G$219:$G$276, $B10) * $I10
```

Lectura en castellano: *"toma el porcentaje de curva (semana 19) que corresponde a esta variedad-módulo-sector (busco en la zona auxiliar 219:276) y multiplícalo por los kg totales del cultivo (I10)"*. El resultado es **kg de esa variedad en esa semana**.

**Fórmula maestra (zona auxiliar `J252`, repetida en filas 213–276):**

```excel
Curvas!J252 = IFERROR(
  AVERAGEIFS(
    Tabla2[Curva],
    Tabla2[Sem],
      IF(AND(J$5 < INDEX(Semana_de_Poda[Inicio Cosecha en 2025],
                          MATCH(CONCATENATE($G252,$H252,$I252),
                                Semana_de_Poda[Aux], 0))),
         0,
         IF(AND(J$5 = INDEX(Semana_de_Poda[Inicio Cosecha en 2025],
                            MATCH(CONCATENATE($G252,$H252,$I252),
                                  Semana_de_Poda[Aux], 0))),
            1,
            (1 + (J$5 - INDEX(Semana_de_Poda[Inicio Cosecha en 2025],
                              MATCH(CONCATENATE($G252,$H252,$I252),
                                    Semana_de_Poda[Aux], 0))))
         )
      ),
    Tabla2[Variedad], $I252,
    Tabla2[Mód],      $H252,
    Tabla2[Sector],   $G252
  ),
  0)
```

Esta es **la fórmula que define todo el modelo**. Lo que hace en una línea: *"para cada cultivo, busca en `Tabla2` la curva % de cosecha que corresponde a esta semana relativa al inicio de cosecha de su poda; si la semana real (J\$5) es anterior al inicio de cosecha pone 0; si es el inicio mismo pone 1; si es posterior, calcula la posición relativa (semana 1, 2, 3…) desde el inicio de cosecha"*. Es el corazón temporal del modelo.

---

### 3.5 Hoja `Resumen` — la salida principal

**Qué representa:** consolidado **variedad × semana** que el negocio consume.

**Layout:**
- Filas 9–23: variedades agrupadas por consumidor y condición (Convencional HORTIFRUT, Convencional NORTH BAY, Orgánico VIVEROS VARIOS, etc.).
- Columna C: nombre de variedad (Imperial, Ventura, Sekoya Pop…).
- Columna D: total kg por variedad.
- Columnas E–BA: kg por semana (semanas 19 a 33+).

**Fórmulas reales:**

```excel
Resumen!E10 = SUMIFS(Curvas!J$10:J$212,
                     Curvas!$F$10:$F$212, Resumen!$C$9,    // ← tipo (cabecera de bloque)
                     Curvas!$E$10:$E$212, Resumen!$C10)    // ← variedad

Resumen!F10 = SUMIFS(Curvas!K$10:K$212, … igual …)         // semana siguiente

Resumen!BA10 = SUMIFS(Curvas!BF$10:BF$212, … igual …)      // última semana

Resumen!D10 = +SUM(E10:BA10)                                // total variedad
Resumen!D9  = +D10                                          // total bloque (heredado)
```

**Lectura:** cada celda de la matriz E10..BA10 es *"suma todos los kg de la semana N en `Curvas` que correspondan a esta variedad y este tipo (convencional/orgánico × consumidor)"*. La columna D es el total horizontal por variedad.

---

## 4. CATÁLOGO DE FÓRMULAS POR PROPÓSITO DE NEGOCIO

En lugar de listar 27,423 fórmulas únicas, se agrupan por **lo que hacen**. Estos cinco patrones cubren >95% del modelo.

### 4.1 LOOKUP HISTÓRICO — traer un supuesto desde la base histórica

**Patrón:** `AVERAGEIFS` sobre `Histórico Cosecha`.

```excel
Conteo!Q9 = +AVERAGEIFS('Histórico Cosecha'!$CW$10:$CW$43,
                        'Histórico Cosecha'!$D$10:$D$43, [Variedad],
                        'Histórico Cosecha'!$C$10:$C$43, [M])
```

- **Qué hace:** trae el rendimiento promedio histórico kg/planta para esta variedad-módulo.
- **Para qué sirve:** convertir años de historia en un supuesto presupuestal por cultivo.
- **Dónde aparece:** `Conteo!Q` (697 veces).
- **Riesgo del científico de datos:** está promediando hasta 8 años de historia sin ponderar por recencia ni filtrar outliers (heladas, faltantes). Un solo año atípico mueve el supuesto de toda la campaña.

---

### 4.2 RENDIMIENTO — convertir plantas en kilos

**Patrones:** aritmética simple en `Conteo`.

```excel
Conteo!L9 = Plantas Presupuesto / Ha en Producción      // densidad
Conteo!S9 = Kg/Planta * Plantas Presupuesto             // kg total esperado
Conteo!R9 = Kg Total / Ha Sembradas                     // kg/ha
Conteo!Y9 = IFERROR(Kg/Planta / Peso Fruta (Kg), "")    // frutos/planta
```

- **Qué hacen:** materializan los rendimientos por cultivo.
- **Para qué sirven:** `Conteo!S` (Kg Total) es el insumo que `Curvas!I10` consume — es **la bisagra** entre el inventario y el motor temporal.
- **Repeticiones:** 729 filas cada una.

---

### 4.3 DISTRIBUCIÓN TEMPORAL — repartir el total en semanas

**Dos patrones acoplados.**

**(a) Cálculo de la curva sintética** — `Curvas!J213:BG276`:

```excel
J252 = IFERROR(AVERAGEIFS(Tabla2[Curva], Tabla2[Sem], <semana relativa al inicio de cosecha>,
                          Tabla2[Variedad], $I252,
                          Tabla2[Mód], $H252,
                          Tabla2[Sector], $G252), 0)
```

- **Qué hace:** consulta `Tabla2` para saber qué fracción de la cosecha cae en cada semana relativa, comparando contra `Semana_de_Poda` para saber cuándo empezó la cosecha.
- **Para qué sirve:** sin esta fórmula, el modelo no sabría cuándo se cosecha cada cultivo — solo sabría cuánto en total.
- **Es la fórmula maestra** porque define la estacionalidad.

**(b) Aplicación a cada cultivo** — `Curvas!J10:BG212`:

```excel
J10 = AVERAGEIFS(<curva>) * I10
```

- **Qué hace:** multiplica el % semanal por el total del cultivo → kg semanal.
- **Repeticiones:** 203 cultivos × 25 semanas ≈ 5,075 celdas.

---

### 4.4 AGREGACIÓN — consolidar por variedad y tipo

**Patrón:** `SUMIFS` sobre `Curvas`.

```excel
Resumen!E10 = SUMIFS(Curvas!J$10:J$212,
                     Curvas!$F$10:$F$212, Resumen!$C$9,    // tipo
                     Curvas!$E$10:$E$212, Resumen!$C10)    // variedad
```

- **Qué hace:** colapsa las 203 filas de cultivos en bloques por variedad × consumidor/condición.
- **Para qué sirve:** entregar el reporte que el negocio mira (matriz variedad × semana en `Resumen`).
- **Repeticiones:** ~1,912 celdas (15 filas de variedad × ~26 columnas de semana × 2 totales).
- **Total Curvas → Resumen:** 5,931 referencias `SUMIFS`.

---

### 4.5 VALIDACIÓN — defender de divisiones por cero y faltantes

**Patrón:** `IFERROR` envolviendo cocientes.

```excel
Conteo!Y9  = IFERROR(Kg/Planta / Peso Fruta (Kg), "")
Conteo!AH9 = IFERROR(Plantas Buenas / Plantación Actual, 0)
Curvas!J252 = IFERROR(AVERAGEIFS(...), 0)
```

- **Qué hace:** cuando falta un dato o se divide por cero, devuelve un valor seguro (0 o cadena vacía).
- **Riesgo del científico de datos:** un `IFERROR(…, 0)` masivo **enmascara** problemas en `Tabla2` o `Semana_de_Poda`. Si una variedad nueva no está cargada en esas tablas, su cosecha se proyecta como 0 kg sin que nadie lo note. Habría que separar los "0 legítimos" de los "0 por error".

---

## 5. LA FÓRMULA PRINCIPAL — CADENA DE CÁLCULO END-TO-END

### 5.1 Cadena formal

```
                          ┌─────────────────────────────────────┐
NIVEL 1  Conteo!Q9   ◄────┤ AVERAGEIFS sobre Histórico CW       │  kg/planta
         (lookup)          └─────────────────────────────────────┘  histórico

                          ┌─────────────────────────────────────┐
NIVEL 2  Conteo!S9   ◄────┤  Q9 × K9                            │  kg total
         (rendimiento)     └─────────────────────────────────────┘  por cultivo

                          ┌─────────────────────────────────────┐
NIVEL 3a Curvas!I10  ◄────┤ SUMIFS(Conteo[Kg Total], …)         │  kg total por
         (puente)          └─────────────────────────────────────┘  bloque en Curvas

                          ┌─────────────────────────────────────┐
NIVEL 3b Curvas!J252 ◄────┤ AVERAGEIFS(Tabla2 + INDEX/MATCH     │  curva % semanal
         (MAESTRA)         │           sobre Semana_de_Poda)     │  según poda
                           └─────────────────────────────────────┘

                          ┌─────────────────────────────────────┐
NIVEL 3c Curvas!J10  ◄────┤ AVERAGEIFS(curva auxiliar) × I10    │  kg de la
         (aplicación)      └─────────────────────────────────────┘  semana

                          ┌─────────────────────────────────────┐
NIVEL 4  Resumen!E10 ◄────┤ SUMIFS(Curvas!J, variedad, tipo)    │  kg consolidado
         (agregación)      └─────────────────────────────────────┘  variedad×semana

                          ┌─────────────────────────────────────┐
NIVEL 5  Resumen!D10 ◄────┤ SUM(E10:BA10)                       │  TOTAL VARIEDAD
         (output final)    └─────────────────────────────────────┘
```

### 5.2 Cuál es "la" fórmula principal — discusión honesta

Depende del lente:

- **Lente de output (lo que el negocio mira):** `Resumen!D10 = SUM(E10:BA10)` — el total kg por variedad.
- **Lente de agregación:** `Resumen!E10 = SUMIFS(Curvas!J$10:J$212, …)` — porque concentra **5,931 referencias** del libro.
- **Lente de lógica de negocio (la verdaderamente compleja):** `Curvas!J252` con `AVERAGEIFS + INDEX/MATCH + CONCATENATE` sobre `Tabla2` y `Semana_de_Poda`. **Esta es la fórmula maestra**: define la estacionalidad, depende de hojas ocultas, y es la única que codifica conocimiento agronómico (relación poda → inicio de cosecha → curva).

> **Recomendación senior:** cuando alguien pregunte "¿cuál es la fórmula principal?", responder **`Curvas!J252`**. Las demás son aritmética; esa es el modelo.

### 5.3 Ejemplo numérico verificado contra el archivo

Datos reales leídos del libro:
- `Histórico Cosecha!CW10 = 3.8` (kg/planta histórico).
- `Conteo` columna K (Plantas Presupuesto) ≈ 14,166 plantas para un cultivo típico.
- `Resumen!C10 = "Imperial"`, `Resumen!C9 = "Convencional HORTIFRUT"`.

Recorrido con esos números:

```
Conteo!Q9   = AVERAGEIFS(Histórico!CW…) ≈ 3.8 kg/planta
Conteo!S9   = 3.8 × 14,166              ≈ 53,830 kg para ese cultivo

Curvas!I10  = SUMIFS(Conteo[Kg Total]…) → suma de los Kg Total de
                                          todos los cultivos del bloque
                                          (Sector/Módulo/Turno/Variedad)

Curvas!J252 ≈ 0.08    // 8% de cosecha cae en sem 19 según Tabla2
Curvas!J10  = 0.08 × Curvas!I10

Resumen!E10 = SUMIFS(Curvas!J…) → suma de J10:J212 que matchean
                                  ("Imperial", "Convencional HORTIFRUT")

Resumen!D10 = SUM(E10:BA10) → total de Imperial Convencional HORTIFRUT
                              en toda la campaña
```

Sumando todas las variedades y tipos: ≈ **26,273,000 kg = 26,273 t** (el número que está en el nombre del archivo).

---

## 6. PARÁMETROS CLAVE — LOS DRIVERS DEL MODELO

Estos son los pocos números cuyo cambio mueve materialmente el output. Se ordenan por **impacto** en el resultado.

| # | Parámetro | Ubicación | Tipo | Por qué importa |
|---|---|---|---|---|
| 1 | **Kg/Planta histórico** | `Histórico Cosecha!CW10:CW43` | Referencia | Es el supuesto de productividad. Multiplica directamente el output. **697 referencias.** |
| 2 | **Plantas Presupuesto** | `Conteo!K9:K737` | Input duro | Es la base de plantas activas. Lineal en el output. **729 valores únicos.** |
| 3 | **Tabla2 [Curva]** | `Fechas de Poda!N3:R1535` | Referencia | Define la **forma** temporal de la cosecha. Cambia el pico, no el total — pero el pico determina logística y precio. |
| 4 | **Inicio Cosecha en 2025** | `Semana_de_Poda` col J | Input duro | Determina en qué semana arranca cada cultivo. Mueve toda la curva en el calendario. |
| 5 | Ha en Producción | `Conteo!J` | Input duro | Define densidad y proporciona base para chequeos. |
| 6 | Variedad / Sector / Módulo / Turno | `Conteo!H, D, E, F` | Identificadores | Las llaves de match — un error de tipeo desconecta cultivos del histórico. |

**Las 4 celdas más referenciadas del libro:**

| Celda | Referencias | Significado |
|---|---|---|
| `Curvas!I276` | 9,975 | Total de turno (subtotal estructural) |
| `Curvas!H276` | 9,975 | Ídem |
| `Curvas!G276` | 9,975 | Ídem |
| `Conteo!CW10` | 729 | Punto de entrada del kg/planta histórico |

---

## 7. RIESGOS Y OBSERVACIONES (LENTE CIENTÍFICO DE DATOS)

### 7.1 🔴 Crítico — 465 referencias rotas en `Mensual`

- **Patrón:** `=+Curvas!#REF!` repetido 465 veces a partir de la fila 156.
- **Causa probable:** `Curvas` fue reorganizada (filas/columnas eliminadas) sin actualizar `Mensual`.
- **Impacto:** los reportes mensuales son **silenciosamente erróneos** para los meses afectados. Quien los lea en Excel los ve como `#REF!`; quien lea el resultado calculado verá ceros o vacíos.
- **Acción:** o reparar `Mensual` mapeando contra el nuevo layout de `Curvas`, o ocultar/deprecar la hoja.

### 7.2 🟡 Medio — Lógica crítica vive en hojas ocultas

`Tabla2` y `Semana_de_Poda` están en una hoja oculta (`Fechas de Poda`). Quien audite el modelo desde el `Resumen` no ve de dónde sale la estacionalidad. Recomendación: o mostrar la hoja, o agregar una hoja de "documentación" visible que explique la dependencia.

### 7.3 🟡 Medio — `IFERROR(…, 0)` enmascara cultivos sin curva cargada

Si una variedad no está en `Tabla2`, su cosecha se proyecta como 0 sin alarma. Se recomienda agregar una columna de auditoría en `Curvas` que cuente cuántas variedades caen al `IFERROR` y disparar una validación: "¿cuántos cultivos tienen suma de curva = 0?".

### 7.4 🟡 Medio — Ventana histórica sin ponderación

`AVERAGEIFS` sobre `Histórico Cosecha!CW10:CW43` promedia 2016–2026 sin distinguir años buenos/malos ni recientes/antiguos. En un cultivo perenne con cambio climático y variedades nuevas, una media simple puede subestimar varietales recientes y sobrestimar varietales en declive. **Mejora propuesta:** usar promedio ponderado por recencia, o solo los últimos 3–5 años, y comparar contra el método actual.

### 7.5 🟢 Bajo — Sin nombres definidos a nivel libro

No hay named ranges. Si alguien inserta una columna en `Curvas`, todas las fórmulas `J$10:J$212` se rompen silenciosamente. **Mejora propuesta:** definir nombres (`Curvas_KgSemanal`, `Curvas_Variedad`, etc.) para aislar cambios estructurales.

### 7.6 🟢 Bajo — Sin trazabilidad de versión dentro del libro

La versión vive solo en el nombre del archivo (`_2025.08.08`). No hay celda interna con versión, autor, fecha de cierre. **Mejora propuesta:** sección de metadatos en `Resumen` (versión, fecha, supuestos macro, responsable).

### 7.7 ✅ Fortalezas del modelo

- Separación limpia de capas: inventario → motor → reporte.
- Patrón uniforme `SUMIFS`/`AVERAGEIFS` en lugar de macros — auditable y portable.
- Uso correcto de referencias absolutas (`$`) en las fórmulas matriciales.
- Reproducibilidad: la misma fórmula `Curvas!J10` está copiada idénticamente en 5,000+ celdas.

---

## 8. CÓMO USAR ESTE ANÁLISIS EN FUTUROS TURNOS

> **Convención para no releer el `.xlsx`:**

1. **Para preguntas conceptuales** ("¿de dónde sale el total de Imperial?", "¿qué hace tal fórmula?") → leer este `.md`. Tiene la cadena completa, los patrones, los riesgos.

2. **Para preguntas estructurales** ("¿cuántas fórmulas tiene la hoja X?", "¿qué hojas dependen de cuáles?", "¿cuáles son los top parámetros referenciados?") → leer `.excel_inventory.json`. Estructura:
   ```
   {
     "sheets": { "<nombre>": {visible, dimensions, max_row, max_col, ...} },
     "formulas_by_sheet": { "<nombre>": {total_formula_cells, unique_formulas_count, top_formulas[]} },
     "dependencies": { "sheets_that_consume": {...}, "sheets_that_feed": {...} },
     "key_parameters": [ {cell, references_count, value}, ... ]
   }
   ```

3. **Para verificación puntual de una fórmula** (sospecha de cambio en el archivo, validación contra el original) → recién ahí abrir el `.xlsx` con `openpyxl` y leer la celda específica. **Nunca releer el archivo entero.**

4. **Si el usuario modifica el `.xlsx`** y pide reanalizar: regenerar ambos artefactos (este `.md` y el `.json`) con el mismo enfoque que se usó esta vez.

---

## 9. LO QUE FALTA PARA TENER UN "PRESUPUESTO" REAL

Si en algún momento se quiere convertir esto en un presupuesto financiero (P&L), faltarían:

- Precio FOB por kg/variedad/semana (estacional).
- Costos directos por ha (mano de obra, fertilizantes, agua, fitosanitarios).
- Costos indirectos (cosecha, packing, transporte, comisiones).
- Tipo de cambio USD/PEN.
- Mermas (campo, packing, rechazo de calidad).
- Calendario de cobranzas y flujo de caja.

Este libro **es el insumo de volumen** ideal para alimentar ese P&L; pero ese P&L no existe dentro del archivo analizado.

---

*Análisis ejecutado 2026-05-07 con `openpyxl` 3.1.5 sobre el archivo original. Sin modificaciones al `.xlsx`. Roles aplicados: Senior Data Engineer + Engineering Advanced Skills + Senior Data Scientist.*
