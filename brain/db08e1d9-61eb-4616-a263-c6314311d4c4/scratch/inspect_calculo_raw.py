
import pandas as pd

def inspect_calculo_raw():
    path = r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx"
    df = pd.read_excel(path, sheet_name='Calculo', header=None, nrows=10)
    print(df)

if __name__ == "__main__":
    inspect_calculo_raw()
