# backend/workers/update_worker.py

import subprocess
import os
import requests
import tempfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version 

# =========================================================================
# CONFIGURACIÓN DE VERSIÓN
# =========================================================================
INTERNAL_VERSION = "1.9.1.0"
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
            
            # TRUCO 1: Lanza una excepción si el status no es 200 (OK), mandándolo al bloque 'except'
            resp.raise_for_status()

            data = resp.json()
            remote_ver = data.get("version", "0.0.0.0")

            # 2. Comparar versiones
            if version.parse(remote_ver) > version.parse(INTERNAL_VERSION):
                self.update_available.emit(remote_ver, data.get("url", ""), data.get("changelog", ""))
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
        # TRUCO 2: Uso de Pathlib para crear la ruta cruzando sistemas operativos
        self.installer_path = Path(tempfile.gettempdir()) / "KickMonitor_Update.exe"

    def run(self):
        try:
            # Descargar con stream para barra de progreso
            with requests.get(self.url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                dl = 0
                
                # TRUCO 3: Abrimos el archivo directamente desde el objeto Path
                with self.installer_path.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            dl += len(chunk)
                            f.write(chunk)
                            if total_length > 0:
                                # Calculamos y emitimos el porcentaje
                                self.progress.emit(int((dl / total_length) * 100))

            # Lanzar instalación
            self._launch_installer()
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Error en descarga: {e}")

    def _launch_installer(self):
        """
        Ejecuta el instalador en un proceso independiente sin heredar 
        el entorno de PyInstaller para evitar errores de DLL.
        """
        if not self.installer_path.exists():
            return
            
        try:
            # TRUCO 4: Comprensión de Diccionarios (Dict Comprehension).
            # Clona TODO el entorno de Windows, PERO excluyendo las llaves tóxicas en una sola línea.
            forbidden_keys = {'_MEIPASS', 'PYTHONHOME', 'PYTHONPATH'}
            clean_env = {k: v for k, v in os.environ.items() if k not in forbidden_keys}

            # Lanzamos el instalador pasando la variable de entorno limpia
            subprocess.Popen([str(self.installer_path)], env=clean_env, shell=False, close_fds=True)
            
            # Matar la app actual inmediatamente para liberar el archivo .exe y permitir sobrescritura.
            os._exit(0) 
            
        except Exception as e:
            self.error.emit(f"No se pudo abrir el instalador: {e}")