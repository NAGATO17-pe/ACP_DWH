
import pandas as pd

def inspect_excel_more():
    path = r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx"
    
    print("\n--- Sheet: Pesos ---")
    df_pesos = pd.read_excel(path, sheet_name='Pesos', nrows=10)
    print(df_pesos.head())
    
    print("\n--- Sheet: Calculo ---")
    df_calc = pd.read_excel(path, sheet_name='Calculo', nrows=10)
    print(df_calc.head())

    print("\n--- Sheet: Proyección Turno (Skipping rows) ---")
    # Proyección Turno seems to have headers at row 3 (0-indexed)
    df_proy = pd.read_excel(path, sheet_name='Proyeccin Turno', skiprows=3, nrows=10)
    print(df_proy.columns.tolist())
    print(df_proy.head())

if __name__ == "__main__":
    inspect_excel_more()
