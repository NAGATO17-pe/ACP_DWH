
from config.conexion import obtener_engine
from sqlalchemy import text

def reset():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("Reseteando registros de Bronce.Maduracion...")
        res = conn.execute(text("UPDATE Bronce.Maduracion SET Estado_Carga = 'CARGADO' WHERE Estado_Carga = 'RECHAZADO'"))
        conn.commit()
        print(f"Filas actualizadas: {res.rowcount}")

if __name__ == "__main__":
    reset()
