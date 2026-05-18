
# Auditoria Profunda de Dimensiones  vs  Data Historica

Generado: 2026-05-14 12:00:41

DB: `ACP_DataWarehose_Proyecciones` @ localhost

## 1. Dim_Tiempo

- DB: **2020-01-01** -> **2026-06-30** (2,373 filas)
- Archivos requieren: **2016-07-26** -> **2026-04-08**
- Fechas requeridas y faltantes en Dim_Tiempo: **1,254**
- Primera faltante: `2016-07-26`  ·  Ultima faltante: `2019-12-31`

## 2. Dim_Campana

Estado actual en DB:

```
 ID_Campana  Anio_Cosecha Nombre_Campana
          0          1900    SIN_CAMPANA
          4          2020   Campaña 2020
          5          2021   Campaña 2021
          6          2022   Campaña 2022
          7          2023   Campaña 2023
          8          2024   Campaña 2024
          9          2025   Campaña 2025
          3          2026   Campaña 2026
```

Valores distintos de "Campana" observados en los archivos: **34**
(Ver `audit_csv/02_dim_campana_valores_archivo.csv` para detalle.)

**Problema**: el archivo mezcla formatos `2022`, `2022.0`, `2022 - 2023`, `2022-2023`. Necesita normalizacion antes de mapear a `Anio_Cosecha`.

## 3. Dim_Variedad — duplicados ya cargados + faltantes

Variedades en DB: **102**
Clusters duplicados (mismo material con nombres distintos): **3**
Total IDs duplicados a consolidar: **3**

| Clave normalizada | # IDs | IDs | Nombres en DB |
|---|---:|---|---|
| `FL19006` | 2 | 39, 88 | FL 19-006 | FL19 - 006 |
| `MEGACRISP` | 2 | 77, 10 | MEGA CRISP | Megacrisp |
| `MEGAEARLY` | 2 | 78, 29 | MEGA EARLY | Megaearly |

Variedades del archivo que NO matchean ningun cluster (faltantes reales): **20**
Top faltantes (ya normalizadas, ordenadas por frecuencia):

| Nombre en archivo | Frecuencia | Norm |
|---|---:|---|
| `FCM15-005 (2022)` | 127 | `FCM150052022` |
| `FCM15-005 (2023)` | 123 | `FCM150052023` |
| `MEGACRISP (T111-519)` | 100 | `MEGACRISPT111519` |
| `FCM15 - 005- 2022` | 60 | `FCM150052022` |
| `MAGAGEM (T111-219)` | 38 | `MAGAGEMT111219` |
| `FCM15 - 005- 2023` | 36 | `FCM150052023` |
| `MANILA 2° SIEMBRA` | 28 | `MANILA2°SIEMBRA` |
| `FCM15 - 005 - 2023` | 19 | `FCM150052023` |
| `MANILA 2°SIEMBRA` | 19 | `MANILA2°SIEMBRA` |
| `FCM15 - 005 - 2022` | 19 | `FCM150052022` |
| `ATLAS BLUE 2° SIEMBRA` | 12 | `ATLASBLUE2°SIEMBRA` |
| `JUPITER` | 9 | `JUPITER` |
| `BIANCA` | 6 | `BIANCA` |
| `FCM 15-087` | 2 | `FCM15087` |
| `SIN SEMBRAR` | 1 | `SINSEMBRAR` |
| `FL 03-228` | 1 | `FL03228` |
| `U. DE LA FLORIDA` | 1 | `UDELAFLORIDA` |
| `INDIGO CRISP` | 1 | `INDIGOCRISP` |
| `MAGA GEM` | 1 | `MAGAGEM` |
| `FALCONE` | 1 | `FALCONE` |

## 4. Dim_Personal — evaluadores historicos

Dim_Personal actual: **2** registros
```
 ID_Personal      DNI Nombre_Completo
          -1 00000000   Sin Evaluador
           2 42395461      Sin Nombre
```

DNIs unicos en archivo Evaluacion Vegetativa: **221**
DNIs que FALTAN en Dim_Personal: **220**

