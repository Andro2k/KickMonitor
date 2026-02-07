# frontend/pages/chat_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QCheckBox, QFrame, QComboBox, QSlider, QLineEdit,
    QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt
from frontend.factories import create_page_header
from frontend.theme import LAYOUT, THEME_DARK, STYLES
from frontend.utils import get_icon, get_icon_colored
from backend.services.chat_service import ChatService
from frontend.components.flow_layout import FlowLayout

class ChatPage(QWidget):
    def __init__(self, db, tts_worker, parent=None):
        super().__init__(parent)
        self.service = ChatService(db, tts_worker)
        self.voice_ids_map = []
        
        self.init_ui()
        self._load_initial_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # CONTENEDOR PRINCIPAL CON MARGENES
        content = QWidget()
        l_content = QVBoxLayout(content)
        l_content.setContentsMargins(*LAYOUT["level_03"])
        l_content.setSpacing(LAYOUT["space_01"])

        # 1. HEADER
        self._setup_header(l_content)
        
        # 2. AREA DE CONTROLES (RESPONSIVE FLOW)
        controls_container = QWidget()
        controls_layout = FlowLayout(controls_container, margin=0, spacing=10)
        
        # Tarjeta 1: Configuración de Voz
        self.card_tts = self._create_tts_card()
        self.card_tts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        controls_layout.addWidget(self.card_tts)
        
        # Tarjeta 2: Filtros y Acciones
        self.card_actions = self._create_actions_card()
        self.card_actions.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        controls_layout.addWidget(self.card_actions)
        
        l_content.addWidget(controls_container)

        # 3. CHAT LOG (Expandible)
        self._setup_chat_log(l_content)
        
        main_layout.addWidget(content)

    def _setup_header(self, layout):
        h_box = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)
        
        self.lbl_status = QLabel("Desconectado")
        self.lbl_status.setObjectName("subtitle")
        
        v_titles.addWidget(create_page_header("Monitor de Chat", "Gestión del chat y el TTS"))
        v_titles.addWidget(self.lbl_status)
        
        h_box.addLayout(v_titles)
        h_box.addStretch()
        
        layout.addLayout(h_box)

    # ==========================================
    # CREACIÓN DE TARJETAS
    # ==========================================
    def _create_tts_card(self):
        """Tarjeta con: Selector de Voz, Velocidad, Volumen."""
        frame = QFrame()
        frame.setMinimumWidth(320)
        frame.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(frame)
        l.setContentsMargins(*LAYOUT["level_03"])
        l.setSpacing(LAYOUT["space_01"])

        # Título
        h_head = QHBoxLayout()
        h_head.addWidget(QLabel("Configuración de Voz", objectName="h3"))
        h_head.addStretch()
        l.addLayout(h_head)

        # Selector
        self.c_voice = QComboBox()
        self.c_voice.setStyleSheet(STYLES["combobox"])
        self.c_voice.currentIndexChanged.connect(self._handle_settings_changed)
        l.addWidget(QLabel("Voz del Sistema:", styleSheet="color:#aaa; font-size:11px;"))
        l.addWidget(self.c_voice)

        # Sliders en Grid (Lado a Lado)
        grid = QGridLayout()
        self.s_rate = self._create_slider_widget("Velocidad", 50, 300)
        self.s_vol = self._create_slider_widget("Volumen", 0, 100)
        
        grid.addWidget(self.s_rate, 0, 0)
        grid.addWidget(self.s_vol, 0, 1)
        l.addLayout(grid)
        
        return frame

    def _create_actions_card(self):
        """Tarjeta con: Comando, Checkbox, Test, Mute."""
        frame = QFrame()
        frame.setMinimumWidth(320)
        frame.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(frame)
        l.setContentsMargins(*LAYOUT["level_03"])
        l.setSpacing(LAYOUT["space_01"])

        # Título
        l.addWidget(QLabel("Comportamiento", objectName="h3"))

        # Fila: Comando + Botones
        row_top = QHBoxLayout()
        
        # Input Comando
        self.txt_cmd_tts = QLineEdit()
        self.txt_cmd_tts.setPlaceholderText("!voz")
        self.txt_cmd_tts.setFixedWidth(80)
        self.txt_cmd_tts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_cmd_tts.setStyleSheet(STYLES["input_readonly"])
        self.txt_cmd_tts.editingFinished.connect(self._handle_command_saved)
        
        row_top.addWidget(QLabel("Trigger:", styleSheet="color:#aaa; font-weight:bold;"))
        row_top.addWidget(self.txt_cmd_tts)
        row_top.addStretch()
        
        # Botones de Acción
        btn_test = QPushButton(" Test Audio")
        btn_test.setIcon(get_icon("play-circle.svg"))
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet(STYLES["btn_nav"])
        btn_test.clicked.connect(self._handle_test_audio)
        
        self.voice_btn = QPushButton()
        self.voice_btn.setFixedSize(36, 36)
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setCheckable(True)
        self.voice_btn.setChecked(True) # Start unmuted
        self.voice_btn.clicked.connect(self._update_mute_visuals)
        
        row_top.addWidget(btn_test)
        row_top.addWidget(self.voice_btn)
        l.addLayout(row_top)

        # Separador
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {THEME_DARK['border']};")
        l.addWidget(sep)

        # Checkbox
        self.chk_command_only = QCheckBox("Solo leer si inicia con comando")
        self.chk_command_only.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_command_only.setStyleSheet(f"QCheckBox {{ color: {THEME_DARK['Gray_N1']}; spacing: 8px; }}")
        self.chk_command_only.stateChanged.connect(self._handle_filter_changed)
        l.addWidget(self.chk_command_only)

        return frame

    def _create_slider_widget(self, label_text, min_v, max_v):
        """Helper para crear un mini-widget de slider vertical u horizontal."""
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0,0,0,0); l.setSpacing(5)
        
        header = QHBoxLayout()
        lbl_name = QLabel(label_text, styleSheet="color:#aaa; font-size:11px;")
        lbl_val = QLabel(str(min_v), styleSheet=f"color:{THEME_DARK['Gray_N2']}; font-weight:bold; font-size:11px;")
        header.addWidget(lbl_name); header.addStretch(); header.addWidget(lbl_val)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        
        # Conexión interna para actualizar etiqueta
        slider.valueChanged.connect(lambda v: lbl_val.setText(str(v)))
        slider.valueChanged.connect(self._handle_settings_changed)
        
        l.addLayout(header)
        l.addWidget(slider)
        return w

    def _setup_chat_log(self, layout):
        layout.addWidget(QLabel("Historial en Vivo", objectName="h3"))
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlaceholderText("Esperando mensajes de Kick.")
        self.txt.setStyleSheet(STYLES["text_edit_log"])
        layout.addWidget(self.txt)

    # ==========================================
    # CARGA Y HANDLERS (Lógica igual)
    # ==========================================
    def _load_initial_state(self):
        self.c_voice.blockSignals(True)
        
        voices = self.service.get_available_voices()
        self.voice_ids_map = []
        self.c_voice.clear()
        for v in voices:
            self.c_voice.addItem(v["name"])
            self.voice_ids_map.append(v["id"])
        
        settings = self.service.get_tts_settings()
        self.txt_cmd_tts.setText(settings["command"])
        self.chk_command_only.setChecked(settings["filter_enabled"])
        
        # Sliders (buscamos el QSlider dentro del widget contenedor)
        self.s_rate.findChild(QSlider).setValue(settings["rate"])
        self.s_vol.findChild(QSlider).setValue(settings["volume"])
        
        if settings["voice_id"] in self.voice_ids_map:
            idx = self.voice_ids_map.index(settings["voice_id"])
            self.c_voice.setCurrentIndex(idx)
        
        self.c_voice.blockSignals(False)
        self._update_mute_visuals()

    def _handle_settings_changed(self):
        idx = self.c_voice.currentIndex()
        if idx < 0: return
        
        # Accedemos al valor real del slider
        rate_val = self.s_rate.findChild(QSlider).value()
        vol_val = self.s_vol.findChild(QSlider).value()
        
        self.service.save_tts_config(
            voice_id=self.voice_ids_map[idx],
            rate=rate_val,
            volume=vol_val
        )

    def _handle_command_saved(self):
        text = self.txt_cmd_tts.text().strip()
        if not text: text = "!voz"
        if not text.startswith("!"): text = "!" + text
        self.txt_cmd_tts.setText(text)
        if hasattr(self.service, 'save_tts_command'):
            self.service.save_tts_command(text)

    def _handle_filter_changed(self):
        self.service.set_filter_enabled(self.chk_command_only.isChecked())

    def _handle_test_audio(self):
        self._handle_settings_changed()
        self.service.tts.add_message("Prueba de audio, monitor activo.")

    def update_user_info(self, *args):
        pass

    def _update_mute_visuals(self):
        is_active = self.voice_btn.isChecked()
        icon_name = "volume_on.svg" if is_active else "volume_off.svg"
        color = THEME_DARK['NeonGreen_Main'] if is_active else THEME_DARK['Gray_N1']
        
        self.voice_btn.setIcon(get_icon_colored(icon_name, color))
        self.voice_btn.setStyleSheet(STYLES["btn_nav"])