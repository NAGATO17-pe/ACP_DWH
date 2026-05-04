
import pandas as pd

def inspect_calculo():
    path = r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx"
    
    print("\n--- Sheet: Calculo (Headers at row 2) ---")
    df_calc = pd.read_excel(path, sheet_name='Calculo', skiprows=2, nrows=10)
    # Remove unnamed columns if possible or just print them
    print(df_calc.columns.tolist())
    # Display columns related to phenology states
    states_cols = [c for c in df_calc.columns if any(s in str(c) for s in ['Boton', 'Flor', 'Verde', 'Cosechable'])]
    print(f"\nFound {len(states_cols)} state-related columns.")
    print(df_calc[['Sem', 'CC'] + states_cols[:10]].head())

if __name__ == "__main__":
    inspect_calculo()
