# backend/updater.py
import json
import sys
import os
import subprocess
import requests
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version # Recomendado: pip install packaging

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, funciona para dev y PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_local_version():
    """Lee la versión desde el archivo version.json incluido en el EXE"""
    try:
        path = get_resource_path("version.json")
        with open(path, 'r') as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception as e:
        print(f"Error leyendo versión local: {e}")
        return "0.0.0"

# --- CAMBIO AQUÍ ---
# Ya no escribimos el número a mano:
CURRENT_VERSION = get_local_version()
# URL RAW donde tienes tu json (ejemplo GitHub)
UPDATE_JSON_URL = "https://raw.githubusercontent.com/Andro2k/KickMonitor/refs/heads/main/version.json"

class UpdateCheckerWorker(QThread):
    update_available = pyqtSignal(str, str, str) # version, url, changelog
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            # 1. Consultar versión remota
            resp = requests.get(UPDATE_JSON_URL, timeout=10)
            if resp.status_code != 200:
                self.error.emit("No se pudo conectar al servidor de actualizaciones.")
                return

            data = resp.json()
            remote_ver = data.get("version", "0.0.0")
            url = data.get("url", "")
            changelog = data.get("changelog", "")

            # 2. Comparar versiones
            if version.parse(remote_ver) > version.parse(CURRENT_VERSION):
                self.update_available.emit(remote_ver, url, changelog)
            else:
                self.no_update.emit()

        except Exception as e:
            self.error.emit(f"Error buscando actualizaciones: {str(e)}")

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
            # 1. Crear ruta temporal para el instalador
            temp_dir = tempfile.gettempdir()
            self.installer_path = os.path.join(temp_dir, "KickMonitor_Update.exe")

            # 2. Descargar con stream para barra de progreso
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

            # 3. Ejecutar instalador y cerrar app
            self._launch_installer()
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _launch_installer(self):
        if os.path.exists(self.installer_path):
            # subprocess.Popen lanza el proceso y NO espera a que termine
            subprocess.Popen([self.installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
            # CERRAR LA APP ACTUAL INMEDIATAMENTE
            # Esto es vital para que el instalador pueda sobrescribir el .exe
            sys.exit(0)