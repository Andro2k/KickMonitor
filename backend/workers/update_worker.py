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
INTERNAL_VERSION = "1.8.4.0"
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
        """
        Ejecuta el instalador en un proceso totalmente independiente
        y sin heredar el entorno de PyInstaller para evitar el error de DLL.
        """
        if os.path.exists(self.installer_path):
            try:
                # 1. Copiamos el entorno actual del sistema
                env = os.environ.copy()

                # 2. ELIMINAMOS las variables que PyInstaller inyecta.
                # Esto es crucial: evita que el instalador busque en la carpeta _MEI incorrecta.
                keys_to_remove = ['_MEIPASS', 'PYTHONHOME', 'PYTHONPATH']
                for key in keys_to_remove:
                    if key in env:
                        del env[key]

                # 3. Lanzamos el instalador usando subprocess con el entorno limpio
                # close_fds=True ayuda a desconectar los procesos en algunos sistemas
                subprocess.Popen([self.installer_path], env=env, shell=False, close_fds=True)
                
                # 4. Matar la app actual inmediatamente para liberar el archivo .exe
                # y permitir que el instalador lo sobrescriba.
                os._exit(0) 
                
            except Exception as e:
                self.error.emit(f"No se pudo abrir el instalador: {e}")