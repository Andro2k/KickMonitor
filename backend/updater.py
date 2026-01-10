# backend/updater.py
import json
import sys
import os
import subprocess
import requests
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version 

# --- CORRECCIÓN 1: Rutas Robustas ---
def get_base_path():
    """Devuelve la ruta base correcta tanto en DEV como en EXE (Frozen)"""
    if getattr(sys, 'frozen', False):
        # Si es EXE (PyInstaller)
        return sys._MEIPASS
    else:
        # Si es DEV (Python script), asumimos que updater.py está en /backend
        # y queremos ir a la raiz del proyecto
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_local_version():
    """Lee la versión desde el archivo version.json"""
    try:
        base_path = get_base_path()
        path = os.path.join(base_path, "version.json")
        
        # DEBUG: Imprimir ruta para verificar si falla
        # print(f"[DEBUG] Buscando version.json en: {path}")

        if not os.path.exists(path):
            return "0.0.0"

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception as e:
        print(f"Error leyendo versión local: {e}")
        return "0.0.0"

CURRENT_VERSION = get_local_version()
UPDATE_JSON_URL = "https://raw.githubusercontent.com/Andro2k/KickMonitor/refs/heads/main/version.json"

# --- WORKER CHECKER (Sin cambios mayores, solo validación) ---
class UpdateCheckerWorker(QThread):
    update_available = pyqtSignal(str, str, str)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            resp = requests.get(UPDATE_JSON_URL, timeout=10)
            if resp.status_code != 200:
                self.error.emit("No se pudo conectar al servidor.")
                return

            data = resp.json()
            remote_ver = data.get("version", "0.0.0")
            url = data.get("url", "")
            changelog = data.get("changelog", "")

            # Comparamos versiones
            print(f"[SYSTEM] Local: {CURRENT_VERSION} vs Remota: {remote_ver}") # Log para debug
            
            if version.parse(remote_ver) > version.parse(CURRENT_VERSION):
                self.update_available.emit(remote_ver, url, changelog)
            else:
                self.no_update.emit()

        except Exception as e:
            self.error.emit(f"Error buscando: {str(e)}")

# --- WORKER DOWNLOADER (Corrección del lanzador) ---
class UpdateDownloaderWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, download_url):
        super().__init__()
        self.url = download_url
        self.installer_path = ""

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            # Usamos un nombre fijo para evitar basura, o dinámico si prefieres
            self.installer_path = os.path.join(temp_dir, "KickMonitor_Update.exe")

            with requests.get(self.url, stream=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                dl = 0
                
                with open(self.installer_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            dl += len(chunk)
                            f.write(chunk)
                            if total_length > 0:
                                percent = int((dl / total_length) * 100)
                                self.progress.emit(percent)

            self._launch_installer()
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _launch_installer(self):
        if os.path.exists(self.installer_path):
            print(f"[SYSTEM] Ejecutando instalador: {self.installer_path}")
            
            # --- CORRECCIÓN 2: Ejecución Visible y Desacoplada ---
            # Quitamos /VERYSILENT para que el usuario vea el instalador y pueda aceptar permisos de Admin.
            # Usamos ShellExecute (os.startfile) o Popen con shell=True para despegar el proceso.
            
            try:
                # Opción recomendada para Windows: os.startfile
                # Esto ejecuta el .exe como si le dieras doble clic.
                os.startfile(self.installer_path)
                
                # Cerramos la app actual para liberar archivos (DB, logs, etc)
                # Damos un pequeño respiro para asegurar que el comando salió
                QThread.msleep(500) 
                sys.exit(0)
                
            except Exception as e:
                print(f"Error lanzando instalador: {e}")
                self.error.emit(f"No se pudo abrir el instalador: {e}")