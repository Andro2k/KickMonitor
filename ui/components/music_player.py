# ui/components/music_player.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QCheckBox, 
    QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from ui.theme import THEME_DARK, get_switch_style
from ui.utils import get_icon

class MusicPlayerPanel(QFrame):
    def __init__(self, service, spotify_worker, parent=None):
        super().__init__(parent)
        self.service = service
        self.spotify = spotify_worker
        
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setMinimumWidth(340)
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

        # --- REPRODUCTOR ---
        player_row = QHBoxLayout()
        player_row.setSpacing(15)

        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(100, 100)
        self.lbl_art.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 10px;")
        self.lbl_art.setScaledContents(True)
        player_row.addWidget(self.lbl_art)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        
        self.lbl_song = QLabel("No Song Playing", styleSheet=f"color: {THEME_DARK['White_N1']}; font-weight: bold; font-size: 15px;")
        self.lbl_artist = QLabel("Artist Name", styleSheet=f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 12px;")
        
        time_layout = QHBoxLayout()
        self.lbl_curr = QLabel("0:00", styleSheet="color: #888; font-size: 10px;")
        self.lbl_total = QLabel("0:00", styleSheet="color: #888; font-size: 10px;")
        time_layout.addWidget(self.lbl_curr); time_layout.addStretch(); time_layout.addWidget(self.lbl_total)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ background: {THEME_DARK['Black_N4']}; border-radius: 3px; }} QProgressBar::chunk {{ background: {THEME_DARK['NeonGreen_Main']}; border-radius: 3px; }}")

        ctrls = QHBoxLayout()
        ctrls.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.btn_play = self._create_icon_btn("play-circle.svg", self.spotify.play_pause, 26)
        ctrls.addWidget(self._create_icon_btn("prev.svg", self.spotify.prev_track, 20))
        ctrls.addSpacing(10)
        ctrls.addWidget(self.btn_play)
        ctrls.addSpacing(10)
        ctrls.addWidget(self._create_icon_btn("next.svg", self.spotify.next_track, 20))

        info_col.addWidget(self.lbl_song); info_col.addWidget(self.lbl_artist)
        info_col.addLayout(time_layout); info_col.addWidget(self.progress); info_col.addLayout(ctrls)
        
        player_row.addLayout(info_col)
        main_layout.addLayout(player_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {THEME_DARK['border']}; margin: 5px 0;")
        main_layout.addWidget(sep)

        main_layout.addWidget(QLabel("COMANDOS", styleSheet="color:#666; font-size:10px; font-weight:bold;"))
        grid = QGridLayout(); grid.setSpacing(10)
        cmds = self.service.get_music_commands_list()
        for i, (key, default, desc) in enumerate(cmds):
            r, c = divmod(i, 2)
            self._add_cmd_input(grid, r, c, key, default, desc)
        main_layout.addLayout(grid)
        main_layout.addStretch()

    def _create_icon_btn(self, icon, func, size):
        btn = QPushButton(); btn.setIcon(get_icon(icon)); btn.setIconSize(QSize(size, size))
        btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setStyleSheet("background: transparent; border: none;")
        btn.clicked.connect(func); return btn

    def _add_cmd_input(self, grid, r, c, key, default, desc):
        val = self.service.get_command_value(key, default)
        is_active = self.service.get_command_active(key)
        container = QWidget(); container.setStyleSheet("border:none; background:transparent;")
        layout = QHBoxLayout(container); layout.setContentsMargins(0,0,0,0); layout.setSpacing(6)
        
        chk = QCheckBox(); chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(get_switch_style()); chk.setChecked(is_active)
        chk.clicked.connect(lambda chk: self.service.save_command_active(key, chk))

        txt = QLineEdit(val); txt.setPlaceholderText(default)
        txt.setStyleSheet(f"QLineEdit {{ background: {THEME_DARK['Black_N4']}; color: {THEME_DARK['NeonGreen_Main']}; border: none; border-radius: 4px; padding: 4px; font-family: Consolas; font-weight: bold; font-size: 11px; }} QLineEdit:focus {{ background: {THEME_DARK['Black_N2']}; }}")
        
        def save():
            t = txt.text().strip()
            if t and not t.startswith("!"): t = "!" + t; txt.setText(t)
            self.service.save_command(key, t)
        txt.editingFinished.connect(save)
        
        layout.addWidget(chk); layout.addWidget(txt, 1)
        grid.addWidget(container, r, c)

    def update_state(self, title, artist, art_pixmap, prog, dur, is_playing):
        self.lbl_song.setText(title[:30] + "..." if len(title) > 30 else title)
        self.lbl_artist.setText(artist)
        self.btn_play.setIcon(get_icon("pause.svg" if is_playing else "play-circle.svg"))
        if art_pixmap: self.lbl_art.setPixmap(art_pixmap)
        if dur > 0:
            self.progress.setRange(0, dur); self.progress.setValue(prog)
            self.lbl_curr.setText(self._format_time(prog))
            self.lbl_total.setText(self._format_time(dur))

    def _format_time(self, ms):
        s = (ms // 1000) % 60; m = (ms // (1000 * 60)) % 60
        return f"{m}:{s:02}"