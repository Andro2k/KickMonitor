# frontend/components/tray_icon.py

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from frontend.utils import resource_path

class TrayIcon(QSystemTrayIcon):
    """Maneja el icono en la barra de tareas y sus notificaciones."""
    
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.main_window = parent_window

        self.icon_path = resource_path("icon.ico")
        self.setIcon(QIcon(self.icon_path))
        
        self._setup_menu()
        self.activated.connect(self._on_activated)
        self.show()

    def _setup_menu(self):
        tray_menu = QMenu()
        
        action_show = QAction("Mostrar Monitor", self)
        action_show.triggered.connect(self.show_window)

        action_quit = QAction("Cerrar Totalmente", self)
        action_quit.triggered.connect(self.force_close)
        
        tray_menu.addAction(action_show)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)
        
        self.setContextMenu(tray_menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def force_close(self):
        self.hide()
        QApplication.quit()

    def show_minimized_notification(self):
        """Muestra la burbuja de notificación nativa del SO."""
        custom_icon = QIcon(self.icon_path)
        
        self.showMessage(
            "Kick Monitor",
            "Ejecutándose en segundo plano.",
            custom_icon,
            2000
        )