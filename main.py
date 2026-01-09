# main.py

import os
import sys
import ctypes  # <--- 1. NECESARIO PARA WINDOWS
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon  # <--- 2. NECESARIO PARA EL ICONO

from ui.main_window import MainWindow
from ui.utils import resource_path  # <--- 3. IMPORTAMOS TU FUNCIÓN DE RUTAS

# --- FIX PARA "LOST SYS.STDIN" Y "ATTRIBUTE ERROR" ---
if sys.platform.startswith('win'):
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

if not hasattr(sys, '_MEIPASS'):
    pass

myappid = 'kickmonitor.bot.v2.0' 
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = resource_path("icon.png") 
    app.setWindowIcon(QIcon(icon_path))
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())