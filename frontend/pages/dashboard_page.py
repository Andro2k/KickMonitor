# frontend/pages/dashboard_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QDialog,
    QTextEdit, QSizePolicy, QScrollArea, QComboBox # <--- ASEGURATE DE IMPORTAR QComboBox
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

# --- IMPORTS DE COMPONENTES ---
from frontend.components.flow_layout import FlowLayout
from frontend.components.music_card import MusicPlayerPanel
from frontend.factories import create_card_header, create_dashboard_action_btn, create_shortcut_btn 

class DashboardPage(QWidget):
    navigate_signal = pyqtSignal(int) 
    connect_signal = pyqtSignal()

    def __init__(self, db_handler, spotify_worker, ytmusic_worker, parent=None):
        super().__init__(parent)
        self.service = DashboardService(db_handler)
        self.spotify = spotify_worker 
        self.ytmusic = ytmusic_worker 

        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_download_finished)
        self._current_art_url = None
        
        # 1. Crear UI (Aquí se crean cmb_music y btn_music)
        self.init_ui()
        
        # 2. Conectar Señales
        self._connect_signals()

        # 3. Cargar estado inicial (Ahora sí existen los elementos)
        self._refresh_music_ui_state()

    def _connect_signals(self):
        # --- SPOTIFY SIGNALS ---
        self.spotify.track_changed.connect(self._on_spotify_update)
        self.spotify.status_msg.connect(lambda m: self._handle_music_alert("Spotify", m))
        
        # --- YTMUSIC SIGNALS ---
        self.ytmusic.sig_now_playing.connect(self._on_ytmusic_update)
        self.ytmusic.sig_error.connect(lambda m: self._handle_music_alert("YTMusic", m))

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
        self.main_layout.setContentsMargins(*LAYOUT["margins"])
        self.main_layout.setSpacing(LAYOUT["spacing"])

        self._setup_top_grid_section() 
        self._setup_log_section()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _setup_top_grid_section(self):
        grid_container = QWidget()
        grid_layout = FlowLayout(grid_container, margin=0, spacing=LAYOUT["spacing"])

        # COLUMNA IZQUIERDA
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

        # COLUMNA DERECHA
        self.shortcuts_card = self._create_shortcuts_card()
        self.shortcuts_card.setMinimumWidth(300)
        self.shortcuts_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grid_layout.addWidget(self.shortcuts_card)

        self.main_layout.addWidget(grid_container)

    # ==========================================
    # CREADORES DE TARJETAS (CORREGIDO)
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
        
        # --- FILA 1: KICK ---
        kick_row = QHBoxLayout()
        self.btn_connect = create_dashboard_action_btn("Kick: Offline", "kick.svg", self._handle_kick_connect_click)
        
        self.btn_auto = QPushButton()
        self.btn_auto.setStyleSheet(STYLES["btn_toggle"])
        self.btn_auto.setCheckable(True)
        self.btn_auto.setFixedSize(28, 28)
        self.btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto.setIcon(get_icon("plug.svg"))
        self.btn_auto.toggled.connect(self._toggle_auto_connect)
        self.btn_auto.setChecked(self.service.get_auto_connect_state())
        
        kick_row.addWidget(self.btn_connect)
        kick_row.addWidget(self.btn_auto)
        
        # --- FILA 2: MÚSICA (NUEVO) ---
        music_row = QHBoxLayout()
        music_row.setSpacing(5)

        # Selector de Proveedor
        self.cmb_music = QComboBox()
        self.cmb_music.addItems(["Spotify", "YT Music"])
        self.cmb_music.setFixedSize(100, 30)
        self.cmb_music.setStyleSheet(STYLES["combobox"])
        self.cmb_music.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cmb_music.currentIndexChanged.connect(self._on_music_provider_changed)
        
        # Botón Conectar Música
        self.btn_music = QPushButton("Conectar")
        self.btn_music.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_music.setFixedHeight(30)
        self.btn_music.clicked.connect(self._toggle_music_connection)
        
        music_row.addWidget(self.cmb_music)
        music_row.addWidget(self.btn_music)

        actions.addLayout(kick_row)
        actions.addLayout(music_row)

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
            btn = create_shortcut_btn(txt, icon, lambda _, x=idx: self.navigate_signal.emit(x))
            r, c = divmod(i, cols)
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
    # LOGICA DE ACTUALIZACIÓN
    # ==========================================
    def refresh_data(self):
        data = self.service.get_profile_data()
        self.lbl_welcome.setText(data["greeting"])
        self.lbl_stats.setText(data["stats"])
        if data["pic_url"]: self._start_download(data["pic_url"], "avatar")
        self._refresh_music_ui_state()

    # ==========================================
    # LOGICA DE MÚSICA Y UI STATE
    # ==========================================
    def _refresh_music_ui_state(self):
        """Sincroniza el combo y el botón con la DB y el estado real."""
        provider = self.service.db.get("music_provider", "spotify")
        idx = 1 if provider == "ytmusic" else 0
        
        # Bloqueamos señal para evitar bucle infinito al setear index
        self.cmb_music.blockSignals(True)
        self.cmb_music.setCurrentIndex(idx)
        self.cmb_music.blockSignals(False)
        
        active = self.ytmusic._is_active if provider == "ytmusic" else self.spotify.is_active
        self._update_music_btn_style(active, provider)
        
        # Actualizamos el worker del panel
        worker = self.ytmusic if provider == "ytmusic" else self.spotify
        self.music_panel.set_worker(worker)

    def _on_music_provider_changed(self, index):
        provider = "ytmusic" if index == 1 else "spotify"
        self.service.db.set("music_provider", provider)
        self._refresh_music_ui_state()

    def _toggle_music_connection(self):
        provider = self.service.db.get("music_provider", "spotify")
        
        if provider == "spotify":
            if self.spotify.is_active:
                self.spotify.sig_do_disconnect.emit()
            else:
                if self._ensure_credentials("spotify"):
                    self.spotify.sig_do_auth.emit()
        else:
            # Lógica YTMusic
            if self.ytmusic._is_active:
                self.ytmusic.set_active(False)
                self.music_panel.update_state("YTMusic Detenido", "", None, 0, 0, False)
            else:
                self.ytmusic.set_active(True)
                
        # Pequeño delay para dar tiempo a que los workers cambien estado
        import PyQt6.QtCore as Core
        Core.QTimer.singleShot(200, self._refresh_music_ui_state)

    def _update_music_btn_style(self, active, provider):
        color = "#FF0000" if provider == "ytmusic" else "#1DB954"
        icon = "play.svg" if provider == "ytmusic" else "spotify.svg"
        
        bg = color if active else THEME_DARK['Black_N3']
        fg = "white" if active else THEME_DARK['White_N1']
        txt = "On" if active else "Conectar"
        
        self.btn_music.setText(txt)
        self.btn_music.setIcon(get_icon_colored(icon, fg))
        self.btn_music.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg}; color: {fg}; border-radius: 6px; 
                font-weight: bold; padding: 0 10px;
            }}
        """)

    # ==========================================
    # HANDLERS
    # ==========================================
    def _handle_kick_connect_click(self):
        if self.btn_connect.isChecked(): pass 

        if not self._ensure_credentials("kick"):
            self.btn_connect.setChecked(False)
            return

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

    def _ensure_credentials(self, s_type):
        if self.service.has_credentials(s_type): return True
        defaults = self.service.get_default_creds(s_type)
        if defaults and ModalConfirm(self, "Configuración", f"¿Usar credenciales default?").exec():
            self.service.apply_creds(defaults)
            return True
        worker = self.spotify if s_type == "spotify" else None
        return ConnectionModal(self.service.db, service_type=s_type, worker=worker, parent=self).exec() == QDialog.DialogCode.Accepted

    def _toggle_auto_connect(self, checked):
        self.service.set_auto_connect_state(checked)

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

    def _handle_music_alert(self, source, msg):
        if "Error" in msg or "❌" in msg:
            ToastNotification(self, source, msg, "status_error").show_toast()
        self._refresh_music_ui_state()

    def _on_spotify_update(self, title, artist, art_url, prog, dur, is_playing):
        if self.service.db.get("music_provider") == "spotify":
            if art_url and art_url != self._current_art_url:
                self._current_art_url = art_url
                self._start_download(art_url, "music_art")
            self.music_panel.update_state(title, artist, None, prog, dur, is_playing)

    def _on_ytmusic_update(self, text_status):
        if self.service.db.get("music_provider") == "ytmusic":
            parts = text_status.split(" - ", 1)
            title = parts[0]
            artist = parts[1] if len(parts) > 1 else ""
            self.music_panel.update_state(title, artist, None, 0, 0, True)

    def append_log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # --- NETWORK HELPERS ---
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
                    sq_pix = crop_to_square(pix, 100)
                    self.lbl_avatar.setPixmap(get_rounded_pixmap(sq_pix, is_circle=True))
                elif tag == "music_art":
                    # Actualizamos el music_panel directamente
                    self.music_panel.lbl_art.setPixmap(get_rounded_pixmap(pix, radius=10))
                    
        reply.deleteLater()