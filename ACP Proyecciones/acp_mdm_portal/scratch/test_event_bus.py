"""
POC: Prueba de concepto del Bus de Eventos Zenith
===============================================
Este script simula un proceso del ETL emitiendo una señal al Backend.
"""
import sys
import os

# Añadir el path para que encuentre el backend
sys.path.append(os.path.join(os.getcwd(), "..", "backend"))

from servicios.event_bus import bus
import servicios.servicio_auditoria # Esto registra el listener

def simular_carga_fact():
    print("--- Simulando proceso de carga ETL ---")
    
    # El ETL emite la señal al terminar
    bus.task_finished.send(
        'ETL_PIPELINE', 
        tabla='Fact_Cosecha_SAP', 
        filas=1500, 
        mensaje='Carga de datos diarios completada'
    )

if __name__ == "__main__":
    simular_carga_fact()
