# frontend/pages/chat_page.py

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QCheckBox, QFrame, QComboBox, QSlider, QLineEdit,
    QSizePolicy, QGridLayout, QScrollArea, QColorDialog
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
from frontend.factories import create_page_header
from frontend.theme import LAYOUT, THEME_DARK, STYLES
from frontend.utils import get_icon, get_icon_colored
from backend.services.chat_service import ChatService
from frontend.components.flow_layout import FlowLayout

class ChatPage(QWidget):
    def __init__(self, db, tts_worker, chat_overlay_worker=None, parent=None):
        super().__init__(parent)
        self.service = ChatService(db, tts_worker)
        self.chat_overlay = chat_overlay_worker
        self.voice_ids_map = []
        
        # Bandera para evitar guardar datos en BD mientras se carga la interfaz
        self._is_loading = True 
        
        self.overlay_colors = {"bg_color": "#000000", "text_color": "#ffffff"}
        
        # Mapeos internos para ComboBox
        self.anim_keys = ["fade", "pop", "slideLeft", "slideRight"]
        self.theme_keys = ["bubble", "transparent", "neon", "horizontal"]
        
        self.init_ui()
        self._load_initial_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        l_content = QVBoxLayout(content)
        l_content.setContentsMargins(*LAYOUT["level_03"])
        l_content.setSpacing(LAYOUT["space_01"])

        self._setup_header(l_content)
        
        controls_container = QWidget()
        controls_layout = FlowLayout(controls_container, margin=0, spacing=10)
        
        self.card_tts = self._create_tts_card()
        controls_layout.addWidget(self.card_tts)
        
        self.card_actions = self._create_actions_card()
        controls_layout.addWidget(self.card_actions)

        self.card_overlay_design = self._create_overlay_design_card()
        controls_layout.addWidget(self.card_overlay_design)

        self.card_overlay_behavior = self._create_overlay_behavior_card()
        controls_layout.addWidget(self.card_overlay_behavior)
        
        l_content.addWidget(controls_container)
        self._setup_chat_log(l_content)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _setup_header(self, layout):
        h_box = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)
        self.lbl_status = QLabel("Desconectado")
        self.lbl_status.setObjectName("subtitle")
        v_titles.addWidget(create_page_header("Monitor de Chat", "Gestión del chat, TTS y Overlay de OBS"))
        v_titles.addWidget(self.lbl_status)
        h_box.addLayout(v_titles)
        h_box.addStretch()
        layout.addLayout(h_box)

    # ==========================================
    # TARJETAS DE TTS
    # ==========================================
    def _create_tts_card(self):
        f = QFrame(); f.setMinimumWidth(320); f.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        l = QVBoxLayout(f); l.setContentsMargins(*LAYOUT["level_03"]); l.setSpacing(LAYOUT["space_01"])
        l.addWidget(QLabel("Configuración de Voz", objectName="h3"))
        
        self.c_voice = QComboBox(); self.c_voice.setStyleSheet(STYLES["combobox"]); self.c_voice.currentIndexChanged.connect(self._handle_tts_settings_changed)
        l.addWidget(QLabel("Voz del Sistema:", styleSheet="color:#aaa; font-size:11px;")); l.addWidget(self.c_voice)
        
        grid = QGridLayout()
        self.s_rate = self._create_slider_widget("Velocidad", 50, 300, self._handle_tts_settings_changed)
        self.s_vol = self._create_slider_widget("Volumen", 0, 100, self._handle_tts_settings_changed)
        grid.addWidget(self.s_rate, 0, 0); grid.addWidget(self.s_vol, 0, 1)
        l.addLayout(grid)
        
        l.addStretch() # <--- RESORTE: Empuja todo hacia arriba
        return f

    def _create_actions_card(self):
        f = QFrame(); f.setMinimumWidth(320); f.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        l = QVBoxLayout(f); l.setContentsMargins(*LAYOUT["level_03"]); l.setSpacing(LAYOUT["space_01"])
        l.addWidget(QLabel("Comportamiento TTS", objectName="h3"))
        
        row_top = QHBoxLayout()
        self.txt_cmd_tts = QLineEdit(); self.txt_cmd_tts.setPlaceholderText("!voz"); self.txt_cmd_tts.setFixedWidth(80)
        self.txt_cmd_tts.setAlignment(Qt.AlignmentFlag.AlignCenter); self.txt_cmd_tts.setStyleSheet(STYLES["input_readonly"]); self.txt_cmd_tts.editingFinished.connect(self._handle_command_saved)
        row_top.addWidget(QLabel("Trigger:", styleSheet="color:#aaa; font-weight:bold;")); row_top.addWidget(self.txt_cmd_tts); row_top.addStretch()
        
        btn_test = QPushButton(" Test Audio"); btn_test.setIcon(get_icon("play-circle.svg")); btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet(STYLES["btn_nav"]); btn_test.clicked.connect(self._handle_test_audio)
        self.voice_btn = QPushButton(); self.voice_btn.setFixedSize(36, 36); self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setCheckable(True); self.voice_btn.setChecked(True); self.voice_btn.clicked.connect(self._update_mute_visuals)
        row_top.addWidget(btn_test); row_top.addWidget(self.voice_btn); l.addLayout(row_top)
        
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {THEME_DARK['border']};"); l.addWidget(sep)
        
        self.chk_command_only = QCheckBox("Solo leer si inicia con comando"); self.chk_command_only.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_command_only.setStyleSheet(f"QCheckBox {{ color: {THEME_DARK['Gray_N1']}; spacing: 8px; }}"); self.chk_command_only.stateChanged.connect(self._handle_filter_changed)
        l.addWidget(self.chk_command_only)
        
        l.addStretch() # <--- RESORTE: Empuja todo hacia arriba
        return f

    # ==========================================
    # TARJETAS DE OVERLAY
    # ==========================================
    def _create_overlay_design_card(self):
        frame = QFrame()
        frame.setMinimumWidth(380) 
        frame.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        l = QVBoxLayout(frame)
        l.setContentsMargins(*LAYOUT["level_03"])
        l.setSpacing(LAYOUT["space_01"])

        h_head = QHBoxLayout()
        h_head.addWidget(QLabel("Diseño Overlay OBS", objectName="h3"))
        h_head.addStretch()
        
        self.btn_copy_url = QPushButton(" URL")
        self.btn_copy_url.setIcon(get_icon("copy.svg")); self.btn_copy_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_url.setStyleSheet(STYLES["btn_nav"]); self.btn_copy_url.clicked.connect(self._handle_copy_url)
        h_head.addWidget(self.btn_copy_url)

        btn_test = QPushButton(" Test")
        btn_test.setIcon(get_icon("play-circle.svg")); btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet(STYLES["btn_nav"]); btn_test.clicked.connect(self._handle_test_overlay)
        h_head.addWidget(btn_test)
        l.addLayout(h_head)

        h_combos = QHBoxLayout()
        self.c_anim = QComboBox(); self.c_anim.setStyleSheet(STYLES["combobox"])
        self.c_anim.addItems(["Aparecer (Fade)", "Rebotar (Pop)", "Deslizar Izq", "Deslizar Der"])
        self.c_theme = QComboBox(); self.c_theme.setStyleSheet(STYLES["combobox"])
        self.c_theme.addItems(["Burbuja Clásica", "Transparente", "Estilo Neón", "Horizontal (Línea)"])
        self.c_anim.currentIndexChanged.connect(self._handle_overlay_settings_changed)
        self.c_theme.currentIndexChanged.connect(self._handle_overlay_settings_changed)
        
        v_anim = QVBoxLayout(); v_anim.addWidget(QLabel("Animación:", styleSheet="color:#aaa; font-size:11px;")); v_anim.addWidget(self.c_anim)
        v_theme = QVBoxLayout(); v_theme.addWidget(QLabel("Diseño:", styleSheet="color:#aaa; font-size:11px;")); v_theme.addWidget(self.c_theme)
        h_combos.addLayout(v_anim); h_combos.addLayout(v_theme)
        l.addLayout(h_combos)

        grid = QGridLayout()
        self.s_font = self._create_slider_widget("Tamaño Texto (px)", 12, 40, self._handle_overlay_settings_changed)
        self.w_txt_color = self._create_color_picker_widget("Color Texto", "text_color")
        self.s_bg_op = self._create_slider_widget("Opacidad Fondo (%)", 0, 100, self._handle_overlay_settings_changed)
        self.w_bg_color = self._create_color_picker_widget("Color Fondo", "bg_color")
        self.s_radius = self._create_slider_widget("Bordes (px)", 0, 20, self._handle_overlay_settings_changed)
        self.s_space = self._create_slider_widget("Espaciado (px)", 0, 30, self._handle_overlay_settings_changed)
        
        grid.addWidget(self.s_font, 0, 0); grid.addWidget(self.w_txt_color, 0, 1)
        grid.addWidget(self.s_bg_op, 1, 0); grid.addWidget(self.w_bg_color, 1, 1)
        grid.addWidget(self.s_radius, 2, 0); grid.addWidget(self.s_space, 2, 1)
        l.addLayout(grid)
        
        l.addStretch() # <--- RESORTE: Empuja todo hacia arriba
        return frame

    def _create_overlay_behavior_card(self):
        frame = QFrame()
        frame.setMinimumWidth(320)
        frame.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        l = QVBoxLayout(frame)
        l.setContentsMargins(*LAYOUT["level_03"])
        l.setSpacing(LAYOUT["space_01"])

        l.addWidget(QLabel("Filtros y Comportamiento", objectName="h3"))

        check_style = f"QCheckBox {{ color: {THEME_DARK['Gray_N1']}; }}"
        self.chk_hide_bots = QCheckBox("Ocultar mensajes de bots"); self.chk_hide_bots.setStyleSheet(check_style)
        self.chk_hide_cmds = QCheckBox("Ocultar comandos ( ! )"); self.chk_hide_cmds.setStyleSheet(check_style)
        self.chk_show_time = QCheckBox("Mostrar hora del mensaje"); self.chk_show_time.setStyleSheet(check_style)
        self.chk_hide_old = QCheckBox("Ocultar mensajes antiguos"); self.chk_hide_old.setStyleSheet(check_style)
        
        self.chk_hide_bots.toggled.connect(self._handle_overlay_settings_changed)
        self.chk_hide_cmds.toggled.connect(self._handle_overlay_settings_changed)
        self.chk_show_time.toggled.connect(self._handle_overlay_settings_changed)
        self.chk_hide_old.toggled.connect(self._handle_overlay_settings_changed)

        l.addWidget(self.chk_hide_bots); l.addWidget(self.chk_hide_cmds); l.addWidget(self.chk_show_time); l.addWidget(self.chk_hide_old)

        self.s_hide_time = self._create_slider_widget("Desaparecer después de (Seg)", 5, 60, self._handle_overlay_settings_changed)
        l.addWidget(self.s_hide_time)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {THEME_DARK['border']};"); l.addWidget(sep)

        l.addWidget(QLabel("Usuarios ignorados (separados por coma):", styleSheet="color:#aaa; font-size:11px;"))
        self.txt_ignored = QLineEdit()
        self.txt_ignored.setPlaceholderText("usuario1, usuario2...")
        self.txt_ignored.setStyleSheet(STYLES["input_cmd"])
        self.txt_ignored.editingFinished.connect(self._handle_overlay_settings_changed)
        l.addWidget(self.txt_ignored)
        
        l.addStretch() # <--- RESORTE: Empuja todo hacia arriba
        return frame

    # Helpers UI
    def _create_slider_widget(self, label_text, min_v, max_v, callback=None):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(5)
        header = QHBoxLayout(); lbl_name = QLabel(label_text, styleSheet="color:#aaa; font-size:11px;")
        lbl_val = QLabel(str(min_v), styleSheet=f"color:{THEME_DARK['Gray_N2']}; font-weight:bold; font-size:11px;")
        header.addWidget(lbl_name); header.addStretch(); header.addWidget(lbl_val)
        
        slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(min_v, max_v)
        # La magia de actualizar el texto instantáneamente
        slider.valueChanged.connect(lambda v: lbl_val.setText(str(v)))
        if callback: slider.valueChanged.connect(callback)
        
        l.addLayout(header); l.addWidget(slider)
        return w

    def _create_color_picker_widget(self, label_text, color_key):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(5)
        lbl_name = QLabel(label_text, styleSheet="color:#aaa; font-size:11px;")
        
        btn_color = QPushButton(); btn_color.setFixedSize(60, 22); btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        def pick_color():
            current = QColor(self.overlay_colors[color_key])
            color = QColorDialog.getColor(current, self, f"Seleccionar {label_text}")
            if color.isValid():
                hex_color = color.name(); self.overlay_colors[color_key] = hex_color
                btn_color.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #555; border-radius: 4px;")
                self._handle_overlay_settings_changed()
        btn_color.clicked.connect(pick_color)
        
        if color_key == "bg_color": self.btn_bg_color = btn_color
        elif color_key == "text_color": self.btn_text_color = btn_color
        
        h = QHBoxLayout(); h.addWidget(btn_color); h.addStretch()
        l.addWidget(lbl_name); l.addLayout(h)
        return w

    def _setup_chat_log(self, layout):
        layout.addWidget(QLabel("Historial en Vivo", objectName="h3"))
        self.txt = QTextEdit()
        self.txt.setReadOnly(True); self.txt.setMinimumHeight(300) 
        self.txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.txt.setPlaceholderText("Esperando mensajes de Kick."); self.txt.setStyleSheet(STYLES["text_edit_log"])
        layout.addWidget(self.txt)

    # ==========================================
    # CARGA Y GUARDADO
    # ==========================================
    def _load_initial_state(self):
        self._is_loading = True # Activamos bandera de "carga silenciosa"
        
        # 1. Carga TTS
        voices = self.service.get_available_voices()
        self.voice_ids_map = []
        self.c_voice.clear()
        for v in voices:
            self.c_voice.addItem(v["name"]); self.voice_ids_map.append(v["id"])
        
        tts_cfg = self.service.get_tts_settings()
        self.txt_cmd_tts.setText(tts_cfg["command"])
        self.chk_command_only.setChecked(tts_cfg["filter_enabled"])
        
        # Como las señales NO están bloqueadas, setValue() actualizará el texto (lbl_val) de la UI automáticamente
        self.s_rate.findChild(QSlider).setValue(tts_cfg["rate"])
        self.s_vol.findChild(QSlider).setValue(tts_cfg["volume"])
        
        if tts_cfg["voice_id"] in self.voice_ids_map: 
            self.c_voice.setCurrentIndex(self.voice_ids_map.index(tts_cfg["voice_id"]))
            
        self._update_mute_visuals()

        # 2. Carga Overlay
        ov_cfg = self.service.get_chat_overlay_settings()
        
        self.overlay_colors["bg_color"] = ov_cfg["bg_color"]
        self.overlay_colors["text_color"] = ov_cfg["text_color"]
        self.btn_bg_color.setStyleSheet(f"background-color: {ov_cfg['bg_color']}; border: 1px solid #555; border-radius: 4px;")
        self.btn_text_color.setStyleSheet(f"background-color: {ov_cfg['text_color']}; border: 1px solid #555; border-radius: 4px;")

        self.c_anim.setCurrentIndex(self.anim_keys.index(ov_cfg["animation"]))
        self.c_theme.setCurrentIndex(self.theme_keys.index(ov_cfg["theme"]))
        self.chk_hide_bots.setChecked(ov_cfg["hide_bots"])
        self.chk_hide_cmds.setChecked(ov_cfg["hide_cmds"])
        self.chk_show_time.setChecked(ov_cfg["show_time"])
        self.chk_hide_old.setChecked(ov_cfg["hide_old"])
        self.txt_ignored.setText(ov_cfg["ignored_users"])

        self.s_font.findChild(QSlider).setValue(ov_cfg["font_size"])
        self.s_bg_op.findChild(QSlider).setValue(ov_cfg["bg_opacity"])
        self.s_radius.findChild(QSlider).setValue(ov_cfg["border_radius"])
        self.s_space.findChild(QSlider).setValue(ov_cfg["spacing"])
        self.s_hide_time.findChild(QSlider).setValue(ov_cfg["hide_time"])
        
        self._is_loading = False # Terminó la carga silenciosa
        
        # Disparamos manualmente los guardados iniciales para enviar a OBS
        self._handle_overlay_settings_changed()
        self._handle_tts_settings_changed()

    def _handle_overlay_settings_changed(self):
        if getattr(self, '_is_loading', False): return # Si está cargando la UI, ignorar guardado en BD
        
        font_size = self.s_font.findChild(QSlider).value()
        bg_opacity = self.s_bg_op.findChild(QSlider).value() 
        radius = self.s_radius.findChild(QSlider).value()
        space = self.s_space.findChild(QSlider).value()
        bg_hex = self.overlay_colors["bg_color"]
        text_hex = self.overlay_colors["text_color"]

        anim_val = self.anim_keys[self.c_anim.currentIndex()]
        theme_val = self.theme_keys[self.c_theme.currentIndex()]
        h_bots = self.chk_hide_bots.isChecked()
        h_cmds = self.chk_hide_cmds.isChecked()
        s_time = self.chk_show_time.isChecked()
        h_old = self.chk_hide_old.isChecked()
        h_time_val = self.s_hide_time.findChild(QSlider).value()
        ignored_val = self.txt_ignored.text()

        config_to_save = {
            "font_size": font_size, "bg_opacity": bg_opacity,
            "border_radius": radius, "spacing": space,
            "bg_color": bg_hex, "text_color": text_hex,
            "animation": anim_val, "theme": theme_val,
            "hide_bots": h_bots, "hide_cmds": h_cmds,
            "show_time": s_time, "hide_old": h_old,
            "hide_time": h_time_val, "ignored_users": ignored_val
        }
        self.service.save_chat_overlay_settings(config_to_save)
        
        if not self.chat_overlay: return
        hex_clean = bg_hex.lstrip('#')
        rgb = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
        rgba_bg = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {bg_opacity / 100.0})"
        
        payload_obs = {
            "--font-size": f"{font_size}px",
            "--msg-bg-color": rgba_bg,
            "--text-color": text_hex,
            "--border-radius": f"{radius}px",
            "--msg-spacing": f"{space}px",
            "animation": anim_val,
            "theme": theme_val,
            "show_time": s_time,
            "hide_old": h_old,
            "hide_time": h_time_val
        }
        self.chat_overlay.update_chat_styles(payload_obs)

    # ==========================================
    # OTROS EVENTOS EXISTENTES
    # ==========================================
    def _handle_tts_settings_changed(self):
        if getattr(self, '_is_loading', False): return # Si está cargando la UI, ignorar guardado en BD
        
        idx = self.c_voice.currentIndex()
        if idx < 0: return
        self.service.save_tts_config(
            voice_id=self.voice_ids_map[idx],
            rate=self.s_rate.findChild(QSlider).value(),
            volume=self.s_vol.findChild(QSlider).value()
        )

    def _handle_test_overlay(self):
        if not self.chat_overlay: return
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M")
        
        self.chat_overlay.send_chat_message_to_overlay(
            sender="KickMonitor", content="¡Este es un mensaje de prueba para ajustar el diseño en OBS!",
            badges=[], user_color="#53fc18", timestamp=now_str
        )
        
    def _handle_copy_url(self):
        QApplication.clipboard().setText("http://localhost:6001/chat")
        self.btn_copy_url.setText("¡Copiado!"); self.btn_copy_url.setStyleSheet(STYLES["btn_nav"] + f"color: {THEME_DARK['NeonGreen_Main']};")
        QTimer.singleShot(1500, lambda: (self.btn_copy_url.setText(" URL"), self.btn_copy_url.setStyleSheet(STYLES["btn_nav"])))

    def _handle_command_saved(self):
        text = self.txt_cmd_tts.text().strip()
        if not text: text = "!voz"
        if not text.startswith("!"): text = "!" + text
        self.txt_cmd_tts.setText(text)
        if hasattr(self.service, 'save_tts_command'): self.service.save_tts_command(text)

    def _handle_filter_changed(self): 
        if getattr(self, '_is_loading', False): return
        self.service.set_filter_enabled(self.chk_command_only.isChecked())
        
    def _handle_test_audio(self): 
        self._handle_tts_settings_changed(); self.service.tts.add_message("Prueba de audio, monitor activo.")
        
    def update_user_info(self, *args): pass

    def _update_mute_visuals(self):
        is_active = self.voice_btn.isChecked()
        icon_name = "volume_on.svg" if is_active else "volume_off.svg"
        color = THEME_DARK['NeonGreen_Main'] if is_active else THEME_DARK['Gray_N1']
        self.voice_btn.setIcon(get_icon_colored(icon_name, color)); self.voice_btn.setStyleSheet(STYLES["btn_nav"])