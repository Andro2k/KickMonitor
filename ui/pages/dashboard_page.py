# ui/pages/dashboard_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout, QDialog,
    QLineEdit, QProgressBar, QTextEdit, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from services.dashboard_service import DashboardService
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.dialogs.connection_modal import ConnectionModal
from ui.theme import LAYOUT, THEME_DARK, get_switch_style
from ui.utils import get_colored_icon, get_icon

# =========================================================================
# COMPONENTE 1: PANEL DE MÚSICA (ESTÁTICO Y LIMPIO)
# =========================================================================
class MusicPlayerPanel(QFrame):
    """
    Panel que agrupa: Carátula, Info, Barra de Progreso, Controles y Comandos.
    Mantiene la lógica visual de música separada del Dashboard principal.
    """
    def __init__(self, parent_page):
        super().__init__()
        self.page = parent_page
        self.service = parent_page.service
        self.spotify = parent_page.spotify
        
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border-radius: 16px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- ZONA SUPERIOR: REPRODUCTOR ---
        player_row = QHBoxLayout()
        player_row.setSpacing(15)

        # 1. Carátula
        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(110, 110)
        self.lbl_art.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 10px;")
        self.lbl_art.setScaledContents(True)
        player_row.addWidget(self.lbl_art)

        # 2. Info + Progreso + Controles
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        
        # Titulo y Artista
        self.lbl_song = QLabel("No Song Playing", styleSheet=f"color: {THEME_DARK['White_N1']}; font-weight: bold; font-size: 15px;")
        self.lbl_artist = QLabel("Artist Name", styleSheet=f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 12px;")
        
        # Tiempos
        time_layout = QHBoxLayout()
        self.lbl_curr = QLabel("0:00", styleSheet="color: #888; font-size: 10px;")
        self.lbl_total = QLabel("0:00", styleSheet="color: #888; font-size: 10px;")
        time_layout.addWidget(self.lbl_curr)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_total)

        # Barra
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {THEME_DARK['Black_N4']}; border-radius: 3px; }} 
            QProgressBar::chunk {{ background: {THEME_DARK['NeonGreen_Main']}; border-radius: 3px; }}
        """)

        # Botones
        ctrls = QHBoxLayout()
        ctrls.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.btn_play = self._create_icon_btn("play-circle.svg", self.spotify.play_pause, 26)
        ctrls.addWidget(self._create_icon_btn("prev.svg", self.spotify.prev_track, 20))
        ctrls.addSpacing(10)
        ctrls.addWidget(self.btn_play)
        ctrls.addSpacing(10)
        ctrls.addWidget(self._create_icon_btn("next.svg", self.spotify.next_track, 20))

        info_col.addWidget(self.lbl_song)
        info_col.addWidget(self.lbl_artist)
        info_col.addLayout(time_layout)
        info_col.addWidget(self.progress)
        info_col.addLayout(ctrls)
        
        player_row.addLayout(info_col)
        main_layout.addLayout(player_row)

        # --- SEPARADOR ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {THEME_DARK['border']}; margin: 5px 0;")
        main_layout.addWidget(sep)

        # --- ZONA INFERIOR: COMANDOS ---
        main_layout.addWidget(QLabel("COMANDOS RÁPIDOS", styleSheet="color:#666; font-size:10px; font-weight:bold;"))
        
        grid = QGridLayout()
        grid.setSpacing(10)
        cmds = self.service.get_music_commands_list()
        
        for i, (key, default, desc) in enumerate(cmds):
            r, c = divmod(i, 2)
            self._add_cmd_input(grid, r, c, key, default, desc)
            
        main_layout.addLayout(grid)
        main_layout.addStretch()

    def _create_icon_btn(self, icon, func, size):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setIconSize(QSize(size, size))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("background: transparent; border: none;")
        btn.clicked.connect(func)
        return btn

    def _add_cmd_input(self, grid, r, c, key, default, desc):
        val = self.service.get_command_value(key, default)
        is_active = self.service.get_command_active(key)
        
        container = QWidget()
        container.setStyleSheet("border:none; background:transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0); layout.setSpacing(6)

        chk = QCheckBox()
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(get_switch_style())
        chk.setChecked(is_active)
        chk.clicked.connect(lambda chk: self.service.save_command_active(key, chk))

        txt = QLineEdit(val)
        txt.setPlaceholderText(default)
        txt.setStyleSheet(f"""
            QLineEdit {{
                background: {THEME_DARK['Black_N4']}; color: {THEME_DARK['NeonGreen_Main']};
                border: none; border-radius: 4px; padding: 4px; font-family: Consolas; font-weight: bold; font-size: 11px;
            }}
            QLineEdit:focus {{ background: {THEME_DARK['Black_N2']}; }}
        """)
        
        def save():
            t = txt.text().strip()
            if t and not t.startswith("!"): t = "!" + t; txt.setText(t)
            self.service.save_command(key, t)
            
        txt.editingFinished.connect(save)
        
        lbl = QLabel(desc, styleSheet="color:#888; font-size:10px;")
        
        layout.addWidget(chk); layout.addWidget(txt, 1); layout.addWidget(lbl)
        grid.addWidget(container, r, c)

    def update_state(self, title, artist, art_pixmap, prog, dur, is_playing):
        self.lbl_song.setText(title[:30] + "..." if len(title) > 30 else title)
        self.lbl_artist.setText(artist)
        
        self.btn_play.setIcon(get_icon("pause.svg" if is_playing else "play-circle.svg"))
        
        if art_pixmap:
            self.lbl_art.setPixmap(art_pixmap)
            
        if dur > 0:
            self.progress.setRange(0, dur)
            self.progress.setValue(prog)
            self.lbl_curr.setText(self.page._format_time(prog))
            self.lbl_total.setText(self.page._format_time(dur))


# =========================================================================
# PAGE PRINCIPAL
# =========================================================================
class DashboardPage(QWidget):
    navigate_signal = pyqtSignal(int) 
    connect_signal = pyqtSignal()

    def __init__(self, db_handler, spotify_worker, parent=None):
        super().__init__(parent)
        self.service = DashboardService(db_handler)
        self.spotify = spotify_worker 
        
        # Gestor de descargas (Imágenes)
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_download_finished)
        self._current_art_url = None
        
        self.init_ui()
        self._connect_signals()

    def _connect_signals(self):
        self.spotify.track_changed.connect(self.update_music_ui)
        self.spotify.status_msg.connect(lambda: self.refresh_data())
        self.spotify.status_msg.connect(self._handle_spotify_status_alert)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(*LAYOUT["margins"])
        self.main_layout.setSpacing(LAYOUT["spacing"])

        self._setup_profile_section()
        self._setup_center_section()
        self._setup_log_section()

    # ==========================================
    # SECCIÓN 1: PERFIL
    # ==========================================
    def _setup_profile_section(self):
        self.profile_card = QFrame()
        self.profile_card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 15px;")
        
        layout = QHBoxLayout(self.profile_card)
        layout.setContentsMargins(*LAYOUT["margins"]); layout.setSpacing(20)

        # Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(120, 120)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 60px;")
        
        # Textos
        info = QVBoxLayout(); info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_welcome = QLabel("Cargando..."); self.lbl_welcome.setObjectName("h1"); self.lbl_welcome.setStyleSheet("border:none;")
        self.lbl_stats = QLabel("..."); self.lbl_stats.setObjectName("normal"); self.lbl_stats.setStyleSheet("border:none;")
        info.addWidget(self.lbl_welcome); info.addWidget(self.lbl_stats)
        
        # Botones
        actions = QVBoxLayout(); actions.setAlignment(Qt.AlignmentFlag.AlignVCenter); actions.setSpacing(10)
        
        # Fila Kick
        kick_row = QHBoxLayout(); kick_row.setSpacing(10)
        self.btn_connect = self._create_main_action_btn("Kick: Desconectado", "kick.svg")
        self.btn_connect.clicked.connect(self._handle_kick_connect_click)
        
        self.btn_auto = QPushButton()
        self.btn_auto.setCheckable(True); self.btn_auto.setFixedSize(40, 40)
        self.btn_auto.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_auto.setIcon(get_icon("plug.svg"))
        self.btn_auto.toggled.connect(self._toggle_auto_connect)
        is_auto = self.service.get_auto_connect_state()
        self.btn_auto.setChecked(is_auto); self._update_auto_btn_style(is_auto)
        
        kick_row.addWidget(self.btn_connect); kick_row.addWidget(self.btn_auto)
        
        # Botón Spotify
        self.btn_spotify = self._create_main_action_btn("Conectar Spotify", "spotify.svg")
        self.btn_spotify.clicked.connect(self._toggle_spotify_connection)
        self._update_spotify_btn_style(False)

        actions.addLayout(kick_row); actions.addWidget(self.btn_spotify)

        layout.addWidget(self.lbl_avatar); layout.addLayout(info); layout.addStretch(); layout.addLayout(actions)
        self.main_layout.addWidget(self.profile_card)

    # ==========================================
    # SECCIÓN 2: CENTRO (MÚSICA + SHORTCUTS)
    # ==========================================
    def _setup_center_section(self):
        center = QHBoxLayout(); center.setSpacing(LAYOUT["spacing"])

        # IZQUIERDA: PANEL DE MÚSICA (NUESTRA CLASE OPTIMIZADA)
        left = QVBoxLayout()
        left.addWidget(QLabel("Control de Música", objectName="h3"))
        self.music_panel = MusicPlayerPanel(self)
        left.addWidget(self.music_panel)
        left.addStretch() # Empujar hacia arriba

        # DERECHA: ACCESOS DIRECTOS
        right = QVBoxLayout()
        right.addWidget(QLabel("Accesos Directos", objectName="h3"))
        
        shortcuts_card = QFrame()
        shortcuts_card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        s_layout = QVBoxLayout(shortcuts_card); s_layout.setContentsMargins(*LAYOUT["margins"])
        
        self._setup_shortcuts_grid(s_layout)
        s_layout.addStretch()
        
        right.addWidget(shortcuts_card)

        center.addLayout(left, 45)
        center.addLayout(right, 55)
        self.main_layout.addLayout(center)

    def _setup_shortcuts_grid(self, layout):
        grid = QGridLayout(); grid.setSpacing(10)
        shortcuts = [
            ("chat.svg", "Chat", 1, "#20C554"), ("terminal.svg", "Comandos", 2, "#2196F3"),
            ("bell.svg", "Alertas", 3, "#AAFF00"), ("layers.svg", "Triggers", 4, "#FF9800"), 
            ("users.svg", "Usuarios", 5, "#E91E63"), ("casino.svg", "Casino", 6, "#D81EE9"), 
            ("settings.svg", "Ajustes", 7, "#9E9E9E")
        ]
        for i, (icon, txt, idx, color) in enumerate(shortcuts):
            btn = self._create_shortcut_btn(icon, txt, color)
            btn.clicked.connect(lambda _, x=idx: self.navigate_signal.emit(x))
            r, c = divmod(i, 3)
            grid.addWidget(btn, r, c)
        layout.addLayout(grid)

    def _setup_log_section(self):
        self.main_layout.addWidget(QLabel("Registros del Sistema", objectName="h3"))
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Esperando conexión...")
        self.log_console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {THEME_DARK['Black_N3']}; color: #aaa;
                font-family: Consolas, monospace; font-size: 12px; white-space: pre;
            }}
        """)

        self.main_layout.addWidget(self.log_console, 1)

    # ==========================================
    # LOGICA DE ACTUALIZACIÓN
    # ==========================================
    def refresh_data(self):
        data = self.service.get_profile_data()
        self.lbl_welcome.setText(data["greeting"])
        self.lbl_stats.setText(data["stats"])
        if data["pic_url"]: self._start_download(data["pic_url"], "avatar")
        self._update_spotify_btn_style(self.spotify.is_active)

    def update_music_ui(self, title, artist, art_url, prog, dur, is_playing):
        # Delegamos en el panel
        pix = None
        if art_url and art_url != self._current_art_url:
            self._current_art_url = art_url
            self._start_download(art_url, "music_art")
        
        # El panel se actualiza inmediatamente (texto), la imagen cuando descargue
        self.music_panel.update_state(title, artist, None, prog, dur, is_playing)

    def _on_download_finished(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            tag = reply.request().attribute(QNetworkRequest.Attribute.User)
            data = reply.readAll()
            pix = QPixmap(); pix.loadFromData(data)
            
            if not pix.isNull():
                if tag == "avatar": 
                    self._set_rounded_avatar(pix) 
                elif tag == "music_art":
                    r_pix = self._round_image(pix, radius=10)
                    self.music_panel.lbl_art.setPixmap(r_pix)
        reply.deleteLater()

    # ==========================================
    # HELPERS Y ESTILOS
    # ==========================================
    def _create_main_action_btn(self, text, icon):
        btn = QPushButton(text); btn.setIcon(get_icon(icon))
        btn.setCheckable(True); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40); btn.setMinimumWidth(180)
        return btn

    def _create_shortcut_btn(self, icon, text, hover_c):
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(65)
        
        l = QVBoxLayout(btn)
        l.addWidget(QLabel(pixmap=get_icon(icon).pixmap(24,24), alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="border:none; background:transparent;"))
        l.addWidget(QLabel(text, alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="border:none; font-weight:bold; font-size:11px; background:transparent;"))
        
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {THEME_DARK['Black_N4']}; border-radius: 12px; }} 
            QPushButton:hover {{ background-color: {THEME_DARK['Black_N3']}; border: 1px solid {hover_c}; }}
        """)
        return btn

    def _update_auto_btn_style(self, checked):
        bg = "rgba(83, 252, 24, 0.15)" if checked else THEME_DARK['Black_N4']
        bc = THEME_DARK['NeonGreen_Main'] if checked else THEME_DARK['border']
        self.btn_auto.setStyleSheet(f"QPushButton {{ background-color: {bg}; border: 1px solid {bc}; border-radius: 8px; }}")

    def _update_spotify_btn_style(self, active):
        bg = "#1DB954" if active else THEME_DARK['Black_N4']
        fg = "black" if active else THEME_DARK['White_N1']
        border = "#1DB954" if active else THEME_DARK['border']
        txt = "Spotify: Conectado" if active else "Conectar Spotify"
        self.btn_spotify.setIcon(get_colored_icon("spotify.svg", fg))
        self.btn_spotify.setText(txt)
        self.btn_spotify.setStyleSheet(f"QPushButton {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 8px; font-weight: bold; font-size: 14px; text-align: left; padding-left: 20px; }}")

    def update_connection_state(self, connected):
        self.btn_connect.setChecked(connected)
        bg = THEME_DARK['NeonGreen_Main'] if connected else THEME_DARK['Black_N4']
        fg = "black" if connected else THEME_DARK['White_N1']
        msg = "Bot Conectado" if connected else "Conectar Bot"
        self.btn_connect.setIcon(get_colored_icon("kick.svg", fg))
        self.btn_connect.setText(msg)
        self.btn_connect.setStyleSheet(f"QPushButton {{ background-color: {bg}; color: {fg}; border-radius: 8px; font-weight: bold; font-size: 14px; text-align: left; padding-left: 20px; }}")

    def append_log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # ==========================================
    # LÓGICA DE BOTONES (HANDLERS)
    # ==========================================
    def _handle_kick_connect_click(self):
        if self.btn_connect.isChecked():
            if self._check_creds("kick"): self.connect_signal.emit()
            else: self.btn_connect.setChecked(False)
        else: self.connect_signal.emit()

    def _toggle_spotify_connection(self):
        if self.spotify.is_active:
            if ModalConfirm(self, "Desconectar", "¿Detener Spotify?").exec() == QDialog.DialogCode.Accepted:
                self.service.db.set("spotify_enabled", "0"); self.spotify.sig_do_disconnect.emit()
        else:
            if self._check_creds("spotify"):
                self.service.db.set("spotify_enabled", "1"); self.spotify.sig_do_auth.emit()

    def _toggle_auto_connect(self, checked):
        self.service.set_auto_connect_state(checked); self._update_auto_btn_style(checked)

    def _check_creds(self, s_type):
        key = "client_id" if s_type == "kick" else "spotify_client_id"
        if self.service.db.get(key): return True
        
        defaults = self.service.get_default_creds(s_type)
        if defaults and ModalConfirm(self, "Configuración", f"¿Usar credenciales default?").exec():
            self.service.apply_creds(defaults); return True
            
        worker = self.spotify if s_type == "spotify" else None
        return ConnectionModal(self.service.db, service_type=s_type, worker=worker, parent=self).exec() == QDialog.DialogCode.Accepted

    def _handle_spotify_status_alert(self, msg):
        if any(x in msg for x in ["❌", "Error", "Cancelado"]):
            ToastNotification(self, "Spotify", msg, "Status_Red").show_toast()
            self._update_spotify_btn_style(False)

    # ==========================================
    # UTILIDADES IMAGEN
    # ==========================================
    def _format_time(self, ms):
        s = (ms // 1000) % 60; m = (ms // (1000 * 60)) % 60
        return f"{m}:{s:02}"

    def _start_download(self, url, tag):
        req = QNetworkRequest(QUrl(url)); req.setAttribute(QNetworkRequest.Attribute.User, tag)
        self.nam.get(req)

    def _set_rounded_avatar(self, pix):
        s = 118; pix = pix.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        r = QPixmap(s, s); r.fill(Qt.GlobalColor.transparent)
        p = QPainter(r); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath(); path.addEllipse(0, 0, s, s)
        p.setClipPath(path); p.drawPixmap(0, 0, pix); p.end()
        self.lbl_avatar.setPixmap(r)

    def _round_image(self, pix, radius=12):
        if pix.isNull(): return pix
        r = QPixmap(pix.size()); r.fill(Qt.GlobalColor.transparent)
        p = QPainter(r); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(0, 0, pix.width(), pix.height(), radius, radius)
        p.setClipPath(path); p.drawPixmap(0, 0, pix); p.end()
        return r