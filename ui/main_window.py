# ui/main_window.py
import ctypes
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, 
    QStackedWidget, QDialog
)
from PyQt6.QtCore import QTimer

# Backend
from backend.controller import MainController

# UI Components
from ui.components.sidebar import Sidebar
from ui.theme import get_sheet
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.dialogs.username_input import UsernameInputDialog

# Páginas
from ui.pages.alerts_page import AlertsPage
from ui.pages.dashboard_page import DashboardPage 
from ui.pages.chat_page import ChatPage
from ui.pages.settings_page import SettingsPage
from ui.pages.overlay_page import OverlayPage
from ui.pages.points_page import PointsPage
from ui.pages.commands_page import CommandsPage
from ui.pages.casino_page import GamblingPage 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()      
        self.setWindowTitle("Kick Monitor")
        self.resize(1000, 750)
        
        self.controller = MainController()
        
        self._init_pages()
        self.setup_ui()
        self._connect_signals()
        
        # Estado Inicial
        self.controller.force_user_refresh()
        self.ui_home.refresh_data()
        self.ui_home.update_connection_state(False)
        
        if self.controller.db.get_bool("auto_connect"):
            QTimer.singleShot(1000, self.controller.start_bot)

    def _setup_app_id(self):
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('kick.monitor.bot.v2')
        except: pass

    def _init_pages(self):
        db = self.controller.db
        # Instanciamos todas las páginas
        self.ui_home = DashboardPage(db, self.controller.spotify)
        self.ui_chat = ChatPage(db, self.controller.tts) 
        self.ui_cmds = CommandsPage(db)
        self.ui_alerts = AlertsPage(db)
        self.ui_overlay = OverlayPage(self.controller.overlay_server, db)
        self.ui_points = PointsPage(db)
        self.ui_gamble = GamblingPage(db, self.controller)
        self.ui_conf = SettingsPage(db, self.controller)
        
        # Lista ordenada para el Stack
        self.pages_list = [
            self.ui_home, self.ui_chat, self.ui_cmds,
            self.ui_alerts, self.ui_overlay, self.ui_points,
            self.ui_gamble, self.ui_conf
        ]

    def setup_ui(self):
        self.setStyleSheet(get_sheet(True))
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout Principal Horizontal (Sidebar | Contenido)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) 

        # 1. SIDEBAR (Componente Nuevo)
        self.sidebar = Sidebar()
        # self.sidebar.setFixedWidth(240) # Ancho inicial
        self.sidebar.page_selected.connect(self.switch_page)
        
        # 2. CONTENIDO (Stack)
        self.stack = QStackedWidget()
        for page in self.pages_list:
            self.stack.addWidget(page)

        # Agregar al layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)       
        
        # Seleccionar Home por defecto en UI
        self.sidebar.set_current_index(0)

    def switch_page(self, index): 
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            # Sincronizar el botón visual del sidebar (por si se llamó desde otro lado)
            self.sidebar.set_current_index(index)
            
            # Refrescar Home si volvemos a ella
            if self.stack.currentWidget() == self.ui_home: 
                self.ui_home.refresh_data()

    def _connect_signals(self):
        # Navegación interna (ej: Cards del Dashboard -> Sidebar)
        self.ui_home.navigate_signal.connect(self.switch_page)
        
        # Resto de conexiones existentes...
        self.ui_home.connect_signal.connect(self.toggle_connection)
        self.ui_conf.user_changed.connect(self.controller.force_user_refresh)
        
        self.ui_chat.voice_btn.toggled.connect(self.controller.set_tts_enabled)
        self.ui_chat.chk_command_only.toggled.connect(self.controller.set_command_only)
        self.controller.set_tts_enabled(self.ui_chat.voice_btn.isChecked())
        self.controller.set_command_only(self.ui_chat.chk_command_only.isChecked())

        self.controller.log_signal.connect(self.on_log_received)
        self.controller.chat_signal.connect(self.append_chat_message)
        self.controller.status_signal.connect(self.ui_chat.lbl_status.setText)
        self.controller.connection_changed.connect(self.ui_home.update_connection_state)
        self.controller.toast_signal.connect(self.show_toast)
        self.controller.user_info_signal.connect(self.ui_chat.update_user_info)
        self.controller.user_info_signal.connect(lambda u,f,p: self.ui_home.refresh_data())
        self.controller.user_info_signal.connect(lambda u, f, p: self.sidebar.update_user_info(u, p))
        self.controller.gamble_result_signal.connect(self.ui_gamble.add_history_entry)
        self.controller.username_needed.connect(self.prompt_username)

    # --- MÉTODOS AUXILIARES (Sin cambios mayores) ---
    def prompt_username(self):
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