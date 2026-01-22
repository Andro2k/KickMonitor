# frontend/components/music_card.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QCheckBox, 
    QLineEdit
)
from PyQt6.QtCore import Qt, QSize
from frontend.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from frontend.utils import get_icon

class MusicPlayerPanel(QFrame):
    def __init__(self, service, initial_worker, parent=None):
        super().__init__(parent)
        self.service = service
        self.worker = initial_worker
        
        self._setup_style()
        self._setup_ui()

    def set_worker(self, new_worker):
        """Cambia el worker que controla este panel (Spotify o YTMusic)."""
        self.worker = new_worker

    def _setup_style(self):
        self.setMinimumWidth(500) 
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 16px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(*LAYOUT["margins"])
        main_layout.setSpacing(LAYOUT["spacing"])

        # 1. SECCIÓN REPRODUCTOR
        player_container = QWidget()
        player_container.setStyleSheet("background: transparent; border: none;")
        player_row = QHBoxLayout(player_container)
        player_row.setContentsMargins(0,0,0,0)
        player_row.setSpacing(LAYOUT["spacing"])

        # Carátula
        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(110, 110)
        self.lbl_art.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 12px;")
        self.lbl_art.setScaledContents(True)
        player_row.addWidget(self.lbl_art)

        # Info + Controles
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_song = QLabel("No Song Playing")
        self.lbl_song.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-weight: bold; font-size: 14px;")
        self.lbl_song.setMaximumHeight(40) 
        self.lbl_song.setWordWrap(True)
        
        self.lbl_artist = QLabel("Artist Name")
        self.lbl_artist.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 12px;")
        
        right_col.addWidget(self.lbl_song)
        right_col.addWidget(self.lbl_artist)
        right_col.addSpacing(4)

        # Tiempos
        time_layout = QHBoxLayout()
        self.lbl_curr = QLabel("0:00", styleSheet="color: #888; font-size: 11px;")
        self.lbl_total = QLabel("0:00", styleSheet="color: #888; font-size: 11px;")
        time_layout.addWidget(self.lbl_curr)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_total)
        right_col.addLayout(time_layout)

        # Barra
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {THEME_DARK['Black_N4']}; border-radius: 3px; }} 
            QProgressBar::chunk {{ background: {THEME_DARK['NeonGreen_Main']}; border-radius: 3px; }}
        """)
        right_col.addWidget(self.progress)
        right_col.addSpacing(6)

        # --- CORRECCIÓN AQUÍ: Controles ---
        ctrls = QHBoxLayout()
        ctrls.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ctrls.setSpacing(15)
        
        # Botón Anterior
        ctrls.addWidget(self._create_icon_btn("prev.svg", lambda: self._safe_call("prev_track"), 18))
        
        # Botón Play/Pause (Ahora sí se agrega al layout)
        self.btn_play = self._create_icon_btn("play-circle.svg", lambda: self._safe_call("play_pause"), 30)
        ctrls.addWidget(self.btn_play) 
        
        # Botón Siguiente
        ctrls.addWidget(self._create_icon_btn("next.svg", lambda: self._safe_call("next_track"), 18))
        
        right_col.addLayout(ctrls)
        player_row.addLayout(right_col)
        main_layout.addWidget(player_container, stretch=1)

        # 2. SEPARADOR
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {THEME_DARK['border']}; margin: 2px;")
        main_layout.addWidget(sep)

        # 3. COMANDOS
        cmds_container = QWidget()
        cmds_container.setStyleSheet("background: transparent; border: none;")
        cmds_container.setFixedWidth(170)
        cmds_col = QVBoxLayout(cmds_container)
        cmds_col.setContentsMargins(5,0,0,0)
        cmds_col.setSpacing(6)
        cmds_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        cmds_col.addWidget(QLabel("COMANDOS", styleSheet="color:#666; font-size:10px; font-weight:bold;"))
        
        cmds = self.service.get_music_commands_list()
        for key, default, desc in cmds:
            self._add_cmd_input(cmds_col, key, default)
            
        cmds_col.addStretch()
        main_layout.addWidget(cmds_container)

    def _safe_call(self, method_name):
        """Llama al método del worker activo si existe."""
        if self.worker:
            if hasattr(self.worker, method_name):
                getattr(self.worker, method_name)()
            elif method_name == "next_track" and hasattr(self.worker, "skip"):
                 # Compatibilidad YTMusic
                 self.worker.skip()
            else:
                print(f"Worker {type(self.worker)} no tiene método {method_name}")

    def _create_icon_btn(self, icon, func, size):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setIconSize(QSize(size, size))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(STYLES["btn_icon_ghost"])
        btn.clicked.connect(func)
        return btn

    def _add_cmd_input(self, parent_layout, key, default):
        val = self.service.get_command_value(key, default)
        is_active = self.service.get_command_active(key)
        
        container = QWidget()
        container.setStyleSheet("border:none; background:transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(6)
        
        chk = QCheckBox()
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(get_switch_style())
        chk.setChecked(is_active)
        chk.clicked.connect(lambda c: self.service.save_command_active(key, c))

        txt = QLineEdit(val)
        txt.setPlaceholderText(default)
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setStyleSheet(STYLES["input_cmd"])
        txt.editingFinished.connect(lambda: self.service.save_command(key, txt.text()))
        
        layout.addWidget(chk)
        layout.addWidget(txt)
        parent_layout.addWidget(container)

    def update_state(self, title, artist, art_pixmap, prog, dur, is_playing):
        self.lbl_song.setText(title[:45] + "..." if len(title) > 45 else title)
        self.lbl_artist.setText(artist)
        self.btn_play.setIcon(get_icon("pause.svg" if is_playing else "play-circle.svg"))
        
        if art_pixmap: self.lbl_art.setPixmap(art_pixmap)
        
        if dur > 0:
            self.progress.setRange(0, dur)
            self.progress.setValue(prog)
            self.lbl_curr.setText(self._format_time(prog))
            self.lbl_total.setText(self._format_time(dur))
        else:
            self.progress.setValue(0)
            self.lbl_curr.setText("--:--")
            self.lbl_total.setText("--:--")

    def _format_time(self, ms):
        s = (ms // 1000) % 60
        m = (ms // (1000 * 60)) % 60
        return f"{m}:{s:02}"