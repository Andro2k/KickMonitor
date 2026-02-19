# backend/workers/update_worker.py

import os
import subprocess
import sys
import requests
import tempfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from packaging import version 

# =========================================================================
# CONFIGURACIÓN DE VERSIÓN
# =========================================================================
INTERNAL_VERSION = "2.3.1"
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
            # Añadimos allow_redirects=True por seguridad
            with requests.get(self.url, stream=True, timeout=15, allow_redirects=True) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                dl = 0
                
                # Si el servidor no nos dice el peso, enviamos -1 a la interfaz
                if total_length == 0:
                    self.progress.emit(-1)
                
                with self.installer_path.open('wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            dl += len(chunk)
                            f.write(chunk)
                            if total_length > 0:
                                self.progress.emit(int((dl / total_length) * 100))

            self._launch_installer()
            self.finished.emit()

        except Exception as e:
            # Si hubo un error y el archivo se quedó a medias, lo borramos
            if self.installer_path.exists():
                try:
                    self.installer_path.unlink()
                except:
                    pass
            self.error.emit(f"Error en descarga: {e}")

    def _launch_installer(self):
        """
        Genera un script temporal (.bat) que espera a que la app se cierre 
        antes de ejecutar el instalador.
        """
        if not self.installer_path.exists():
            self.error.emit("El instalador no se encontró en la ruta temporal.")
            return

        # Obtener el nombre del ejecutable actual (ej. KickMonitor.exe)
        current_exe = os.path.basename(sys.executable)

        # Crear el contenido del script Batch
        bat_content = f"""@echo off
    title Actualizando KickMonitor...
    echo.
    echo ===================================================
    echo     Preparando la actualizacion de KickMonitor
    echo ===================================================
    echo.
    echo Esperando a que la aplicacion se cierre de forma segura...
    timeout /t 3 /nobreak > NUL

    :: Forzar el cierre por si algun worker se quedo colgado
    taskkill /f /im "{current_exe}" > NUL 2>&1

    echo.
    echo Iniciando el instalador...
    start "" "{self.installer_path}"

    :: Autodestruir este script .bat despues de usarlo
    del "%~f0"
    """
        
        # Guardar el script en la carpeta temporal
        bat_path = Path(tempfile.gettempdir()) / "updater_kickmonitor.bat"
        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            # Lanzar el script de forma totalmente independiente a este proceso de Python
            subprocess.Popen(
                [str(bat_path)], 
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        except Exception as e:
            self.error.emit(f"No se pudo crear el actualizador temporal: {e}")