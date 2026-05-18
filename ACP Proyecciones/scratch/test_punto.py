import re

def _parsear_valores_raw(texto: str | None) -> dict[str, str]:
    if not texto or not isinstance(texto, str):
        return {}
    pares = [p.strip() for p in texto.split('|') if p.strip()]
    resultado = {}
    for par in pares:
        if '=' in par:
            k, v = par.split('=', 1)
            resultado[k.strip()] = v.strip()
    return resultado

fila_test = "Fecha_Subida_Raw=25/03/2026 16:45:44 | DNI_Raw=47372749 | Nombres_Raw=JULIA ROSSMERY LOPEZ AYALA | Evaluacion_Raw=PODA GENERAL | Punto_Raw=3 | BotonesFlorales_Raw=0 | Flores_Raw=0 | BayasPequenas_Raw=132 | BayasGrandes_Raw=56 | Fase1_Raw=0 | Fase2_Raw=0 |"
valores_dict = _parsear_valores_raw(fila_test)
punto_val = str(valores_dict.get('Punto_Raw') or valores_dict.get('Punto') or '0').strip()
print(f"Punto extracted: '{punto_val}'")
