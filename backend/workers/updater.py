# backend/updater.py
import subprocess
import sys
import os
import requests
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version 

# =========================================================================
# CONFIGURACIÓN DE VERSIÓN
# =========================================================================
INTERNAL_VERSION = "1.8.1"
CURRENT_VERSION = INTERNAL_VERSION
UPDATE_JSON_URL = "https://raw.githubusercontent.com/Andro2k/KickMonitor/refs/heads/main/version.json"

# =========================================================================
# WORKER 1: VERIFICADOR DE ACTUALIZACIONES
# =========================================================================
class UpdateCheckerWorker(QThread):
    update_available = pyqtSignal(str, str, str)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            # 1. Consultar JSON remoto
            # print(f"[UPDATER] Buscando actualizaciones en: {UPDATE_JSON_URL}")
            resp = requests.get(UPDATE_JSON_URL, timeout=10)
            
            if resp.status_code != 200:
                self.error.emit(f"Error servidor: {resp.status_code}")
                return

            data = resp.json()
            remote_ver = data.get("version", "0.0.0")
            url = data.get("url", "")
            changelog = data.get("changelog", "")

            # 2. Comparar versiones
            if version.parse(remote_ver) > version.parse(CURRENT_VERSION):
                # print(f"[UPDATER] Actualización encontrada: {remote_ver}")
                self.update_available.emit(remote_ver, url, changelog)
            else:
                # print(f"[UPDATER] Sistema actualizado ({CURRENT_VERSION})")
                self.no_update.emit()

        except Exception as e:
            # print(f"[UPDATER] Error check: {e}")
            self.error.emit(f"Error de conexión: {str(e)}")

# =========================================================================
# WORKER 2: DESCARGADOR E INSTALADOR
# =========================================================================
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
            # 1. Preparar ruta temporal
            temp_dir = tempfile.gettempdir()
            self.installer_path = os.path.join(temp_dir, "KickMonitor_Update.exe")
            # print(f"[UPDATER] Descargando en: {self.installer_path}")

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

            # 3. Lanzar instalación
            self._launch_installer()
            self.finished.emit()

        except Exception as e:
            # print(f"[UPDATER] Error download: {e}")
            self.error.emit(f"Error en descarga: {str(e)}")

    def _launch_installer(self):
        """Ejecuta el instalador de forma independiente y cierra la app actual."""
        if os.path.exists(self.installer_path):
            # print(f"[UPDATER] Ejecutando instalador.")
            
            try:
                # 2. FIX PARA PYINSTALLER:
                # 'close_fds=True' y 'shell=True' ayudan a desvincular el proceso.
                subprocess.Popen([self.installer_path], shell=True, close_fds=True)
                
                # Damos un pequeño respiro para asegurar que el comando se envió al SO
                QThread.msleep(1000) 
                
                # Cerramos la aplicación
                sys.exit(0)
                
            except Exception as e:
                # print(f"[UPDATER] Error lanzando EXE: {e}")
                self.error.emit(f"No se pudo abrir el instalador: {e}")
        else:
            self.error.emit("El archivo descargado no existe.")