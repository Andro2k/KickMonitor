# frontend/components/tray_icon.py

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from frontend.utils import resource_path, get_icon_colored 

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
        # Usamos tu función get_icon_colored para cargar el SVG y pintarlo
        icon_show = get_icon_colored("home.svg", "#FFFFFF")
        action_show = QAction(icon_show, "Mostrar Monitor", self)
        action_show.triggered.connect(self.show_window)

        # --- OPCIÓN 2: Conectar Bot ---
        icon_connect = get_icon_colored("link.svg", "#53fc18")
        action_connect = QAction(icon_connect, "Conectar Bot", self)
        action_connect.triggered.connect(self._connect_bot)

        # --- OPCIÓN 3: Desconectar Bot ---
        icon_disconnect = get_icon_colored("unlink.svg", "#ffc107")
        action_disconnect = QAction(icon_disconnect, "Desconectar Bot", self)
        action_disconnect.triggered.connect(self._disconnect_bot)

        # --- OPCIÓN 4: Cerrar Aplicación ---
        icon_quit = get_icon_colored("power.svg", "#ff453a")
        action_quit = QAction(icon_quit, "Cerrar Totalmente", self)
        action_quit.triggered.connect(self.force_close)
        
        # --- AGREGAR AL MENÚ CON SEPARADORES ---
        tray_menu.addAction(action_show)
        tray_menu.addSeparator()
        tray_menu.addAction(action_connect)
        tray_menu.addAction(action_disconnect)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)
        
        self.setContextMenu(tray_menu)

    # ==========================================
    # HANDLERS DE LAS ACCIONES
    # ==========================================
    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _connect_bot(self):
        """Llama a la función del main_window para iniciar el bot si no está activo."""
        if hasattr(self.main_window, 'controller'):
            # Prevenir conexión si el worker ya existe y está corriendo
            if self.main_window.controller.worker is not None:
                return
            self.main_window.controller.start_bot()

    def _disconnect_bot(self):
        """Llama a la función del main_window para detener el bot."""
        if hasattr(self.main_window, 'controller'):
            # Prevenir desconexión si ya está desconectado
            if self.main_window.controller.worker is None:
                return
            self.main_window.controller.stop_bot()

    def force_close(self):
        self.hide()
        QApplication.quit()

    def show_minimized_notification(self):
        """Muestra la burbuja de notificación nativa del SO."""
        custom_icon = QIcon(self.icon_path)
        
        self.showMessage(
            "KickMonitor",
            "Ejecutándose en segundo plano. Haz clic derecho en este icono para ver más opciones.",
            custom_icon,
            3000
        )