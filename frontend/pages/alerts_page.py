# frontend/pages/alerts_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, 
    QApplication, QLabel, QComboBox, QLineEdit, QTextEdit, QFrame,
    QSpinBox, QCheckBox, QColorDialog, QSizePolicy
)
from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView

from frontend.components.core.factories import create_page_header
from frontend.theme import LAYOUT, STYLES, THEME_DARK
from frontend.utils import get_icon, get_icon_colored
from backend.services.alerts_service import AlertsService

class AlertsPage(QWidget):
    def __init__(self, db_handler, alert_worker=None, parent=None):
        super().__init__(parent)
        self.service = AlertsService(db_handler, alert_worker) 
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(*LAYOUT["level_03"])
        main_layout.setSpacing(12)

        # =========================================================
        # COLUMNA IZQUIERDA: PREVISUALIZACIÓN
        # =========================================================
        left_panel = QWidget()
        left_panel.setMinimumWidth(460) 
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        left_layout.addWidget(create_page_header("Diseñador de Alertas", "Personaliza y previsualiza en tiempo real."))

        # Contenedor del Visor Web
        preview_container = QFrame()
        preview_container.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        preview_layout = QVBoxLayout(preview_container)
        
        # Visor Web (Carga el HTML de OBS)
        self.webview = QWebEngineView()
        self.webview.page().setBackgroundColor(QColor(0, 0, 0, 0)) 
        self.webview.setUrl(QUrl("http://127.0.0.1:8081/alerts"))
        
        preview_layout.addWidget(self.webview)
        
        # Hacemos que el contenedor del visor se expanda en ambas direcciones
        preview_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(preview_container, stretch=1)
        
        # Fila de botones debajo de la previsualización
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_copy_url = QPushButton("Copiar URL")
        self.btn_copy_url.setIcon(get_icon("copy.svg"))
        self.btn_copy_url.setStyleSheet(STYLES["btn_nav"])
        self.btn_copy_url.clicked.connect(self._handle_copy_url)
        
        self.btn_test = QPushButton("Reproducir Alerta")
        self.btn_test.setIcon(get_icon_colored("play-circle.svg", THEME_DARK['NeonGreen_Main']))
        self.btn_test.setStyleSheet(STYLES["btn_primary"])
        self.btn_test.clicked.connect(self._test_alert)
        self.btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_layout.addWidget(self.btn_copy_url)
        btn_layout.addWidget(self.btn_test)
        left_layout.addLayout(btn_layout)

        # =========================================================
        # COLUMNA DERECHA: PANEL DE EDICIÓN (SCROLL)
        # =========================================================
        right_panel = QWidget()
        right_panel.setFixedWidth(300) 
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content_widget = QWidget()
        self.form_layout = QVBoxLayout(content_widget)
        self.form_layout.setSpacing(5)

        # -- SECCIÓN 1: GENERAL --
        self.form_layout.addWidget(QLabel("<b>Ajustes Generales</b>", styleSheet="font-size: 14px;"))
        
        self.combo_alert = QComboBox()
        self.combo_alert.setStyleSheet(STYLES["combobox_modern"])
        self.combo_alert.addItems(["Nuevo Seguidor", "Suscripción", "Host / Raid"])
        self.combo_alert.currentTextChanged.connect(self._load_alert_data)
        self.form_layout.addLayout(self._create_input_group("Seleccionar Alerta a editar:", self.combo_alert))
        
        self.chk_active = QCheckBox("Activar esta alerta")
        self.chk_active.setChecked(True)
        self.form_layout.addWidget(self.chk_active)

        # -- SECCIÓN 2: TEXTOS --
        self.form_layout.addWidget(QLabel("<b>Textos</b>", styleSheet="font-size: 14px; margin-top: 10px;"))
        
        self.inp_title = QLineEdit("{user} te está siguiendo!")
        self.form_layout.addLayout(self._create_input_group("Título de la Alerta (Visual en pantalla):", self.inp_title))
        
        self.txt_msg = QTextEdit()
        self.txt_msg.setFixedHeight(100)
        self.form_layout.addLayout(self._create_input_group("Mensaje en el Chat del stream:", self.txt_msg))

        # -- SECCIÓN 3: MULTIMEDIA --
        self.form_layout.addWidget(QLabel("<b>Multimedia</b>", styleSheet="font-size: 14px; margin-top: 10px;"))
        
        self.inp_image = QLineEdit()
        self.inp_image.setPlaceholderText("https://ejemplo.com/gif.gif")
        self.form_layout.addLayout(self._create_input_group("URL de Imagen / GIF:", self.inp_image))

        self.inp_sound = QLineEdit()
        self.inp_sound.setPlaceholderText("https://ejemplo.com/sonido.mp3")
        self.form_layout.addLayout(self._create_input_group("URL del Sonido:", self.inp_sound))

        # -- SECCIÓN 4: APARIENCIA --
        self.form_layout.addWidget(QLabel("<b>Apariencia y Animación</b>", styleSheet="font-size: 14px; margin-top: 10px;"))

        row_layout = QHBoxLayout()

        self.current_color = "#53fc18"
        self.btn_color = QPushButton()
        self.btn_color.setFixedHeight(32)
        self.btn_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_color.clicked.connect(self._pick_color)
        self._update_color_btn()
        row_layout.addLayout(self._create_input_group("Color Principal:", self.btn_color))
        
        self.spin_duration = QSpinBox()
        self.spin_duration.setFixedHeight(32)
        self.spin_duration.setStyleSheet(f"{STYLES['spinbox_modern']};")
        self.spin_duration.setRange(1, 30)
        self.spin_duration.setValue(5)
        self.spin_duration.setSuffix(" seg")
        row_layout.addLayout(self._create_input_group("Duración:", self.spin_duration))
        self.form_layout.addLayout(row_layout)

        self.combo_layout = QComboBox()
        self.combo_layout.setStyleSheet(STYLES["combobox_modern"])
        self.combo_layout.addItems(["Imagen Arriba, Texto Abajo", "Imagen a la Izquierda", "Imagen a la Derecha"])
        self.form_layout.addLayout(self._create_input_group("Diseño (Layout):", self.combo_layout))

        self.combo_anim = QComboBox()
        self.combo_anim.setStyleSheet(STYLES["combobox_modern"])
        self.combo_anim.addItems(["Pop In (Rebote)", "Fade In (Desvanecer)", "Slide Up (Deslizar)"])
        self.form_layout.addLayout(self._create_input_group("Animación de Entrada:", self.combo_anim))

        self.form_layout.addStretch()

        # Botón Guardar
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.setIcon(get_icon_colored("save.svg", THEME_DARK['NeonGreen_Main']))
        self.btn_save.setStyleSheet(STYLES["btn_primary"])
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_alert_data)
        self.form_layout.addWidget(self.btn_save)

        scroll.setWidget(content_widget)
        right_layout.addWidget(scroll)

        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=0)

        self._load_alert_data()

    # FUNCIONES DE COLOR
    def _update_color_btn(self):
        self.btn_color.setStyleSheet(
            f"background-color: {self.current_color}; "
            f"border: 1px solid {THEME_DARK['Black_N1']}; "
            f"border-radius: 6px;"
        )

    def _pick_color(self):
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(self.current_color))
        if dialog.exec():
            self.current_color = dialog.selectedColor().name()
            self._update_color_btn()

    def _create_input_group(self, label_text, widget):
        layout = QVBoxLayout()
        layout.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; font-size: 11px;")
        
        base_style = f"background: {THEME_DARK['Black_N3']}; padding: 8px; border-radius: 6px; color: {THEME_DARK['White_N1']}; border: 1px solid {THEME_DARK['Black_N1']};"
        if isinstance(widget, (QLineEdit, QTextEdit)):
            widget.setStyleSheet(base_style)
            
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return layout

    def _handle_copy_url(self):
        QApplication.clipboard().setText("http://127.0.0.1:8081/alerts")
        self.btn_copy_url.setText(" ¡Copiado!")
        QTimer.singleShot(1500, lambda: self.btn_copy_url.setText(" Copiar URL"))

    def _test_alert(self):
        event_map = {"Nuevo Seguidor": "follow", "Suscripción": "subscription", "Host / Raid": "host"}
        selected_event = event_map[self.combo_alert.currentText()]
        
        mock_data = {
            "count": 120, "months": 6, "viewers": 450,
            "title_template": self.inp_title.text(),
            "color": self.current_color,
            "image_url": self.inp_image.text(),
            "sound_url": self.inp_sound.text(),
            "duration": self.spin_duration.value(),
            "layout_style": self.combo_layout.currentText(),
            "animation": self.combo_anim.currentText()
        }
        
        custom_message = self.txt_msg.toPlainText() or "¡Mensaje de prueba!"
        
        self.service.trigger_alert(selected_event, "UsuarioTest", mock_data, custom_template=custom_message)

    def _load_alert_data(self):
        event_map = {"Nuevo Seguidor": "follow", "Suscripción": "subscription", "Host / Raid": "host"}
        selected_event = event_map.get(self.combo_alert.currentText())
        if not selected_event: return

        config = self.service.get_alert_config(selected_event)
        
        self.chk_active.setChecked(bool(config.get("is_active", True)))
        self.inp_title.setText(config.get("title_template", ""))
        self.txt_msg.setPlainText(config.get("message_template", ""))
        self.inp_image.setText(config.get("image_url", ""))
        self.inp_sound.setText(config.get("sound_url", ""))
        self.spin_duration.setValue(int(config.get("duration", 5)))
        self.current_color = config.get("color", "#53fc18")
        self._update_color_btn()
        self.combo_layout.setCurrentText(config.get("layout_style", "Imagen Arriba, Texto Abajo"))
        self.combo_anim.setCurrentText(config.get("animation", "Pop In (Rebote)"))

    def _save_alert_data(self):
        event_map = {"Nuevo Seguidor": "follow", "Suscripción": "subscription", "Host / Raid": "host"}
        selected_event = event_map[self.combo_alert.currentText()]
        
        data = {
            "title_template": self.inp_title.text(),
            "message_template": self.txt_msg.toPlainText(),
            "is_active": self.chk_active.isChecked(),
            "image_url": self.inp_image.text(),
            "sound_url": self.inp_sound.text(),
            "color": self.current_color,
            "duration": self.spin_duration.value(),
            "layout_style": self.combo_layout.currentText(),
            "animation": self.combo_anim.currentText()
        }
        self.service.save_alert(selected_event, data)
        
        # --- NUEVO: Feedback visual ---
        texto_original = self.btn_save.text()
        self.btn_save.setText("¡Guardado!")
        
        # Volver al estado normal después de 1.5 segundos
        QTimer.singleShot(1500, lambda: [
            self.btn_save.setText(texto_original),
            self.btn_save.setStyleSheet(STYLES["btn_primary"])
        ])