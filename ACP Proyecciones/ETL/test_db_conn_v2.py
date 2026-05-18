import pyodbc
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el directorio padre
load_dotenv('../.env')

def test_connections():
    # Usar las claves correctas del .env
    server = os.getenv('ACP_DB_SERVER', 'LCP-PAG-PRACTIC')
    database = os.getenv('ACP_DB_DATABASE', 'ACP_DataWarehose_Proyecciones')
    trusted = os.getenv('ACP_DB_TRUSTED', 'True')

    print(f"Probando conexión TRUSTED a: {server} / {database}")
    
    conn_strings = [
        # 1. Original (TCP/IP) con Trusted Connection
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes",
        
        # 2. Shared Memory (LPC) - Más probable que funcione si TCP está desactivado
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=lpc:{server};DATABASE={database};Trusted_Connection=yes",
        
        # 3. Punto (Shared Memory)
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=.;DATABASE={database};Trusted_Connection=yes",
        
        # 4. Driver 18 with Trust Certificate (Required for v18 sometimes)
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes"
    ]

    for i, conn_str in enumerate(conn_strings, 1):
        print(f"\nTentativa {i}: {conn_str}")
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
            print(f"¡ÉXITO en tentativa {i}!")
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            print(f"Versión: {row[0]}")
            conn.close()
            return # Si uno funciona, paramos
        except Exception as e:
            print(f"FALLÓ tentativa {i}: {str(e)}")

if __name__ == "__main__":
    test_connections()
