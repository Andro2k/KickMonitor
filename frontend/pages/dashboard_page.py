# frontend/pages/dashboard_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QDialog,
    QTextEdit, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from backend.services.dashboard_service import DashboardService
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.dialogs.connection_modal import ConnectionModal
from frontend.theme import LAYOUT, STYLES, THEME_DARK
from frontend.utils import crop_to_square, get_icon_colored, get_icon, get_rounded_pixmap

# --- IMPORTS NUEVOS ---
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
        self.spotify.status_msg.connect(lambda: self.refresh_data())
        self.spotify.status_msg.connect(self._handle_spotify_status_alert)

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        # 1. Scroll Area Principal
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
        self.main_layout.setContentsMargins(*LAYOUT["margins"])
        self.main_layout.setSpacing(LAYOUT["spacing"])

        self._setup_top_grid_section() 
        self._setup_log_section()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _setup_top_grid_section(self):
        grid_container = QWidget()
        # FlowLayout para respuesta responsiva
        grid_layout = FlowLayout(grid_container, margin=0, spacing=(LAYOUT["spacing"]))

        # A. COLUMNA IZQUIERDA (Perfil + Música)
        left_col = QWidget()
        left_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col.setMinimumWidth(380)
        
        left_l = QVBoxLayout(left_col)
        left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(LAYOUT["spacing"])

        self.profile_card = self._create_profile_card()
        left_l.addWidget(self.profile_card)

        self.music_panel = MusicPlayerPanel(self.service, self.spotify)
        left_l.addWidget(self.music_panel)
        
        grid_layout.addWidget(left_col)

        # B. COLUMNA DERECHA (Accesos Directos)
        self.shortcuts_card = self._create_shortcuts_card()
        self.shortcuts_card.setMinimumWidth(300)
        self.shortcuts_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Expanding vertical
        
        grid_layout.addWidget(self.shortcuts_card)

        self.main_layout.addWidget(grid_container)

    # ==========================================
    # CREADORES DE TARJETAS (Actualizado)
    # ==========================================
    def _create_profile_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card_large"])
        card.setFixedHeight(120) 
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        # Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(100, 100)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 50px;")
        
        # Info
        info = QVBoxLayout()
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        info.setSpacing(4)
        
        self.lbl_welcome = QLabel("Streamer.", objectName="h2")
        self.lbl_welcome.setStyleSheet("border:none;")
        self.lbl_stats = QLabel("Informacion.", objectName="normal")
        self.lbl_stats.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; border:none;")
        
        info.addWidget(self.lbl_welcome)
        info.addWidget(self.lbl_stats)
        
        # Acciones
        actions = QVBoxLayout()
        actions.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        actions.setSpacing(8)
        
        kick_row = QHBoxLayout()
        
        # --- USO DE FACTORY ---
        self.btn_connect = create_dashboard_action_btn("Kick: Offline", "kick.svg", self._handle_kick_connect_click)
        
        self.btn_auto = QPushButton()
        self.btn_auto.setStyleSheet(STYLES["btn_toggle"])
        self.btn_auto.setCheckable(True)
        self.btn_auto.setFixedSize(28, 28)
        self.btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto.setIcon(get_icon("plug.svg"))
        self.btn_auto.setToolTip("Auto-conectar al inicio")
        self.btn_auto.toggled.connect(self._toggle_auto_connect)
        
        is_auto = self.service.get_auto_connect_state()
        self.btn_auto.setChecked(is_auto)
        
        kick_row.addWidget(self.btn_connect)
        kick_row.addWidget(self.btn_auto)
        
        # --- USO DE FACTORY ---
        self.btn_spotify = create_dashboard_action_btn("Spotify", "spotify.svg", self._toggle_spotify_connection)
        self._update_spotify_btn_style(False)

        actions.addLayout(kick_row)
        actions.addWidget(self.btn_spotify)

        layout.addWidget(self.lbl_avatar)
        layout.addLayout(info)
        layout.addStretch()
        layout.addLayout(actions)
        
        return card

    def _create_shortcuts_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card_large"])
        
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])
        
        l.addWidget(create_card_header("Accesos Directos"))
        l.addStretch()
        
        grid = QGridLayout()
        grid.setSpacing(LAYOUT["spacing"])
        
        shortcuts = self.service.get_shortcuts_data()
        cols = 3 
        
        for i, (icon, txt, idx) in enumerate(shortcuts):
            # --- USO DE FACTORY ---
            btn = create_shortcut_btn(txt, icon, lambda _, x=idx: self.navigate_signal.emit(x))
            
            r, c = divmod(i, cols)
            grid.addWidget(btn, r, c)
            
        l.addLayout(grid)
        l.addStretch()
        
        return card

    def _setup_log_section(self):
        # Header Factory
        self.main_layout.addWidget(create_card_header("Registros del Sistema"))
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Esperando conexión.")
        self.log_console.setMinimumHeight(150)
        self.log_console.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)    
        self.log_console.setStyleSheet(STYLES["text_edit_console"]) # Estilo del theme

        self.main_layout.addWidget(self.log_console)

    # ==========================================
    # LOGICA DE ACTUALIZACIÓN
    # ==========================================
    def refresh_data(self):
        data = self.service.get_profile_data()
        self.lbl_welcome.setText(data["greeting"])
        self.lbl_stats.setText(data["stats"])
        if data["pic_url"]: 
            self._start_download(data["pic_url"], "avatar")
        else:
            from frontend.utils import get_icon
            default_pix = get_icon("user.svg").pixmap(100, 100)
            from frontend.utils import get_rounded_pixmap, crop_to_square
            sq_pix = crop_to_square(default_pix, 100)
            self.lbl_avatar.setPixmap(get_rounded_pixmap(sq_pix, is_circle=True))

        self._update_spotify_btn_style(self.spotify.is_active)

    def update_music_ui(self, title, artist, art_url, prog, dur, is_playing):
        if art_url and art_url != self._current_art_url:
            self._current_art_url = art_url
            self._start_download(art_url, "music_art")
        self.music_panel.update_state(title, artist, None, prog, dur, is_playing)

    # ==========================================
    # HANDLERS (Simplificados)
    # ==========================================
    def _handle_kick_connect_click(self):
        # 1. Si ya está conectado (botón presionado), no hacer nada (la desconexión la maneja el controlador global normalmente o un botón stop)
        if self.btn_connect.isChecked():
            pass 

        # 2. Verificar Credenciales (Delegado al servicio + Modal si falla)
        if not self._ensure_credentials("kick"):
            self.btn_connect.setChecked(False)
            return

        # 3. Verificar Usuario
        current_user = self.service.get_kick_username()
        if not current_user:
            from frontend.dialogs.user_modal import UsernameInputDialog
            dlg = UsernameInputDialog(self)
            if dlg.exec():
                self.service.set_kick_username(dlg.username)
                self.connect_signal.emit()
            else:
                self.btn_connect.setChecked(False)
        else:
            self.connect_signal.emit()

    def _toggle_spotify_connection(self):
        if self.spotify.is_active:
            if ModalConfirm(self, "Desconectar", "¿Detener Spotify?").exec():
                self.service.set_spotify_enabled(False)
                self.spotify.sig_do_disconnect.emit()
        else:
            if self._ensure_credentials("spotify"):
                self.service.set_spotify_enabled(True)
                self.spotify.sig_do_auth.emit()

    def _ensure_credentials(self, s_type):
        """Lógica de UI para pedir credenciales si faltan."""
        if self.service.has_credentials(s_type):
            return True
            
        defaults = self.service.get_default_creds(s_type)
        if defaults and ModalConfirm(self, "Configuración", f"¿Usar credenciales default?").exec():
            self.service.apply_creds(defaults)
            return True
            
        worker = self.spotify if s_type == "spotify" else None
        return ConnectionModal(self.service.db, service_type=s_type, worker=worker, parent=self).exec() == QDialog.DialogCode.Accepted

    def _toggle_auto_connect(self, checked):
        self.service.set_auto_connect_state(checked)

    # ==========================================
    # HELPERS VISUALES
    # ==========================================
    def _update_spotify_btn_style(self, active):
        bg = "#1DB954" if active else THEME_DARK['Black_N3']
        fg = "black" if active else THEME_DARK['White_N1']
        txt = "Spotify: On" if active else "Conectar Spotify"
        
        self.btn_spotify.setIcon(get_icon_colored("spotify.svg", fg))
        self.btn_spotify.setText(txt)
        self.btn_spotify.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg}; color: {fg}; border-radius: 8px; 
                font-weight: bold; font-size: 13px; text-align: left; padding-left: 15px; 
            }}
        """)

    def update_connection_state(self, connected):
        self.btn_connect.setChecked(connected)
        bg = THEME_DARK['NeonGreen_Main'] if connected else THEME_DARK['Black_N3']
        fg = "black" if connected else THEME_DARK['White_N1']
        msg = "Bot Conectado" if connected else "Conectar Bot"
        self.btn_connect.setIcon(get_icon_colored("kick.svg", fg))
        self.btn_connect.setText(msg)
        self.btn_connect.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg}; color: {fg}; border-radius: 8px; 
                font-weight: bold; font-size: 13px; text-align: left; padding-left: 15px; 
            }}
        """)

    def _handle_spotify_status_alert(self, msg):
        if any(x in msg for x in ["❌", "Error", "Cancelado"]):
            ToastNotification(self, "Spotify", msg, "status_error").show_toast()
            self._update_spotify_btn_style(False)

    def append_log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # --- NETWORK HELPERS (Se mantienen en UI porque manejan Pixmaps) ---
    def _start_download(self, url, tag):
        req = QNetworkRequest(QUrl(url)); req.setAttribute(QNetworkRequest.Attribute.User, tag)
        self.nam.get(req)

    def _on_download_finished(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            tag = reply.request().attribute(QNetworkRequest.Attribute.User)
            data = reply.readAll()
            pix = QPixmap(); pix.loadFromData(data)
            
            if not pix.isNull():
                if tag == "avatar": 
                    # Cuadrado 100x100 -> Círculo
                    sq_pix = crop_to_square(pix, 100)
                    self.lbl_avatar.setPixmap(get_rounded_pixmap(sq_pix, is_circle=True))
                elif tag == "music_art":
                    # Redondeado radio 10
                    self.music_panel.lbl_art.setPixmap(get_rounded_pixmap(pix, radius=10))
                    
        reply.deleteLater()

    