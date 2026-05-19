"""
cargar_historicos_v2.py
=======================
Orquestador para cargar TODA la data historica desde ETL/data/Data Historica/
al DWH usando la ruta canonica del pipeline: Excel -> Bronce -> Silver.

Caracteristicas:
- Cada archivo se copia primero a ETL/data/entrada/<carpeta>/<archivo>__hist_<TS>.<ext>
  con sufijo timestamp para no pisar archivos existentes.
- Bronce: se usa bronce/cargador.cargar_archivo (mismo path que el pipeline normal).
- Silver: se invoca el cargar_fact_* correspondiente (lee de Bronce con Estado_Carga='CARGADO').
- Idempotente: BaseFactProcessor usa WHERE NOT EXISTS sobre UX_*_Grain.
- try/except por tarea: una falla no aborta las demas. Captura ErrorCircuitBreaker*.
- Censo: caso especial, va directo a Silver.Fact_Areas_Plantas (sin Bronce).
- Calidad_Poda: NO se carga (el CSV historico no trae mediciones, no encaja en el modelo).

Uso:
    python cargar_historicos_v2.py              # corre todas las tareas
    python cargar_historicos_v2.py --solo Pesos # corre solo una
    python cargar_historicos_v2.py --dry-run    # corre Bronce pero no Silver
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

# Asegurar imports relativos al ETL/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.conexion import obtener_engine
from bronce.cargador import cargar_archivo
from bronce.rutas import CARPETA_ENTRADA
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError

from silver.facts.fact_conteo_fenologico import cargar_fact_conteo_fenologico
from silver.facts.fact_evaluacion_pesos import cargar_fact_evaluacion_pesos
from silver.facts.fact_cosecha_sap import cargar_fact_cosecha_sap
from silver.facts.fact_evaluacion_vegetativa import cargar_fact_evaluacion_vegetativa
from silver.facts.fact_areas_plantas import cargar_fact_areas_plantas


BASE_PATH = Path(__file__).parent / 'data' / 'Data Historica'
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')


TAREAS = [
    {
        'nombre':  'Fenologia',
        'archivo': 'fact_Fenologia.xlsx',
        'carpeta': 'conteo_fruta',
        'bronce':  'Bronce.Conteo_Fruta',
        'silver':  cargar_fact_conteo_fenologico,
    },
    {
        'nombre':  'Vegetativa',
        'archivo': 'fact_Evaluacion_vegetativa.xlsx',
        'carpeta': 'evaluacion_vegetativa_v2',
        'bronce':  'Bronce.Evaluacion_Vegetativa',
        'silver':  cargar_fact_evaluacion_vegetativa,
    },
    {
        'nombre':  'Pesos',
        'archivo': 'Fact_pesos.xlsx',
        'carpeta': 'evaluacion_pesos',
        'bronce':  'Bronce.Evaluacion_Pesos',
        'silver':  cargar_fact_evaluacion_pesos,
    },
    {
        'nombre':  'Cosecha',
        'archivo': 'historico_BI_Cosecha3.xlsx',
        'carpeta': 'reporte_cosecha',
        'bronce':  'Bronce.Reporte_Cosecha',
        'silver':  cargar_fact_cosecha_sap,
    },
    {
        'nombre':       'Censo',
        'archivo':      'fact_Censo_Plantas.xlsx',
        'directo_silver': True,
        'silver':       cargar_fact_areas_plantas,
    },
]


def _resumen_rechazos(cuarentena: list[dict], top_n: int = 5) -> str:
    if not cuarentena:
        return '      (sin rechazos)'
    motivos = Counter(c.get('motivo', 'SIN_MOTIVO') for c in cuarentena)
    lineas = [f'      - {n}x  {m}' for m, n in motivos.most_common(top_n)]
    extras = len(motivos) - top_n
    if extras > 0:
        lineas.append(f'      - ... y {extras} motivo(s) mas')
    return '\n'.join(lineas)


def _copiar_a_entrada(ruta_origen: Path, carpeta_canonica: str) -> Path:
    destino_dir = CARPETA_ENTRADA / carpeta_canonica
    destino_dir.mkdir(parents=True, exist_ok=True)
    nuevo_nombre = f'{ruta_origen.stem}__hist_{TIMESTAMP}{ruta_origen.suffix}'
    destino = destino_dir / nuevo_nombre
    shutil.copy2(ruta_origen, destino)
    return destino


def procesar_tarea(tarea: dict, engine, dry_run: bool = False) -> tuple[str, int, int, list]:
    """Retorna (estado, filas_bronce, filas_silver, cuarentena)."""
    ruta_origen = BASE_PATH / tarea['archivo']
    nombre = tarea['nombre']
    print(f"\n>>> {nombre}  ({tarea['archivo']})")

    if not ruta_origen.exists():
        print(f'    [SKIP] Archivo no encontrado: {ruta_origen}')
        return ('NO_ENCONTRADO', 0, 0, [])

    # Caso especial: Censo va directo a Silver
    if tarea.get('directo_silver'):
        try:
            resumen = tarea['silver'](engine, str(ruta_origen))
        except Exception as e:
            print(f'    [ERROR] {type(e).__name__}: {e}')
            traceback.print_exc()
            return ('SILVER_ERROR', 0, 0, [])
        filas_silver = resumen.get('Filas_Insertadas', 0)
        cuar = resumen.get('cuarentena', [])
        leidos = resumen.get('Filas_Leidas_Bronce', 0)
        print(f'    Leidos del Excel: {leidos}  |  Insertados en Silver: {filas_silver}  |  Rechazados: {len(cuar)}')
        if cuar:
            print(f'    Top motivos:\n{_resumen_rechazos(cuar)}')
        return ('OK', leidos, filas_silver, cuar)

    # 1. Copiar a data/entrada/<carpeta>/
    ruta_entrada = _copiar_a_entrada(ruta_origen, tarea['carpeta'])
    print(f"    Copiado a: {ruta_entrada.relative_to(Path(__file__).parent)}")

    # 2. Bronce
    res_bronce = cargar_archivo(tarea['carpeta'], ruta_entrada, tarea['bronce'], engine)
    estado_b = res_bronce.get('estado', 'ERROR')
    filas_bronce = int(res_bronce.get('filas', 0) or 0)
    if estado_b != 'OK':
        print(f"    [BRONCE {estado_b}] {res_bronce.get('mensaje', '(sin mensaje)')}")
        return ('BRONCE_' + estado_b, filas_bronce, 0, [])
    print(f"    Bronce: {filas_bronce} filas insertadas en {tarea['bronce']}")

    if dry_run:
        print(f'    [DRY-RUN] No se ejecuta Silver.')
        return ('OK_DRYRUN', filas_bronce, 0, [])

    # 3. Silver
    try:
        resumen_silver = tarea['silver'](engine)
    except ErrorCircuitBreakerCritico as e:
        print(f'    [CIRCUIT BREAKER CRITICO] {e}')
        return ('SILVER_CB_CRITICO', filas_bronce, 0, [])
    except ErrorCircuitBreakerError as e:
        print(f'    [CIRCUIT BREAKER ERROR] {e}')
        return ('SILVER_CB_ERROR', filas_bronce, 0, [])
    except Exception as e:
        print(f'    [SILVER ERROR] {type(e).__name__}: {e}')
        traceback.print_exc()
        return ('SILVER_ERROR', filas_bronce, 0, [])

    filas_silver = int(resumen_silver.get('Filas_Insertadas', 0) or 0)
    cuar = resumen_silver.get('cuarentena', [])
    print(f'    Silver: {filas_silver} filas insertadas  |  Rechazados: {len(cuar)}')
    if cuar:
        print(f'    Top motivos:\n{_resumen_rechazos(cuar)}')
    return ('OK', filas_bronce, filas_silver, cuar)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solo', help='Nombre de una sola tarea a ejecutar')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo carga Bronce, no llama loader Silver')
    args = parser.parse_args()

    engine = obtener_engine()

    tareas = TAREAS
    if args.solo:
        tareas = [t for t in TAREAS if t['nombre'].lower() == args.solo.lower()]
        if not tareas:
            print(f"No se encontro tarea '{args.solo}'. Disponibles: {[t['nombre'] for t in TAREAS]}")
            return 1

    resultados = []
    for t in tareas:
        try:
            estado, n_bronce, n_silver, cuar = procesar_tarea(t, engine, dry_run=args.dry_run)
        except Exception as e:
            print(f"\n[FATAL] Tarea '{t['nombre']}' aborto: {type(e).__name__}: {e}")
            traceback.print_exc()
            estado, n_bronce, n_silver, cuar = ('FATAL', 0, 0, [])
        resultados.append((t['nombre'], estado, n_bronce, n_silver, len(cuar)))

    print('\n' + '=' * 70)
    print('RESUMEN FINAL CARGA HISTORICA')
    print('=' * 70)
    print(f'  {"Tarea":<14} {"Estado":<20} {"Bronce":>10} {"Silver":>10} {"Cuar":>8}')
    print(f'  {"-"*14} {"-"*20} {"-"*10} {"-"*10} {"-"*8}')
    for nombre, estado, nb, ns, nc in resultados:
        print(f'  {nombre:<14} {estado:<20} {nb:>10} {ns:>10} {nc:>8}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
