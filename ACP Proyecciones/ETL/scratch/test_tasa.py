import os
import sys
import time
sys.path.append(os.getcwd())
from config.conexion import obtener_engine
from silver.facts.fact_tasa_crecimiento_brotes import cargar_fact_tasa_crecimiento_brotes
from silver.facts.fact_tasa_crecimiento_brotes import ProcesadorTasaCrecimientoBrotes

engine = obtener_engine()

print("Iniciando test de Tasa Crecimiento Brotes...")
start = time.time()
res = cargar_fact_tasa_crecimiento_brotes(engine)
print("Finished in", time.time() - start, "seconds")
print("Result:", res)
