import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ETL')))

from mdm.lookup import resolver_geografia, limpiar_cache
from utils.db import obtener_engine

def verificar_fix():
    engine = obtener_engine()
    limpiar_cache()
    
    casos = [
        ("FUNDO 1", "9.1", "1", "1"),
        ("FUNDO 1", "11.2", "23", "81"),
        ("FUNDO 1", "14.2", "12", "48")
    ]
    
    print("Verificando resolucion de Geografia con el Fix:")
    print("-" * 50)
    for f, m, t, v in casos:
        res = resolver_geografia(f, None, m, engine, turno=t, valvula=v)
        id_geo = res.get('id_geografia')
        estado = res.get('estado')
        print(f"Input: Modulo={m} Turno={t} Valvula={v}")
        print(f"Resultado: ID_Geografia={id_geo} | Estado={estado}")
        print("-" * 50)

if __name__ == "__main__":
    verificar_fix()
