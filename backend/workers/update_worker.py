# backend/updater.py

import subprocess
import os
import requests
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version 

# =========================================================================
# CONFIGURACIÓN DE VERSIÓN
# =========================================================================
INTERNAL_VERSION = "1.8.3.1"
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
            resp = requests.get(UPDATE_JSON_URL, timeout=10)
            
            if resp.status_code != 200:
                self.error.emit(f"Error servidor: {resp.status_code}")
                return

            data = resp.json()
            remote_ver = data.get("version", "0.0.0.0")
            url = data.get("url", "")
            changelog = data.get("changelog", "")

            # 2. Comparar versiones
            if version.parse(remote_ver) > version.parse(INTERNAL_VERSION):
                self.update_available.emit(remote_ver, url, changelog)
            else:
                self.no_update.emit()

        except Exception as e:
            print(f"[DEBUG_UPDATER] Error de conexión: {e}")
            self.error.emit("No se pudo verificar la actualización.")

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
            self.error.emit(f"Error en descarga: {str(e)}")

    def _launch_installer(self):
        """Ejecuta el instalador limpiando el entorno y mata la app actual."""
        if os.path.exists(self.installer_path):
            try:
                # --- SOLUCIÓN: Usar os.startfile ---
                # Funciona nativamente en Windows y no hereda el entorno corrupto de PyInstaller.
                os.startfile(self.installer_path)
                
                # Matar la app actual inmediatamente para liberar recursos
                os._exit(0) 
                
            except Exception as e:
                # Fallback por si acaso (aunque startfile raramente falla en Windows)
                self.error.emit(f"No se pudo abrir el instalador: {e}")