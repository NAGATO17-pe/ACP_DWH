import sys, os
sys.path.append(os.getcwd())
from utils.motor_proyecciones import ejecutar_proyeccion, MATRIZ_INPUTS_DEFAULT, MARGEN_PESIMISTA, MARGEN_OPTIMISTA

id_t = 20260309
res = ejecutar_proyeccion(id_t, MATRIZ_INPUTS_DEFAULT, MARGEN_PESIMISTA, MARGEN_OPTIMISTA)

print(f"--- PROYECCION SEMANA 11 (Base: {id_t}) ---")
print("\nKPIs Principales:")
print(f"  Toneladas Totales (Base): {res['kpis'].get('total_base', 0)/1000:,.1f} Tn")
print(f"  Toneladas Totales (Opt):  {res['kpis'].get('total_opt', 0)/1000:,.1f} Tn")
print(f"  Toneladas Totales (Pes):  {res['kpis'].get('total_pes', 0)/1000:,.1f} Tn")
print(f"  Kilos por Planta:         {res['kpis'].get('kg_por_planta', 0):,.2f} kg")
print(f"  Plantas Totales:          {res['kpis'].get('total_plantas', 0):,.0f}")

print("\nResultados por Semana:")
df = res['df_semanal']
if not df.empty:
    df['Toneladas'] = df['kg_base'] / 1000.0
    print(df[['semana_label', 'Toneladas']])
else:
    print("No hay datos para esta semana.")
