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
INTERNAL_VERSION = "2.3.2"
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
        Genera un script temporal (.bat) y un (.vbs) para ejecutar la instalación
        de forma 100% invisible y esperando el cierre natural de la app.
        """
        if not self.installer_path.exists():
            self.error.emit("El instalador no se encontró en la ruta temporal.")
            return

        current_exe = os.path.basename(sys.executable)
        temp_dir = tempfile.gettempdir()
        
        bat_path = Path(temp_dir) / "updater_kickmonitor.bat"
        vbs_path = Path(temp_dir) / "updater_hidden.vbs"

        # 1. El script Batch con espera amable (sin matar el proceso de golpe)
        bat_content = f"""@echo off
        :: Espera 2 segundos para permitir el cierre natural de la app
        timeout /t 2 /nobreak > NUL

        :: Bucle para esperar que el proceso desaparezca (maximo 10 segundos)
        set retries=0
        :wait_loop
        tasklist /fi "imagename eq {current_exe}" | find /i "{current_exe}" > NUL
        if %errorlevel% equ 0 (
            timeout /t 1 /nobreak > NUL
            set /a retries+=1
            if %retries% lss 10 goto wait_loop
            
            :: Si despues de 10 segundos sigue abierto, entonces si forzamos cierre
            taskkill /f /im "{current_exe}" > NUL 2>&1
        )

        :: Iniciar el instalador de la nueva version
        start "" "{self.installer_path}"

        :: Limpiar los archivos temporales
        del "{vbs_path}"
        del "%~f0"
        """
        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            # 2. El VBScript para ejecutar el .bat sin mostrar ventana CMD
            vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run chr(34) & "{bat_path}" & chr(34), 0, False'
            with open(vbs_path, "w") as f:
                f.write(vbs_content)

            # 3. Lanzar el VBScript de forma separada
            # 0x08000008 = DETACHED_PROCESS | CREATE_NO_WINDOW
            # close_fds=True es CRUCIAL para evitar el error de Python DLL
            subprocess.Popen(
                ["wscript.exe", str(vbs_path)], 
                creationflags=0x08000008,
                close_fds=True 
            )
        except Exception as e:
            self.error.emit(f"No se pudo crear el actualizador invisible: {e}")