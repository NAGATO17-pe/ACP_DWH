import sys
import shutil
from pathlib import Path

# Add project root to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.conexion import obtener_engine
from bronce.cargador import ejecutar_carga_bronce
from sqlalchemy import text

def test_ingestion():
    # 1. Define paths
    excel_source = ROOT.parent / "reporte_Conteo_de_Fruta.xlsx"
    dest_dir = ROOT / "data" / "entrada" / "conteo_fruta"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "reporte_Conteo_de_Fruta.xlsx"

    print(f"Source file: {excel_source} (exists: {excel_source.exists()})")
    print(f"Destination: {dest_file}")

    # Copy excel file to input folder
    shutil.copy2(str(excel_source), str(dest_file))
    print("Copied successfully.")

    # 2. Run Bronze ingestion
    print("\n--- Running Bronze Ingestion ---")
    resultados = ejecutar_carga_bronce()
    print("Results:")
    for r in resultados:
        print(f"  File: {r.get('archivo')} | Table: {r.get('tabla')} | Rows: {r.get('filas')} | Status: {r.get('estado')} | Msg: {r.get('mensaje')}")

    # 3. Check physical DB data
    print("\n--- Verifying Database Rows in Bronce.Conteo_Fruta ---")
    engine = obtener_engine()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT COUNT(*) AS total_rows, 
                   COUNT(BotonesFlorales_Raw) AS rows_with_botones,
                   COUNT(Flores_Raw) AS rows_with_flores,
                   COUNT(BayasPequenas_Raw) AS rows_with_bayas_peq
            FROM Bronce.Conteo_Fruta
            WHERE Nombre_Archivo LIKE 'reporte_Conteo_de_Fruta%'
        """)).fetchone()
        
        print(f"Total rows inserted: {res[0]}")
        print(f"Rows with BotonesFlorales_Raw: {res[1]}")
        print(f"Rows with Flores_Raw: {res[2]}")
        print(f"Rows with BayasPequenas_Raw: {res[3]}")

        if res[0] > 0:
            print("\nSample row:")
            row = conn.execute(text("""
                SELECT TOP 1 Fecha_Raw, DNI_Raw, Nombres_Raw, Modulo_Raw, Turno_Raw, Valvula_Raw, Variedad_Raw, Punto_Raw, Tipo_Evaluacion_Raw, BotonesFlorales_Raw, Flores_Raw, BayasPequenas_Raw, BayasGrandes_Raw, Fase1_Raw, Fase2_Raw, BayasCremas_Raw, BayasMaduras_Raw, BayasCosechables_Raw, YemasActivadas_Raw, PlantasProductivas_Raw, PlantasNoProductivas_Raw, Muestras_Raw
                FROM Bronce.Conteo_Fruta
                WHERE Nombre_Archivo LIKE 'reporte_Conteo_de_Fruta%'
            """)).fetchone()
            keys = ['Fecha_Raw', 'DNI_Raw', 'Nombres_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw', 'Punto_Raw', 'Tipo_Evaluacion_Raw', 'BotonesFlorales_Raw', 'Flores_Raw', 'BayasPequenas_Raw', 'BayasGrandes_Raw', 'Fase1_Raw', 'Fase2_Raw', 'BayasCremas_Raw', 'BayasMaduras_Raw', 'BayasCosechables_Raw', 'YemasActivadas_Raw', 'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw', 'Muestras_Raw']
            for k, v in zip(keys, row):
                print(f"  {k}: {v}")

if __name__ == "__main__":
    test_ingestion()
