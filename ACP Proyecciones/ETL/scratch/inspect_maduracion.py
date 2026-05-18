
from config.conexion import obtener_engine
from sqlalchemy import text

def inspect():
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT TOP 3 Valores_Raw FROM Bronce.Maduracion")).fetchall()
        for r in res:
            print("-" * 20)
            print(r[0])

if __name__ == "__main__":
    inspect()
