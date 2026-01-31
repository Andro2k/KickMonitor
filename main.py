# main.py

import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from frontend.main_window import MainWindow
from frontend.utils import resource_path

if sys.platform.startswith('win'):
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

if not hasattr(sys, '_MEIPASS'):
    pass

myappid = 'kickmonitor.v1.8.4.0' 
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

if __name__ == "__main__":
    app = QApplication(sys.argv)

    mutex_id = "3E28ED4F-E3D1-466D-8140-E080992D5092"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_id)
    
    if ctypes.windll.kernel32.GetLastError() == 183:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("KickMonitor")
        msg.setText("La aplicación ya se está ejecutando.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setWindowIcon(QIcon(resource_path("icon.ico"))) 
        msg.exec()
        sys.exit(0)

    app.setWindowIcon(QIcon(resource_path("icon.ico")))
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())