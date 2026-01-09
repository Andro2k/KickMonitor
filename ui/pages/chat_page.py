# ui/pages/chat_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QCheckBox, QFrame, QComboBox, QSlider, QLineEdit
)
from PyQt6.QtCore import QSize, Qt
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.utils import get_icon
from services.chat_service import ChatService

class ChatPage(QWidget):
    def __init__(self, db, tts_worker, parent=None):
        super().__init__(parent)
        
        # 1. Lógica de Negocio (Servicio)
        self.service = ChatService(db, tts_worker)
        
        # 2. Estado Interno UI
        self.voice_ids_map = []
        
        # 3. Inicialización
        self.init_ui()
        self._load_initial_state()

    # ==========================================
    # 1. CONSTRUCCIÓN DE UI (SETUP)
    # ==========================================
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*LAYOUT["margins"])
        main_layout.setSpacing(LAYOUT["spacing"])

        # Construcción modular
        self._setup_header(main_layout)
        self._setup_tts_toolbar(main_layout)
        self._setup_filters_bar(main_layout)
        self._setup_chat_log(main_layout)

    def _setup_header(self, layout):
        h_box = QHBoxLayout()
        v_titles = QVBoxLayout()

        lbl_title = QLabel("Monitor de Chat")
        lbl_title.setObjectName("h2")
        
        # Etiqueta pública para que el Controller actualice el estado (En Vivo/Desconectado)
        self.lbl_status = QLabel("Desconectado")
        self.lbl_status.setObjectName("subtitle")
        
        v_titles.addWidget(lbl_title)
        v_titles.addWidget(self.lbl_status)
        
        h_box.addLayout(v_titles)
        h_box.addStretch()
        layout.addLayout(h_box)

    def _setup_tts_toolbar(self, layout):
        self.frame_tts = QFrame()
        self.frame_tts.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border-radius: 8px; 
                
            }}
        """)
        
        toolbar = QHBoxLayout(self.frame_tts)
        toolbar.setContentsMargins(*LAYOUT["margins"])
        toolbar.setSpacing(LAYOUT["spacing"])

        # Icono
        lbl_ico = QLabel()
        lbl_ico.setPixmap(get_icon("voice.svg").pixmap(QSize(18,18)))
        lbl_ico.setStyleSheet("border:none; opacity: 0.8;")
        toolbar.addWidget(lbl_ico)

        # Selector de Voz
        self.c_voice = QComboBox()
        self.c_voice.setStyleSheet(STYLES["combobox"])
        self.c_voice.setFixedWidth(200)
        self.c_voice.currentIndexChanged.connect(self._handle_settings_changed)
        toolbar.addWidget(self.c_voice)

        # Sliders (Velocidad y Volumen)
        self.s_rate = self._create_slider(50, 300, "Velocidad:", toolbar)
        self.s_vol = self._create_slider(0, 100, "Volumen:", toolbar)

        # Comando disparador
        toolbar.addWidget(QLabel("Comando:", styleSheet="border:none; color:#aaa; font-size:12px;"))
        self.txt_cmd_tts = QLineEdit()
        self.txt_cmd_tts.setPlaceholderText("!voz")
        self.txt_cmd_tts.setFixedWidth(70)
        self.txt_cmd_tts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_cmd_tts.setStyleSheet(STYLES["input_cmd"])
        self.txt_cmd_tts.editingFinished.connect(self._handle_command_saved)
        toolbar.addWidget(self.txt_cmd_tts)

        toolbar.addStretch()
        
        # Botón Test
        btn_test = QPushButton("Test")
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setFixedSize(52, 32)
        btn_test.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 4px;")
        btn_test.clicked.connect(self._handle_test_audio)
        toolbar.addWidget(btn_test)

        layout.addWidget(self.frame_tts)

    def _setup_filters_bar(self, layout):
        h_box = QHBoxLayout()
        
        self.chk_command_only = QCheckBox("Solo leer mensajes que inicien con el comando")
        self.chk_command_only.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_command_only.stateChanged.connect(self._handle_filter_changed)
        
        # Botón Toggle Mute (Bocina)
        self.voice_btn = QPushButton()
        self.voice_btn.setFixedSize(38, 38)
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.voice_btn.setCheckable(True)
        self.voice_btn.setChecked(True)
        self.voice_btn.clicked.connect(self._update_mute_visuals)

        h_box.addWidget(self.chk_command_only)
        h_box.addStretch()
        h_box.addWidget(self.voice_btn)
        layout.addLayout(h_box)

    def _setup_chat_log(self, layout):
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlaceholderText("Esperando mensajes de Kick...")
        self.txt.setStyleSheet(f"""
            QTextEdit {{
                background-color: {THEME_DARK['Black_N0']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self.txt)

    # ==========================================
    # 2. CARGA DE DATOS (STATE)
    # ==========================================
    def _load_initial_state(self):
        """Lee configuración de DB y Voces del sistema."""
        # Bloqueamos señales para que al setear valores no dispare eventos de guardado
        self.c_voice.blockSignals(True)
        
        # 1. Voces del Sistema
        voices = self.service.get_available_voices()
        self.voice_ids_map = []
        for v in voices:
            self.c_voice.addItem(v["name"])
            self.voice_ids_map.append(v["id"])
        
        # 2. Configuración Guardada
        settings = self.service.get_tts_settings()
        
        self.txt_cmd_tts.setText(settings["command"])
        self.chk_command_only.setChecked(settings["filter_enabled"])
        self.s_rate.setValue(settings["rate"])
        self.s_vol.setValue(settings["volume"])
        
        # Restaurar voz seleccionada
        if settings["voice_id"] in self.voice_ids_map:
            idx = self.voice_ids_map.index(settings["voice_id"])
            self.c_voice.setCurrentIndex(idx)
        
        self.c_voice.blockSignals(False)
        self._update_mute_visuals()

    # ==========================================
    # 3. MANEJO DE EVENTOS (HANDLERS)
    # ==========================================
    def _handle_settings_changed(self):
        """Guarda configuración al mover sliders o cambiar combo."""
        idx = self.c_voice.currentIndex()
        if idx < 0: return
        
        self.service.save_tts_config(
            voice_id=self.voice_ids_map[idx],
            rate=self.s_rate.value(),
            volume=self.s_vol.value()
        )

    def _handle_command_saved(self):
        # 1. Obtener el texto quitando espacios extra
        text = self.txt_cmd_tts.text().strip()
    
        if not text:
            text = "!voz"

        if not text.startswith("!"):
            text = "!" + text
        
        self.txt_cmd_tts.setText(text)
        
        if hasattr(self.service, 'save_tts_command'):
            self.service.save_tts_command(text)

    def _handle_filter_changed(self):
        self.service.set_filter_enabled(self.chk_command_only.isChecked())

    def _handle_test_audio(self):
        # Aseguramos que la config actual esté guardada antes de probar
        self._handle_settings_changed()
        self.service.tts.add_message("Prueba de audio del monitor de chat.")

    def update_user_info(self, *args):
        """
        Slot para recibir señales de info de usuario.
        (Actualmente no mostramos info específica aquí, pero mantenemos la compatibilidad)
        """
        pass

    # ==========================================
    # 4. HELPERS VISUALES
    # ==========================================
    def _update_mute_visuals(self):
        is_active = self.voice_btn.isChecked()
        
        icon_name = "volume_on.svg" if is_active else "volume_off.svg"
        bg_color = THEME_DARK['NeonGreen_Main'] if is_active else THEME_DARK['Black_N4']
        border = "none" if is_active else "1px solid #555"
        
        self.voice_btn.setIcon(get_icon(icon_name))
        self.voice_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {bg_color}; 
                border-radius: 19px; 
                border: {border}; 
            }}
        """)

    def _create_slider(self, min_v, max_v, label_text, parent_layout):
        # 1. El Título del Slider
        parent_layout.addWidget(QLabel(label_text, styleSheet="border:none; color:#aaa; font-size:12px;"))
        
        # 2. Contenedor horizontal para [Slider] [Numero]
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(container)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(5)

        # 3. El Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setStyleSheet("background: transparent;")
        slider.setRange(min_v, max_v)
        slider.setFixedWidth(100)
        
        # 4. El Label del Valor (NUEVO)
        val_label = QLabel(str(min_v))
        val_label.setFixedWidth(35) # Ancho fijo para que no "baile" la interfaz al cambiar de 9 a 10
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_label.setStyleSheet("color: #fff; font-weight: bold; font-size: 11px; border: none;")
        
        # --- LA MAGIA ---
        slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
        slider.valueChanged.connect(self._handle_settings_changed)
        
        # Agregamos ambos al contenedor fila
        row.addWidget(slider)
        row.addWidget(val_label)
        
        # Agregamos el contenedor al layout padre
        parent_layout.addWidget(container)
        
        return slider