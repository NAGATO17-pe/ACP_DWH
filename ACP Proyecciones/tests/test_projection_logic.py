import sys
import os
import pandas as pd
from datetime import datetime

# Añadir el path del proyecto para importar utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ETL")))

from acp_mdm_portal.utils.motor_proyecciones import (
    cerrar_matriz,
    calcular_pct_productivas,
    kg_unidad_semana,
    MATRIZ_INPUTS_DEFAULT,
    ID_ESTADO_MAP
)

def test_cerrar_matriz():
    print("Testing cerrar_matriz...")
    matriz_cerrada = cerrar_matriz(MATRIZ_INPUTS_DEFAULT)
    
    for estado, semanas in matriz_cerrada.items():
        total = sum(semanas)
        print(f"  {estado}: {semanas} (Total: {total:.4f})")
        if estado in ["cosechable", "maduras", "cremas"]:
            assert abs(total - 1.0) < 1e-6, f"Estado {estado} no suma 1.0"
    print("cerrar_matriz passed!")

def test_calcular_pct_productivas():
    print("Testing calcular_pct_productivas...")
    s1 = 0.90
    prod_w = calcular_pct_productivas(s1)
    print(f"  S1: {s1} -> {prod_w}")
    assert prod_w[0] == 0.90
    assert prod_w[1] == 0.92 # +2%
    assert prod_w[2] == 0.92 # S3 = S2
    assert round(prod_w[3], 2) == 0.89 # -3%
    assert round(prod_w[4], 2) == 0.90 # +1%
    assert round(prod_w[5], 2) == 0.91 # +1%
    print("calcular_pct_productivas passed!")

def test_kg_unidad_semana():
    print("Testing kg_unidad_semana...")
    conteo = {9: 10.0} # 10 bayas cosechables/planta
    matriz = {"cosechable": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    plantas = 1000
    pesos = {1: 0.005, 2: 0.005, 3: 0.005, 4: 0.005, 5: 0.005, 6: 0.005} # 5g
    prod = [1.0] * 6
    
    # Fake DECAY_FACTOR for test if needed, but we imported it
    kg = kg_unidad_semana(conteo, matriz, plantas, pesos, prod)
    print(f"  Kg por semana: {kg}")
    # W1: 10 * 1.0 * 1000 * 0.005 * 1.0 * 1.0 = 50 kg
    assert kg[0] == 50.0
    assert kg[1] == 0.0
    print("kg_unidad_semana passed!")

if __name__ == "__main__":
    try:
        test_cerrar_matriz()
        test_calcular_pct_productivas()
        test_kg_unidad_semana()
        print("\nAll logic tests passed!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
