# frontend/pages/dashboard_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QTextEdit, 
    QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Servicios y Alertas
from backend.services.dashboard_service import DashboardService
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification

# Estilos y Utilidades
from frontend.theme import LAYOUT, STYLES, THEME_DARK
from frontend.utils import crop_to_square, get_icon_colored, get_icon, get_rounded_pixmap

# Componentes
from frontend.components.flow_layout import FlowLayout
from frontend.components.music_card import MusicPlayerPanel
from frontend.factories import create_card_header, create_dashboard_action_btn, create_shortcut_btn 

class DashboardPage(QWidget):
    navigate_signal = pyqtSignal(int) 
    connect_signal = pyqtSignal()

    def __init__(self, db_handler, spotify_worker, parent=None):
        super().__init__(parent)
        self.service = DashboardService(db_handler)
        self.spotify = spotify_worker 

        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_download_finished)
        self._current_art_url = None
        
        self.init_ui()
        self._connect_signals()

    def _connect_signals(self):
        self.spotify.track_changed.connect(self.update_music_ui)
        self.spotify.status_msg.connect(self.refresh_data)
        self.spotify.status_msg.connect(self._handle_spotify_status_alert)

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(*LAYOUT["level_03"])
        self.main_layout.setSpacing(LAYOUT["space_01"])

        self._setup_top_grid_section() 
        self._setup_log_section()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _setup_top_grid_section(self):
        grid_container = QWidget()
        grid_layout = FlowLayout(grid_container, margin=0, spacing=(LAYOUT["space_01"]))

        left_col = QWidget()
        left_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col.setMinimumWidth(380)
        
        left_l = QVBoxLayout(left_col)
        left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(LAYOUT["space_01"])

        self.profile_card = self._create_profile_card()
        self.music_panel = MusicPlayerPanel(self.service, self.spotify)
        
        left_l.addWidget(self.profile_card)
        left_l.addWidget(self.music_panel)
        grid_layout.addWidget(left_col)

        # B. COLUMNA DERECHA (Accesos Directos)
        self.shortcuts_card = self._create_shortcuts_card()
        self.shortcuts_card.setMinimumWidth(300)
        self.shortcuts_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grid_layout.addWidget(self.shortcuts_card)

        self.main_layout.addWidget(grid_container)

    # ==========================================
    # CREADORES DE TARJETAS
    # ==========================================
    def _create_profile_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card_large"])
        
        avatar_size = 112
        card.setFixedHeight(avatar_size + 40) 
    
        layout = QHBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) 
        layout.setContentsMargins(*LAYOUT["level_02"])
        layout.setSpacing(LAYOUT["space_01"])

        # Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(avatar_size, avatar_size)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: {avatar_size // 2}px;")
        
        # Info (Nombre y Stats)
        info = QVBoxLayout()
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        info.setSpacing(4)
        
        self.lbl_welcome = QLabel("Streamer.", objectName="h2")
        self.lbl_welcome.setStyleSheet("border:none;")
        self.lbl_stats = QLabel("Información.", objectName="normal")
        self.lbl_stats.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; border:none;")
        
        info.addWidget(self.lbl_welcome)
        info.addWidget(self.lbl_stats)
        
        # Acciones (Botones)
        actions = QVBoxLayout()
        actions.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        actions.setSpacing(8)
        
        kick_row = QHBoxLayout()
        self.btn_connect = create_dashboard_action_btn("Kick: Offline", "kick.svg", self._handle_kick_connect_click)
        
        self.btn_auto = QPushButton()
        self.btn_auto.setStyleSheet(STYLES["btn_toggle"])
        self.btn_auto.setCheckable(True)
        self.btn_auto.setFixedSize(28, 28)
        self.btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto.setIcon(get_icon("plug.svg"))
        self.btn_auto.setToolTip("Auto-conectar al inicio")
        self.btn_auto.setChecked(self.service.get_auto_connect_state())
        self.btn_auto.toggled.connect(self._toggle_auto_connect)
        
        kick_row.addWidget(self.btn_connect)
        kick_row.addWidget(self.btn_auto)
        
        self.btn_spotify = create_dashboard_action_btn("Spotify", "spotify.svg", self._toggle_spotify_connection)
        self._update_spotify_btn_style(False)

        actions.addLayout(kick_row)
        actions.addWidget(self.btn_spotify)

        # Empaquetado final
        layout.addWidget(self.lbl_avatar)
        layout.addLayout(info)
        layout.addStretch()
        layout.addLayout(actions)
        return card

    def _create_shortcuts_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card_large"])
        
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["level_02"])
        l.setSpacing(LAYOUT["space_01"])
        l.addWidget(create_card_header("Accesos Directos"))
        l.addStretch()
        
        grid = QGridLayout()
        grid.setSpacing(LAYOUT["space_01"])
        
        for i, (icon, txt, idx) in enumerate(self.service.get_shortcuts_data()):
            btn = create_shortcut_btn(txt, icon, lambda _, x=idx: self.navigate_signal.emit(x))
            r, c = divmod(i, 3)
            grid.addWidget(btn, r, c)
            
        l.addLayout(grid)
        l.addStretch()
        return card

    def _setup_log_section(self):
        self.main_layout.addWidget(create_card_header("Registros del Sistema"))
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Esperando conexión.")
        self.log_console.setMinimumHeight(150)
        self.log_console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)    
        self.log_console.setStyleSheet(STYLES["text_edit_console"])
        self.main_layout.addWidget(self.log_console)

    # ==========================================
    # LÓGICA DE ACTUALIZACIÓN
    # ==========================================
    def refresh_data(self):
        data = self.service.get_profile_data()
        self.lbl_welcome.setText(data["greeting"])
        self.lbl_stats.setText(data["stats"])
        
        if data["pic_url"]: 
            self._start_download(data["pic_url"], "avatar")
        else:
            size = self.lbl_avatar.width()
            default_pix = get_icon("user.svg").pixmap(size, size)
            self.lbl_avatar.setPixmap(get_rounded_pixmap(crop_to_square(default_pix, size), is_circle=True))

        self._update_spotify_btn_style(self.spotify.is_active)

    def update_music_ui(self, title, artist, art_url, prog, dur, is_playing):
        if art_url and art_url != self._current_art_url:
            self._current_art_url = art_url
            self._start_download(art_url, "music_art")
        self.music_panel.update_state(title, artist, None, prog, dur, is_playing)

    # ==========================================
    # HANDLERS Y CREDENCIALES
    # ==========================================
    def _handle_kick_connect_click(self):
        if not self._ensure_credentials("kick"):
            self.btn_connect.setChecked(False)
            return
        self.connect_signal.emit()

    def _toggle_spotify_connection(self):
        if self.spotify.is_active:
            if ModalConfirm(self, "Desconectar", "¿Detener Spotify?").exec():
                self.service.set_spotify_enabled(False)
                ToastNotification(self, "Spotify", "Desconectado", "info").show_toast()
                self.spotify.sig_do_disconnect.emit()
        else:
            if self._ensure_credentials("spotify"):
                self.service.set_spotify_enabled(True)
                ToastNotification(self, "Spotify", "Conectado", "info").show_toast()
                self.spotify.sig_do_auth.emit()

    def _ensure_credentials(self, s_type):
        """Valida que existan credenciales. Si no hay, usa defaults o lanza error visual."""
        if self.service.has_credentials(s_type):
            return True
            
        defaults = self.service.get_default_creds(s_type)
        if defaults:
            self.service.apply_creds(defaults)
            return True

        ToastNotification(self, "Error de Credenciales", f"Faltan datos de conexión para {s_type.capitalize()}.", "status_error").show_toast()
        return False

    def _toggle_auto_connect(self, checked):
        self.service.set_auto_connect_state(checked)

    # ==========================================
    # HELPERS VISUALES
    # ==========================================
    def _style_action_btn(self, btn, is_active, bg_active, fg_active, text_active, text_inactive, icon_name):
        bg = bg_active if is_active else THEME_DARK['Black_N3']
        fg = fg_active if is_active else THEME_DARK['White_N1']
        
        btn.setIcon(get_icon_colored(icon_name, fg))
        btn.setText(text_active if is_active else text_inactive)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg}; color: {fg}; border-radius: 8px; 
                font-weight: bold; font-size: 13px; text-align: left; padding-left: 15px; 
            }}
        """)

    def _update_spotify_btn_style(self, active):
        self._style_action_btn(
            self.btn_spotify, active, 
            bg_active="#1DB954", fg_active="black", 
            text_active="Spotify: On", text_inactive="Conectar Spotify", icon_name="spotify.svg"
        )

    def update_connection_state(self, connected):
        self.btn_connect.setChecked(connected)
        self._style_action_btn(
            self.btn_connect, connected, 
            bg_active=THEME_DARK['NeonGreen_Main'], fg_active="black", 
            text_active="Bot Conectado", text_inactive="Conectar Bot", icon_name="kick.svg"
        )

    def _handle_spotify_status_alert(self, msg):
        if any(x in msg for x in ["❌", "Error", "Cancelado"]):
            ToastNotification(self, "Spotify", msg, "status_error").show_toast()
            self._update_spotify_btn_style(False)

    def append_log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # ==========================================
    # DESCARGAS ASÍNCRONAS DE RED
    # ==========================================
    def _start_download(self, url, tag):
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.User, tag)
        self.nam.get(req)

    def _on_download_finished(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            reply.deleteLater()
            return
            
        tag = reply.request().attribute(QNetworkRequest.Attribute.User)
        pix = QPixmap()
        pix.loadFromData(reply.readAll())
        reply.deleteLater()
        
        if pix.isNull(): return
            
        if tag == "avatar": 
            size = self.lbl_avatar.width() 
            self.lbl_avatar.setPixmap(get_rounded_pixmap(crop_to_square(pix, size), is_circle=True))
        elif tag == "music_art":
            self.music_panel.lbl_art.setPixmap(get_rounded_pixmap(pix, radius=10))