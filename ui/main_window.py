# ui/main_window.py
import ctypes
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFrame, QStackedWidget, QDialog, QButtonGroup
)
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QIcon

# Backend
from backend.controller import MainController

# Páginas
from ui.pages.alerts_page import AlertsPage
from ui.pages.dashboard_page import DashboardPage 
from ui.pages.chat_page import ChatPage
from ui.pages.settings_page import SettingsPage
from ui.pages.overlay_page import OverlayPage
from ui.pages.points_page import PointsPage
from ui.pages.commands_page import CommandsPage
from ui.pages.casino_page import GamblingPage 

# Componentes y Utilidades
from ui.utils import resource_path, get_icon
# --- CAMBIO 1: Eliminamos ICONS de la importación ---
from ui.theme import get_sheet, THEME_DARK
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.dialogs.username_input import UsernameInputDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()      
        self.setWindowTitle("Kick Monitor")
        self.resize(1100, 750)
        
        # 1. Controlador Central
        self.controller = MainController()
        
        # 2. Inicializar Interfaz
        self._init_pages()
        self.setup_ui()
        self._connect_signals()
        
        # 3. Estado Inicial
        self.controller.force_user_refresh()
        self.ui_home.refresh_data()
        self.ui_home.update_connection_state(False)
        
        # 4. Auto-Conexión
        if self.controller.db.get_bool("auto_connect"):
            QTimer.singleShot(1000, self.controller.start_bot)

    def _setup_app_id(self):
        try: 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('kick.monitor.bot.v2')
        except: 
            pass

    def _init_pages(self):
        """Instancia todas las páginas pasándoles las dependencias necesarias."""
        db = self.controller.db
        self.ui_home = DashboardPage(db, self.controller.spotify)
        self.ui_chat = ChatPage(db, self.controller.tts) 
        self.ui_cmds = CommandsPage(db)
        self.ui_alerts = AlertsPage(db)
        self.ui_overlay = OverlayPage(self.controller.overlay_server, db)
        self.ui_points = PointsPage(db)
        self.ui_gamble = GamblingPage(db, self.controller)
        self.ui_conf = SettingsPage(db, self.controller)

    def setup_ui(self):
        self.setStyleSheet(get_sheet(True))
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(56)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(2,2,2,2)
        sidebar_layout.setSpacing(4)
        
        # --- Contenido Central (Stack) ---
        self.stack = QStackedWidget()
        self.menu_group = QButtonGroup(self)
        self.menu_btns = []

        # --- CAMBIO 2: Definición del Menú con nombres de archivo explícitos ---
        menu_items = [
            ("home.svg",     "Inicio",          self.ui_home),
            ("chat.svg",  "Monitor de Chat", self.ui_chat),
            ("terminal.svg",  "Comandos",        self.ui_cmds),
            ("bell.svg",     "Alertas Chat",    self.ui_alerts),
            ("layers.svg",   "Overlay",         self.ui_overlay),
            ("users.svg",    "Puntos",          self.ui_points),
            ("casino.svg",   "Casino",          self.ui_gamble),
            ("settings.svg", "Configuración",   self.ui_conf)
        ]

        # Construcción dinámica del menú
        for i, (icon_name, tooltip, widget) in enumerate(menu_items):
            self.stack.addWidget(widget)
            
            # Espaciador antes de configuración (si es el último)
            if i == len(menu_items) - 1: 
                sidebar_layout.addStretch()
            
            btn = self._create_menu_btn(icon_name, tooltip, i)
            self.menu_group.addButton(btn, i)
            self.menu_btns.append(btn)
            sidebar_layout.addWidget(btn)

        # Conexiones internas de navegación
        self.ui_home.navigate_signal.connect(self.switch_page)
        self.ui_home.connect_signal.connect(self.toggle_connection)
        self.ui_conf.user_changed.connect(self.controller.force_user_refresh)
        
        # Sincronización UI Chat -> Controller
        self.ui_chat.voice_btn.toggled.connect(self.controller.set_tts_enabled)
        self.ui_chat.chk_command_only.toggled.connect(self.controller.set_command_only)
        
        # Sincronización Controller -> UI Chat (Estado inicial)
        self.controller.set_tts_enabled(self.ui_chat.voice_btn.isChecked())
        self.controller.set_command_only(self.ui_chat.chk_command_only.isChecked())

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)       
        
        # Página inicial activa
        self.menu_btns[0].setChecked(True)

    def _create_menu_btn(self, icon_filename, tooltip, index):
        # --- CAMBIO 3: Usamos el nombre del archivo directamente ---
        btn = QPushButton()
        btn.setObjectName("MenuBtnMini")
        btn.setIcon(get_icon(icon_filename)) # Ya no usamos ICONS.get()
        btn.setIconSize(QSize(22, 22))
        btn.setCheckable(True)
        btn.setToolTip(tooltip)
        btn.clicked.connect(lambda: self.switch_page(index))
        return btn

    def switch_page(self, index): 
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            # Actualizar estado visual del botón
            if index < len(self.menu_btns): 
                self.menu_btns[index].setChecked(True)
            # Refrescar datos si volvemos al Home
            if self.stack.currentWidget() == self.ui_home: 
                self.ui_home.refresh_data()

    def _connect_signals(self):
        # Logs
        self.controller.log_signal.connect(self.on_log_received)
        # Chat
        self.controller.chat_signal.connect(self.append_chat_message)
        # Estado
        self.controller.status_signal.connect(self.ui_chat.lbl_status.setText)
        self.controller.connection_changed.connect(self.ui_home.update_connection_state)
        # Notificaciones
        self.controller.toast_signal.connect(self.show_toast)
        # Información de Usuario
        self.controller.user_info_signal.connect(self.ui_chat.update_user_info)
        self.controller.user_info_signal.connect(lambda u,f,p: self.ui_home.refresh_data())
        # Casino
        self.controller.gamble_result_signal.connect(self.ui_gamble.add_history_entry)
        # Solicitud de Usuario Manual
        self.controller.username_needed.connect(self.prompt_username)

    def prompt_username(self):
        """Abre el diálogo modal si la detección automática falla."""
        dialog = UsernameInputDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.controller.set_manual_username(dialog.username)
        else:
            self.show_toast("Error", "Se requiere el usuario para conectar.", "Status_Yellow")
            self.ui_home.update_connection_state(False)

    def toggle_connection(self):
        if self.controller.worker is None: 
            self.controller.start_bot()
        else:
            if ModalConfirm(self, "Desconectar", "¿Detener el bot?").exec() == QDialog.DialogCode.Accepted:
                self.controller.stop_bot()
            else: 
                # Si cancela, restauramos el botón visualmente a 'Conectado'
                self.ui_home.update_connection_state(True)

    def on_log_received(self, text):    
        self.ui_home.append_log(text) 
        if "✅" in text or "EN VIVO" in text: 
            self.ui_chat.lbl_status.setText("En Vivo")
        elif "❌" in text: 
            self.ui_chat.lbl_status.setText("Error")

    def append_chat_message(self, timestamp, real_user, display_content):
        c_user = "#00E701" # Kick green default
        current_streamer = self.controller.db.get("kick_username")
        
        # Resaltar al streamer
        if current_streamer and real_user.lower() == current_streamer.lower(): 
            c_user = "#FFD700"
            
        html = f"""
        <div style="line-height: 150%; margin-bottom: 6px;">
            <span style="color:#666; font-size: 11px;">[{timestamp}] </span>
            <span style="color:{c_user}; font-weight: 700; padding-left: 4px;">{real_user}: </span>
            <span style="color:#DDD; padding-left: 4px;">{display_content}</span>
        </div>
        """
        self.ui_chat.txt.append(html)
        sb = self.ui_chat.txt.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_toast(self, title, body, type_msg): 
        ToastNotification(self, title, body, type_msg).show_toast()

    def closeEvent(self, event): 
        if ModalConfirm(self, "Salir", "¿Cerrar?").exec() == QDialog.DialogCode.Accepted:
            self.controller.shutdown()
            event.accept()
        else: 
            event.ignore()