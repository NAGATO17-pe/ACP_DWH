import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def inspect_variety():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("1. Buscando en MDM.Catalogo_Variedades:")
        query_cat = "SELECT * FROM MDM.Catalogo_Variedades"
        df_cat = pd.read_sql(text(query_cat), conn)
        df_cat_filtered = df_cat[df_cat.astype(str).apply(lambda x: x.str.contains('FCM15-005', case=False)).any(axis=1)]
        print(df_cat_filtered.to_string(index=False) if not df_cat_filtered.empty else "No encontrado en Catalogo.")

        print("\n2. Buscando en MDM.Diccionario_Homologacion:")
        query_dic = "SELECT * FROM MDM.Diccionario_Homologacion"
        df_dic = pd.read_sql(text(query_dic), conn)
        df_dic_filtered = df_dic[df_dic.astype(str).apply(lambda x: x.str.contains('FCM15-005', case=False)).any(axis=1)]
        print(df_dic_filtered.to_string(index=False) if not df_dic_filtered.empty else "No encontrado en Diccionario.")

        print("\n3. Buscando en MDM.Cuarentena:")
        query_cuar = "SELECT Tabla_Origen, Valor_Recibido, Motivo FROM MDM.Cuarentena"
        df_cuar = pd.read_sql(text(query_cuar), conn)
        df_cuar_filtered = df_cuar[df_cuar.astype(str).apply(lambda x: x.str.contains('FCM15-005', case=False)).any(axis=1)]
        if not df_cuar_filtered.empty:
            print(df_cuar_filtered.groupby(['Tabla_Origen', 'Valor_Recibido', 'Motivo']).size().reset_index(name='Casos').to_string(index=False))
        else:
            print("No hay casos en Cuarentena.")

if __name__ == "__main__":
    inspect_variety()
