import os
import time
import sys
from sqlalchemy import text

# Configurar path para importar desde el backend
sys.path.append(os.path.abspath("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/backend"))

try:
    from nucleo.conexion import obtener_engine
    from repositorios.repo_catalogos import listar_geografia, listar_variedades
    from repositorios.repo_cuarentena import listar_pendientes
    
    engine = obtener_engine()
    
    print("--- 🔍 TEST DE RENDIMIENTO Y CORRECTITUD (DB OPTIMIZED) ---")
    
    # 1. Test Geografía (Paginación + NOLOCK)
    inicio = time.perf_counter()
    res_geo = listar_geografia(pagina=1, tamano=10)
    fin = time.perf_counter()
    print(f"✅ Listar Geografía (pag 1): {res_geo['total']} registros totales.")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")
    assert "total" in res_geo and "datos" in res_geo
    assert len(res_geo["datos"]) <= 10
    
    # 2. Test Variedades (Paginación + NOLOCK)
    inicio = time.perf_counter()
    res_var = listar_variedades(pagina=1, tamano=5)
    fin = time.perf_counter()
    print(f"✅ Listar Variedades (pag 1): {res_var['total']} registros totales.")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")
    
    # 3. Test Cuarentena (Refactorizado con COUNT OVER)
    inicio = time.perf_counter()
    res_cuar = listar_pendientes(pagina=1, tamano=10)
    fin = time.perf_counter()
    print(f"✅ Listar Cuarentena (pendientes): {res_cuar['total']} registros.")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")
    
    print("\n--- 🧠 TEST MOTOR DE PROYECCIONES (NOLOCK) ---")
    sys.path.append(os.path.abspath("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/acp_mdm_portal"))
    from utils.motor_proyecciones import obtener_fechas_disponibles
    
    inicio = time.perf_counter()
    fechas = obtener_fechas_disponibles()
    fin = time.perf_counter()
    print(f"✅ Fechas disponibles (NOLOCK): {len(fechas)} fechas encontradas.")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")
    
    print("\n🚀 Todos los tests pasaron exitosamente.")

except Exception as e:
    print(f"\n❌ Error durante el test: {e}")
    import traceback
    traceback.print_exc()
