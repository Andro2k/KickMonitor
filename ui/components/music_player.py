# ui/components/music_player.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QCheckBox, 
    QLineEdit
)
from PyQt6.QtCore import Qt, QSize
from ui.theme import LAYOUT, THEME_DARK, get_switch_style
from ui.utils import get_icon

class MusicPlayerPanel(QFrame):
    def __init__(self, service, spotify_worker, parent=None):
        super().__init__(parent)
        self.service = service
        self.spotify = spotify_worker
        
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setMinimumWidth(480) 
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 16px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

    def _setup_ui(self):
        # --- LAYOUT PRINCIPAL HORIZONTAL ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(*LAYOUT["margins"])
        main_layout.setSpacing(LAYOUT["spacing"])

        # ==========================================
        # COLUMNA IZQUIERDA: REPRODUCTOR
        # ==========================================
        player_container = QWidget()
        player_container.setStyleSheet("background: transparent; border: none;")
        player_col = QVBoxLayout(player_container)
        player_col.setContentsMargins(0,0,0,0)
        player_col.setSpacing(LAYOUT["spacing"])

        # 1. Info + Arte
        info_row = QHBoxLayout()
        info_row.setSpacing(15)

        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(100, 100) # Un poco más pequeño para ajustar espacio
        self.lbl_art.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 8px;")
        self.lbl_art.setScaledContents(True)
        info_row.addWidget(self.lbl_art)

        # Textos
        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        txt_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_song = QLabel("No Song Playing")
        self.lbl_song.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-weight: bold; font-size: 16px;")
        self.lbl_song.setWordWrap(True)
        
        self.lbl_artist = QLabel("Artist Name")
        self.lbl_artist.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 14px;")
        
        txt_col.addWidget(self.lbl_song)
        txt_col.addWidget(self.lbl_artist)
        info_row.addLayout(txt_col)
        
        player_col.addLayout(info_row)

        # 2. Tiempos y Barra
        time_layout = QHBoxLayout()
        self.lbl_curr = QLabel("0:00", styleSheet="color: #888; font-size: 12px;")
        self.lbl_total = QLabel("0:00", styleSheet="color: #888; font-size: 12px;")
        time_layout.addWidget(self.lbl_curr)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_total)
        player_col.addLayout(time_layout)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ background: {THEME_DARK['Black_N4']}; border-radius: 3px; }} QProgressBar::chunk {{ background: {THEME_DARK['NeonGreen_Main']}; border-radius: 3px; }}")
        player_col.addWidget(self.progress)

        # 3. Controles
        ctrls = QHBoxLayout()
        ctrls.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ctrls.setSpacing(20)
        self.btn_play = self._create_icon_btn("play-circle.svg", self.spotify.play_pause, 32)
        ctrls.addWidget(self._create_icon_btn("prev.svg", self.spotify.prev_track, 20))
        ctrls.addWidget(self.btn_play)
        ctrls.addWidget(self._create_icon_btn("next.svg", self.spotify.next_track, 20))
        player_col.addLayout(ctrls)

        main_layout.addWidget(player_container, stretch=1)

        # ==========================================
        # SEPARADOR VERTICAL
        # ==========================================
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {THEME_DARK['border']}; margin: 0.5px;")
        main_layout.addWidget(sep)

        # ==========================================
        # COLUMNA DERECHA: COMANDOS
        # ==========================================
        cmds_container = QWidget()
        cmds_container.setStyleSheet("background: transparent; border: none;")
        cmds_container.setFixedWidth(180) # Ancho fijo para los comandos
        
        cmds_col = QVBoxLayout(cmds_container)
        cmds_col.setContentsMargins(0,0,0,0)
        cmds_col.setSpacing(8)
        cmds_col.setAlignment(Qt.AlignmentFlag.AlignTop) # Alinear arriba

        cmds_col.addWidget(QLabel("COMANDOS", styleSheet="color:#666; font-size:10px; font-weight:bold; margin-bottom:5px;"))
        
        # Generar lista de comandos
        cmds = self.service.get_music_commands_list()
        for key, default, desc in cmds:
            self._add_cmd_input(cmds_col, key, default)
            
        cmds_col.addStretch() # Empujar todo hacia arriba
        main_layout.addWidget(cmds_container)

    def _create_icon_btn(self, icon, func, size):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setIconSize(QSize(size, size))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("background: transparent; border: none;")
        btn.clicked.connect(func)
        return btn

    def _add_cmd_input(self, parent_layout, key, default):
        """Añade un par (Switch + Input) al layout vertical dado."""
        val = self.service.get_command_value(key, default)
        is_active = self.service.get_command_active(key)
        
        container = QWidget()
        container.setStyleSheet("border:none; background:transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(8)
        
        chk = QCheckBox()
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(get_switch_style())
        chk.setChecked(is_active)
        chk.clicked.connect(lambda c: self.service.save_command_active(key, c))

        txt = QLineEdit(val)
        txt.setPlaceholderText(default)
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setStyleSheet(f"""
            QLineEdit {{ 
                background: {THEME_DARK['Black_N4']}; 
                color: {THEME_DARK['NeonGreen_Main']}; 
                border: none; border-radius: 6px; 
                padding: 4px; font-family: Consolas; 
                font-weight: bold; font-size: 11px; 
            }} 
            QLineEdit:focus {{ background: {THEME_DARK['Black_N2']}; border: 1px solid {THEME_DARK['NeonGreen_Main']}; }}
        """)
        
        def save():
            t = txt.text().strip()
            if t and not t.startswith("!"): 
                t = "!" + t
                txt.setText(t)
            self.service.save_command(key, t)
            
        txt.editingFinished.connect(save)
        
        layout.addWidget(chk)
        layout.addWidget(txt)
        parent_layout.addWidget(container)

    def update_state(self, title, artist, art_pixmap, prog, dur, is_playing):
        self.lbl_song.setText(title[:40] + "..." if len(title) > 40 else title)
        self.lbl_artist.setText(artist)
        self.btn_play.setIcon(get_icon("pause.svg" if is_playing else "play-circle.svg"))
        if art_pixmap: 
            self.lbl_art.setPixmap(art_pixmap)
        if dur > 0:
            self.progress.setRange(0, dur)
            self.progress.setValue(prog)
            self.lbl_curr.setText(self._format_time(prog))
            self.lbl_total.setText(self._format_time(dur))

    def _format_time(self, ms):
        s = (ms // 1000) % 60
        m = (ms // (1000 * 60)) % 60
        return f"{m}:{s:02}"