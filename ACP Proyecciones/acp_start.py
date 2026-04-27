"""
ACP Platform - Lanzador Unificado
Doble clic en acp_start.bat o ejecutar: python acp_start.py
"""

import subprocess
import sys
import os
import time
import signal
import threading
import urllib.request
import urllib.error
import webbrowser
import ctypes
from pathlib import Path
from datetime import datetime

# ─── Colores ANSI ───────────────────────────────────────────────────────────
# Activar colores en Windows 10+
if sys.platform == "win32":
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BG_BLUE = "\033[44m"

# ─── Configuración de servicios ──────────────────────────────────────────────
BASE = Path(__file__).parent
VENV = BASE / ".venv" / "Scripts"

SERVICIOS = [
    {
        "nombre":   "Backend FastAPI",
        "icono":    "⚙",
        "cmd":      [str(VENV / "uvicorn.exe"), "main:aplicacion",
                     "--host", "0.0.0.0", "--port", "8000"],
        "cwd":      BASE / "backend",
        "health":   "http://localhost:8000/health/live",
        "url":      "http://localhost:8000/docs",
        "log":      BASE / "backend" / "logs" / "backend.log",
        "puerto":   8000,
        "color":    BLUE,
        "proceso":  None,
    },
    {
        "nombre":   "Runner ETL",
        "icono":    "⚡",
        "cmd":      [str(VENV / "python.exe"), "-m", "runner.runner"],
        "cwd":      BASE / "backend",
        "health":   None,
        "url":      None,
        "log":      BASE / "backend" / "logs" / "runner.log",
        "puerto":   None,
        "color":    YELLOW,
        "proceso":  None,
    },
    {
        "nombre":   "Portal MDM",
        "icono":    "🌐",
        "cmd":      [str(VENV / "streamlit.exe"), "run", "app.py",
                     "--server.port", "8501",
                     "--server.headless", "true"],
        "cwd":      BASE / "acp_mdm_portal",
        "health":   "http://localhost:8501/_stcore/health",
        "url":      "http://localhost:8501",
        "log":      BASE / "backend" / "logs" / "portal.log",
        "puerto":   8501,
        "color":    CYAN,
        "proceso":  None,
    },
]

PROCESOS_ACTIVOS = []  # para cleanup en Ctrl+C

# ─── Helpers de UI ───────────────────────────────────────────────────────────

def limpiar():
    os.system("cls" if sys.platform == "win32" else "clear")


def banner():
    print(f"""
{BOLD}{BG_BLUE}                                                        {RESET}
{BOLD}{BG_BLUE}    ACP PLATFORM  -  Lanzador Unificado de Servicios    {RESET}
{BOLD}{BG_BLUE}                                                        {RESET}
{DIM}    Proyecto: ACP Data Warehouse | Entorno: DEV          {RESET}
""")


def linea(char="─", ancho=54):
    print(f"  {DIM}{char * ancho}{RESET}")


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg, nivel="INFO"):
    colores = {"INFO": GREEN, "WARN": YELLOW, "ERR": RED, "OK": GREEN}
    c = colores.get(nivel, WHITE)
    print(f"  {DIM}[{ts()}]{RESET} {c}{nivel:4}{RESET}  {msg}")


