
import pandas as pd

def inspect_excel():
    path = r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\39. Proyecciones Semana 5 + 5 semanas (Conteo S3).xlsx"
    xl = pd.ExcelFile(path)
    print(f"Sheets: {xl.sheet_names}")
    
    for sheet in xl.sheet_names[:3]: # Let's look at the first few sheets
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(path, sheet_name=sheet, nrows=10)
        print(df.head())
        print(f"Columns: {df.columns.tolist()}")

if __name__ == "__main__":
    inspect_excel()
