import traceback
from SixWek import ejecutar_sixweek, ParametrosSixweek, obtener_engine

try:
    engine = obtener_engine()
    params = ParametrosSixweek(id_campaña=None, año_conteo=2026, semana_conteo=13)
    res = ejecutar_sixweek(engine, params)
    print("RESUMEN:", res)
except Exception as e:
    print("ERROR DETECTADO:")
    traceback.print_exc()
