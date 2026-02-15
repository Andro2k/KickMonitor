# frontend/main_window.py

import ctypes
from datetime import datetime
from contextlib import suppress
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

# Backend
from backend.core.controller import MainController
from backend.workers.update_worker import INTERNAL_VERSION

# UI Components
from frontend.components.sidebar import Sidebar
from frontend.theme import get_sheet
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.components.tray_icon import TrayIcon  
from frontend.utils import resource_path 

# Páginas
from frontend.pages.alerts_page import AlertsPage
from frontend.pages.dashboard_page import DashboardPage 
from frontend.pages.chat_page import ChatPage
from frontend.pages.settings_page import SettingsPage
from frontend.pages.trigger_page import TriggerPage
from frontend.pages.points_page import PointsPage
from frontend.pages.commands_page import CommandsPage
from frontend.pages.casino_page import GamblingPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() 
        self._setup_app_id()     
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setWindowTitle(f"Kick Monitor v{INTERNAL_VERSION}")
        self.resize(1000, 650)
        
        self.controller = MainController()
        
        self._init_pages()
        self.setup_ui()
        self._connect_signals()

        # Inicializamos el componente de la bandeja del sistema
        self.tray_icon = TrayIcon(self)

        # Estado Inicial
        self.controller.force_user_refresh()
        self.ui_home.refresh_data()
        self.ui_home.update_connection_state(False)
        
        if self.controller.db.get_bool("auto_connect"):
            QTimer.singleShot(1000, self.controller.start_bot)

    def _setup_app_id(self):
        with suppress(Exception):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'kickmonitor.v2.0.0')

    def _init_pages(self):
        db = self.controller.db
        self.ui_home = DashboardPage(db, self.controller.spotify)
        self.ui_chat = ChatPage(db, self.controller.tts, self.controller.chat_overlay)
        self.ui_cmds = CommandsPage(db)
        self.ui_alerts = AlertsPage(db)
        self.ui_overlay = TriggerPage(self.controller.overlay_server, db)
        self.ui_points = PointsPage(db)
        self.ui_gamble = GamblingPage(db, self.controller)
        self.ui_conf = SettingsPage(db, self.controller)
        
        self.pages_list = [
            self.ui_home, self.ui_chat, self.ui_cmds,
            self.ui_alerts, self.ui_overlay, self.ui_points,
            self.ui_gamble, self.ui_conf
        ]

    def setup_ui(self):
        self.setStyleSheet(get_sheet())
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 

        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(self.switch_page)
        
        self.stack = QStackedWidget()
        for page in self.pages_list:
            self.stack.addWidget(page)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)       
        self.sidebar.set_current_index(0)

    def switch_page(self, index): 
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            self.sidebar.set_current_index(index)
            if self.stack.currentWidget() == self.ui_home: 
                self.ui_home.refresh_data()

    def _connect_signals(self):
        # Navegación y UI
        self.ui_home.navigate_signal.connect(self.switch_page)
        self.ui_home.connect_signal.connect(self.toggle_connection)
        self.ui_conf.user_changed.connect(self.controller.force_user_refresh)
        
        # Opciones de Chat
        self.ui_chat.voice_btn.toggled.connect(self.controller.set_tts_enabled)
        self.ui_chat.chk_command_only.toggled.connect(self.controller.set_command_only)

        # Estados Iniciales Controller
        self.controller.set_tts_enabled(self.ui_chat.voice_btn.isChecked())
        self.controller.set_command_only(self.ui_chat.chk_command_only.isChecked())
        
        # Conexiones Core Controller -> Interfaz
        self.controller.log_signal.connect(self.on_log_received)
        self.controller.chat_signal.connect(self.append_chat_message)
        self.controller.status_signal.connect(self.ui_chat.lbl_status.setText)
        self.controller.connection_changed.connect(self.ui_home.update_connection_state)
        self.controller.toast_signal.connect(self.show_toast)
        self.controller.user_info_signal.connect(self.ui_chat.update_user_info)
        self.controller.user_info_signal.connect(lambda u,f,p: self.ui_home.refresh_data())
        self.controller.user_info_signal.connect(lambda u, f, p: self.sidebar.update_user_info(u, p))
        self.controller.gamble_result_signal.connect(self.ui_gamble.add_history_entry)

    def toggle_connection(self):
        if self.controller.worker is None: 
            self.controller.start_bot()
        else:
            if ModalConfirm(self, "Desconectar", "¿Detener el bot?").exec():
                self.controller.stop_bot()
            else: 
                self.ui_home.update_connection_state(True)

    def on_log_received(self, text):    
        self.ui_home.append_log(text) 
        if any(keyword in text for keyword in ["✅", "EN VIVO"]): 
            self.ui_chat.lbl_status.setText("En Vivo")
        elif "❌" in text: 
            self.ui_chat.lbl_status.setText("Error")

    def append_chat_message(self, timestamp, real_user, display_content):       
        fmt_pref = self.controller.db.get("time_fmt", "Sistema")
        now = datetime.now()
        
        final_time = timestamp
        if "12-hour" in fmt_pref: final_time = now.strftime("%I:%M %p")
        elif "24-hour" in fmt_pref: final_time = now.strftime("%H:%M")

        current_streamer = self.controller.db.get("kick_username", "")
        is_streamer = current_streamer and real_user.lower() == current_streamer.lower()
        c_user = "#FFD700" if is_streamer else "#00E701"
            
        html = f"""
        <div style="line-height: 150%; margin-bottom: 6px;">
            <span style="color:#666; font-size: 11px;">[{final_time}] </span>
            <span style="color:{c_user}; font-weight: 700; padding-left: 4px;">{real_user}: </span>
            <span style="color:#DDD; padding-left: 4px;">{display_content}</span>
        </div>
        """
        self.ui_chat.txt.append(html)
        sb = self.ui_chat.txt.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_toast(self, title, body, type_msg): 
        ToastNotification(self, title, body, type_msg).show_toast()

    # =========================================================================
    # EVENTO DE CIERRE OPTIMIZADO
    # =========================================================================
    def closeEvent(self, event):
        """Maneja el cierre de la ventana principal."""
        # 1. Si está configurado para minimizar a la bandeja:
        if self.controller.db.get_bool("minimize_to_tray"):
            event.ignore() # Ignora el cierre real
            self.hide()    # Solo esconde la ventana
            
            # Usamos el nuevo método del componente separado
            self.tray_icon.show_minimized_notification()
            return # Salida temprana (Guard Clause)

        # 2. Si no, pregunta si quiere cerrar de verdad:
        if ModalConfirm(self, "Salir", "¿Cerrar la aplicación?").exec():
            self.controller.shutdown()
            event.accept()
        else:
            event.ignore()