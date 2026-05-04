
import pandas as pd

def inspect_pesos():
    path = r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx"
    df = pd.read_excel(path, sheet_name='Pesos', skiprows=1, nrows=10)
    print(df.columns.tolist())
    print(df.head())

if __name__ == "__main__":
    inspect_pesos()
