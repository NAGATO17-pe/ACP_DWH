import pandas as pd
import numpy as np
import os

# --- Configuración del Modelo (Sincronizado con motor_proyecciones.py) ---
DECAY_FACTOR = {1: 1.0, 2: 1.0, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8}

# Matriz de maduración (Variable B en Excel)
# Se usará la de motor_proyecciones.py por defecto, o se puede extraer del Excel.
# Por ahora usaremos los valores detectados en el Excel para validación manual.

def simular():
    excel_path = r'd:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx'
    
    print(f"Cargando Excel: {os.path.basename(excel_path)}...")
    df = pd.read_excel(excel_path, sheet_name='Calculo', header=3)
    
    # Filtrar filas sin datos (donde Kg Sem 1 a 6 sean 0 o NaN)
    df = df.dropna(subset=['Kg Sem 1', 'Kg Sem 2', 'Kg Sem 3', 'Kg Sem 4', 'Kg Sem 5', 'Kg Sem 6'], how='all')
    
    resultados = []
    
    for idx, r in df.iterrows():
        # Identificadores (Módulo, Turno, Variedad)
        # Asumiendo columnas 1, 2, 3 son Mod, Tur, Var (visto en Proyección Turno, 
        # pero en Calculo pueden variar. Usaremos las columnas por nombre si existen)
        mod = r.iloc[1]
        tur = r.iloc[2]
        var = r.iloc[3]
        
        plantas = r['Plantas']
        if pd.isna(plantas) or plantas == 0:
            continue
            
        # Conteos (Variable A)
        # ['Boton Floral', 'Flor', 'Pequeña', 'Verdes', 'Fase 1', 'Fase 2', 'Cremas', 'Maduras', 'Cosechable']
        counts = {
            'cosechable': r.get('Cosechable', 0),
            'maduras': r.get('Maduras', 0),
            'cremas': r.get('Cremas', 0),
            'fase_2': r.get('Fase 2', 0),
            'fase_1': r.get('Fase 1', 0),
            'verdes': r.get('Verdes', 0),
            'pequena': r.get('Pequeña', 0)
        }
        
        # Simulación para las 6 semanas
        sim_kg = {}
        excel_kg = {}
        
        for w in range(1, 7):
            # 1. Variables de la semana desde el Excel
            peso = r.get(f'Peso Baya kg Sem {w}', 0)
            prod = r.get(f'% Plantas Productivas Sem {w}', 0)
            
            # 2. Porcentajes de maduración para la semana w (Variable B)
            # En el Excel, Variable B tiene nombres como '% Fase 1 Sem 1', '% Fase 2 Sem 1', etc.
            # No todos los estados están en todas las semanas.
            sum_organos_maduros = 0
            
            # Lógica de estados por semana (según motor_proyecciones.py)
            # S1: cosechable, maduras, cremas, fase_2, fase_1
            # S2: cremas, fase_2, fase_1, maduras, cosechable
            # S3: fase_1, verdes, fase_2
            # ...
            
            # Sin embargo, el Excel tiene columnas EXPLÍCITAS para cada estado/semana.
            # Vamos a usar las columnas del Excel para ver si coinciden.
            for estado in ['Cosechable', 'Maduras', 'Cremas', 'Fase 2', 'Fase 1', 'Verde', 'Pequeña']:
                # Mapeo de nombre de estado a la llave de counts
                estado_key = estado.lower().replace(' ', '_')
                if estado_key == 'verde': estado_key = 'verdes' # Normalización
                if estado_key == 'pequeña': estado_key = 'pequena'
                
                # El nombre de la columna en Excel varía: '% Maduro Sem 2' vs '% Maduras Sem 1'
                # Intentamos varios patrones
                col_patterns = [
                    f'% {estado} Sem {w}',
                    f'% {estado[:-1]} Sem {w}', # Maduras -> Madura
                    f'% {estado}s Sem {w}',     # Verde -> Verdes
                    f'% {estado} Sem {w}'       # Pequeña -> Pequeña
                ]
                # Correcciones específicas observadas en el listado de columnas
                if estado == 'Maduras' and w == 2: col_name = '% Maduro Sem 2'
                elif estado == 'Pequeña': col_name = f'% Pequea Sem {w}'
                elif estado == 'Verde': col_name = f'% Verde Sem {w}'
                else: col_name = f'% {estado} Sem {w}'
                
                pct = r.get(col_name, 0)
                if pd.isna(pct): pct = 0
                
                sum_organos_maduros += counts[estado_key] * pct
            
            # Formula: Sum * Plantas * Peso * Prod * Decay
            decay = DECAY_FACTOR.get(w, 1.0)
            calc_kg = sum_organos_maduros * plantas * peso * prod * decay
            
            sim_kg[w] = calc_kg
            excel_kg[w] = r.get(f'Kg Sem {w}', 0)
            
        resultados.append({
            'modulo': mod,
            'turno': tur,
            'variedad': var,
            'sim_kg': sim_kg,
            'excel_kg': excel_kg
        })

    # --- Reporte de Resultados ---
    total_sim = {w: 0 for w in range(1, 7)}
    total_excel = {w: 0 for w in range(1, 7)}
    
    for res in resultados:
        for w in range(1, 7):
            total_sim[w] += res['sim_kg'][w]
            total_excel[w] += res['excel_kg'][w]
            
    print("\n" + "="*50)
    print("RESUMEN DE SIMULACIÓN (6 SEMANAS)")
    print("="*50)
    print(f"{'Semana':<10} | {'Excel (kg)':<15} | {'Simulado (kg)':<15} | {'Var %':<10}")
    print("-" * 60)
    
    for w in range(1, 7):
        e = total_excel[w]
        s = total_sim[w]
        diff = ((s - e) / e * 100) if e != 0 else 0
        print(f"Semana {w:<2} | {e:15,.2f} | {s:15,.2f} | {diff:>8.2f}%")
        
    total_e = sum(total_excel.values())
    total_s = sum(total_sim.values())
    total_diff = ((total_s - total_e) / total_e * 100) if total_e != 0 else 0
    
    print("-" * 60)
    print(f"{'TOTAL':<10} | {total_e:15,.2f} | {total_s:15,.2f} | {total_diff:>8.2f}%")
    print("="*50)

if __name__ == "__main__":
    simular()
