# main.py

import os
import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QComboBox, QSlider, QAbstractSpinBox
from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtGui import QIcon

from frontend.main_window import MainWindow
from frontend.utils import resource_path
# IMPORTAMOS LA NUEVA ALERTA
from frontend.alerts.startup_alert import AlreadyRunningDialog 

class LockWheelFilter(QObject):
    """
    Filtro global para evitar que el scroll del mouse cambie accidentalmente
    los valores de ComboBoxes, Sliders y SpinBoxes si no tienen el foco.
    """
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QComboBox, QSlider, QAbstractSpinBox)):
                if not obj.hasFocus():
                    event.ignore()
                    return True
        return super().eventFilter(obj, event)

def setup_environment():
    """Configura el entorno del sistema operativo y salidas estándar."""
    if sys.platform.startswith('win'):
        if sys.stdin is None: sys.stdin = open(os.devnull, "r")
        if sys.stdout is None: sys.stdout = open(os.devnull, "w")
        if sys.stderr is None: sys.stderr = open(os.devnull, "w")

    myappid = 'kickmonitor.v2.3.0' 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

def try_create_mutex():
    """
    Intenta crear el mutex y retorna (mutex_handle, ya_existe).
    """
    mutex_id = "3E28ED4F-E3D1-466D-8140-E080992D5092"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_id)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    # Error 183 significa ERROR_ALREADY_EXISTS
    return mutex, (last_error == 183)

def main():
    setup_environment()
    
    # IMPORTANTE: QApplication debe crearse ANTES de mostrar cualquier widget
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))

    # 1. Verificación de Instancia Única
    _mutex, already_running = try_create_mutex()
    
    if already_running:
        # Mostramos la nueva ventana personalizada
        alert = AlreadyRunningDialog()
        alert.exec()
        sys.exit(0)
    
    # 2. Instalación de filtros globales
    wheel_filter = LockWheelFilter()
    app.installEventFilter(wheel_filter)
    
    # 3. Inicio normal de la aplicación
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()