def puerto_en_uso(puerto: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def health_check(url: str, intentos: int = 1) -> bool:
    for _ in range(intentos):
        try:
            req = urllib.request.urlopen(url, timeout=3)
            return req.status < 500
        except Exception:
            time.sleep(1)
    return False


# ─── Inicio de servicios ─────────────────────────────────────────────────────

def iniciar_servicio(svc: dict) -> bool:
    nombre = svc["nombre"]
    color  = svc["color"]

    # Verificar si puerto ya está en uso
    if svc["puerto"] and puerto_en_uso(svc["puerto"]):
        log(f"{color}{nombre}{RESET}  puerto {svc['puerto']} ya ocupado — omitido", "WARN")
        return True

    # Crear carpeta de logs
    svc["log"].parent.mkdir(parents=True, exist_ok=True)

    log(f"Iniciando  {color}{nombre}{RESET} ...", "INFO")

    log_file = open(svc["log"], "a", encoding="utf-8")
    log_file.write(f"\n{'='*60}\n[{datetime.now()}] INICIO\n{'='*60}\n")
    log_file.flush()

    proc = subprocess.Popen(
        svc["cmd"],
        cwd=str(svc["cwd"]),
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    svc["proceso"] = proc
    PROCESOS_ACTIVOS.append((proc, log_file))
    return True


def esperar_health(svc: dict, timeout: int = 30) -> bool:
    if not svc["health"]:
        time.sleep(2)
        return svc["proceso"] is not None and svc["proceso"].poll() is None

    nombre = svc["nombre"]
    color  = svc["color"]
    print(f"  {DIM}         Esperando {color}{nombre}{RESET}{DIM} (max {timeout}s)...{RESET}", end="", flush=True)

    for i in range(timeout):
        if svc["proceso"] and svc["proceso"].poll() is not None:
            print(f"  {RED}FALLO{RESET}")
            return False
        if health_check(svc["health"]):
            print(f"  {GREEN}OK ({i+1}s){RESET}")
            return True
        time.sleep(1)
        if i % 5 == 4:
            print(".", end="", flush=True)

    print(f"  {YELLOW}TIMEOUT{RESET}")
    return False


# ─── Dashboard de estado ─────────────────────────────────────────────────────

def mostrar_estado():
    linea()
    print(f"\n  {'SERVICIO':<20} {'ESTADO':<12} {'PID':<8} {'URL'}")
    linea()
    for svc in SERVICIOS:
        proc  = svc["proceso"]
        color = svc["color"]
        nombre = f"{svc['icono']} {svc['nombre']}"

        if proc is None:
            estado = f"{RED}DETENIDO{RESET}"
            pid    = "─"
            url    = "─"
        elif proc.poll() is not None:
            estado = f"{RED}CAIDO   {RESET}"
            pid    = str(proc.pid)
            url    = "─"
        else:
            alive  = svc["health"] is None or health_check(svc["health"])
            estado = f"{GREEN}ACTIVO  {RESET}" if alive else f"{YELLOW}INICIANDO{RESET}"
            pid    = str(proc.pid)
            url    = svc["url"] or "─"

        print(f"  {color}{nombre:<20}{RESET} {estado:<20} {DIM}{pid:<8}{RESET} {CYAN}{url}{RESET}")
    print()


# ─── Apagado limpio ──────────────────────────────────────────────────────────

def detener_todo():
    log("Deteniendo todos los servicios...", "INFO")
    for proc, log_file in PROCESOS_ACTIVOS:
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        finally:
            try:
                log_file.close()
            except Exception:
                pass
    log("Servicios detenidos.", "OK")


def handler_sigint(sig, frame):
    print()
    log("Interrupción recibida (Ctrl+C)", "WARN")
    detener_todo()
    sys.exit(0)


signal.signal(signal.SIGINT, handler_sigint)

# ─── Menú interactivo ────────────────────────────────────────────────────────

def menu():
    while True:
        linea()
        print(f"\n  {BOLD}Comandos:{RESET}  "
              f"{GREEN}[S]{RESET} Status   "
              f"{BLUE}[L]{RESET} Logs   "
              f"{YELLOW}[R]{RESET} Restart   "
              f"{RED}[Q]{RESET} Salir\n")
        try:
            cmd = input(f"  {BOLD}>{RESET} ").strip().upper()
        except EOFError:
            cmd = "Q"

        if cmd == "S":
            mostrar_estado()
        elif cmd == "L":
            mostrar_logs()
        elif cmd == "R":
            log("Reiniciando servicios...", "WARN")
            detener_todo()
            PROCESOS_ACTIVOS.clear()
            for svc in SERVICIOS:
                svc["proceso"] = None
            time.sleep(2)
            arrancar_servicios()
        elif cmd == "Q":
            detener_todo()
            print(f"\n  {DIM}Hasta luego.{RESET}\n")
            sys.exit(0)
        else:
            print(f"  {DIM}Comando no reconocido.{RESET}")


def mostrar_logs(lineas: int = 15):
    for svc in SERVICIOS:
        color = svc["color"]
        print(f"\n  {color}── {svc['nombre']} ──{RESET}")
        if svc["log"].exists():
            try:
                with open(svc["log"], encoding="utf-8", errors="replace") as f:
                    todas = f.readlines()
                    for l in todas[-lineas:]:
                        print(f"  {DIM}{l.rstrip()}{RESET}")
            except Exception as e:
                print(f"  {RED}Error leyendo log: {e}{RESET}")
        else:
            print(f"  {DIM}(sin log todavía){RESET}")


# ─── Flujo principal ─────────────────────────────────────────────────────────

def arrancar_servicios():
    print()
    for svc in SERVICIOS:
        iniciar_servicio(svc)

    print()
    linea()
    print(f"  {BOLD}Verificando health checks...{RESET}\n")

    resultados = {}
    for svc in SERVICIOS:
        ok = esperar_health(svc, timeout=35)
        resultados[svc["nombre"]] = ok

    linea()
    print()
    mostrar_estado()

    # Abrir navegador solo si los servicios críticos levantaron
    if resultados.get("Backend FastAPI") and resultados.get("Portal MDM"):
        log("Abriendo navegador...", "INFO")
        time.sleep(1)
        webbrowser.open("http://localhost:8501")
    elif resultados.get("Backend FastAPI"):
        webbrowser.open("http://localhost:8000/docs")
    else:
        log("Algunos servicios no respondieron. Revisa los logs.", "WARN")


def main():
    limpiar()
    banner()

    # Verificar que el venv existe
    if not VENV.exists():
        print(f"  {RED}ERROR: No se encontró el entorno virtual en:{RESET}")
        print(f"  {DIM}{VENV}{RESET}")
        print(f"\n  {YELLOW}Crea el venv con:{RESET}  python -m venv .venv")
        print(f"  {YELLOW}Instala deps con:{RESET}   .venv\\Scripts\\pip install -r requirements.txt\n")
        input("  Presiona Enter para salir...")
        sys.exit(1)

    # Verificar .env
    env_raiz = BASE / ".env"
    if not env_raiz.exists():
        log("Archivo .env no encontrado en la raíz del proyecto.", "WARN")

    log("Iniciando ACP Platform...", "INFO")
    print()

    arrancar_servicios()
    menu()


if __name__ == "__main__":
    main()