Top 15 evaluadores faltantes (por # de evaluaciones realizadas):

| DNI | Nombre | Evaluaciones |
|---|---|---:|
| 47372749 | JULIA ROSSMERY LOPEZ AYALA | 2,829 |
| 72210549 | ALEXANDRA EUSEBIA CRUZADO HUIMAN | 2,456 |
| 40957182 | YDEYLA RAMOS CAMPOS | 2,181 |
| 44132971 | LADY LAURA SERQUEN CONTRERAS | 2,020 |
| 75469665 | JHONATAN YANPOL CHUZON QUEVEDO | 1,933 |
| 48179290 | DORA ELIZABETH VERA VASQUEZ | 1,879 |
| 43208552 | NELIDA GAMBOA TAFUR | 1,755 |
| 74744440 | YANELLY MILAGROS PALOMINO AYCHO | 1,721 |
| 75322874 | VILMA GISELA CHONATE OLIVA | 1,626 |
| 40533093 | FLOR ESTHER GUEVARA YAMUNAQUE | 1,619 |
| 43693679 | MARIA GIOVANNA FERNANDEZ RODRIGUEZ | 1,587 |
| 75786404 | JULISSA DEL CARMEN MONTERO GUEVARA | 1,543 |
| 75979863 | LESLIE DANITZA DIAZ ELIAS | 1,485 |
| 47301288 | ROSELI LOZANO GIL | 1,477 |
| 48118434 | DENISSE TICLIAHUANCA GARCIA | 1,422 |

## 5. Dim_Geografia — combinaciones Modulo/Turno/Valvula

Combinaciones unicas (Modulo, Turno, Valvula) en DB: **1073**
Combinaciones referenciadas por archivos: **1056**
Combinaciones FALTANTES en Dim_Geografia: **144**

Top 15 combinaciones faltantes (por frecuencia de uso en archivos):

| Modulo | Turno | Valvula | Frecuencia | Archivos |
|---:|---:|---:|---:|---|
| 1 | 3 | 5 | 868 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 2 | 4 | 5 | 731 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 2 | 4 | 6 | 728 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 2 | 1 | 6 | 706 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 1 | 4 | 5 | 634 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 1 | 11 | 503 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 1 | 10 | 478 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 4 | 8 | 457 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 4 | 10 | 457 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 4 | 9 | 456 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 1 | 8 | 452 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 3 | 10 | 449 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 3 | 8 | 444 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 4 | 11 | 442 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |
| 3 | 3 | 11 | 409 | fact_Censo_Plantas.xlsx | fact_Evaluacion_vegetativa.xlsx | fact_Fenologia.xlsx | historico_BI_Cosecha3.xlsx |

## 6. Dim_Estado_Fenologico — mapping archivo <-> DB

Estados en DB:
```
 ID_Estado_Fenologico Nombre_Estado  Orden_Estado
                    1  Boton Floral             0
                    2          Flor             1
                    3       Pequena             2
                    4         Verde             3
                    5     Inicio F1             4
                    6     Inicio F2             5
                    7         Crema             6
                    8        Madura             7
                    9    Cosechable             8
```

Columnas de fase en `fact_Fenologia.xlsx` (a pivotear):
`Yema Hinchada, Boton, Flor, Pequena, Verde, Fase 1, Fase 2, Crema, Madura, Cosechable`

Mapping propuesto:

| Columna archivo | Estado_Fenologico DB | Accion |
|---|---|---|
| `Yema Hinchada` | `(no existe)` | INSERTAR nuevo estado con Orden_Estado=-1 |
| `Boton` | `Boton Floral` | Alias directo |
| `Flor` | `Flor` | Match exacto |
| `Pequena` | `Pequena` | Match exacto (limpiar enie en archivo) |
| `Verde` | `Verde` | Match exacto |
| `Fase 1` | `Inicio F1` | Alias |
| `Fase 2` | `Inicio F2` | Alias |
| `Crema` | `Crema` | Match exacto |
| `Madura` | `Madura` | Match exacto |
| `Cosechable` | `Cosechable` | Match exacto |

## 7. Capacidad de carga con FK estricto

Estimacion del % de filas de cada archivo que entrarian con FK estricto **hoy** (sin agregar nada a las Dims):

| Archivo | Filas | Fallaria por Variedad | Fallaria por Geografia | Fallaria por Tiempo | Filas cargables |
|---|---:|---:|---:|---:|---:|
| `fact_Fenologia.xlsx` | 103,559 | 50 | 2,340 | 0 | **101,169** (97.7%) |
| `fact_Evaluacion_vegetativa.xlsx` | 76,875 | 158 | 1,622 | 0 | **75,095** (97.7%) |
| `fact_Censo_Plantas.xlsx` | 4,169 | 7 | 497 | 0 | **3,671** (88.1%) |
| `fact_calidad_poda.csv` | 248 | 0 | 0 | 0 | **248** (100.0%) |
| `Fact_pesos.xlsx` | 19,862 | 128 | 0 | 0 | **19,734** (99.4%) |
| `historico_BI_Cosecha3.xlsx` | 157,921 | 261 | 8,499 | 18,338 | **133,059** (84.3%) |

# Conclusiones y proximo paso

1. **Dim_Tiempo**: faltan ~1 461 dias (2016-01-01 a 2019-12-31). Script trivial.
2. **Dim_Campana**: faltan 2016-2019. Normalizar formatos antes de cargar.
3. **Dim_Variedad**: corregir primero los clusters duplicados ya cargados; luego agregar las realmente faltantes.
4. **Dim_Personal**: cargar evaluadores desde `fact_Evaluacion_vegetativa.xlsx`.
5. **Dim_Geografia**: necesita poblarse con las combinaciones historicas para que las facts entren.
6. **Dim_Estado_Fenologico**: agregar `Yema Hinchada` + definir alias para `Boton`, `Fase 1`, `Fase 2`.