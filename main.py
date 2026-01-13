# main.py

import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow
from ui.utils import resource_path

if sys.platform.startswith('win'):
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

if not hasattr(sys, '_MEIPASS'):
    pass

# Configurar ID de Windows para la barra de tareas
myappid = 'kickmonitor.v1.8.0' 
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- PROTECCIÓN DE INSTANCIA ÚNICA (NUEVO) ---
    # Creamos un identificador único. Si cambias de versión, puedes mantenerlo igual.
    mutex_id = "3E28ED4F-E3D1-466D-8140-E080992D5092"
    
    # Intentamos crear el Mutex en el Kernel de Windows
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_id)
    
    # Si el error es 183 (ERROR_ALREADY_EXISTS), ya hay una instancia abierta
    if ctypes.windll.kernel32.GetLastError() == 183:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("KickMonitor")
        msg.setText("La aplicación ya se está ejecutando.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowIcon(QIcon(resource_path("icon.ico"))) 
        msg.exec()
        sys.exit(0)
    # ---------------------------------------------

    # Cargar icono de la aplicación
    basedir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(basedir, "icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())