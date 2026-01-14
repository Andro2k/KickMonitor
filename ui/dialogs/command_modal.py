# ui/dialogs/command_modal.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSpinBox, 
    QPlainTextEdit
)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, THEME_DARK, STYLES

class ModalEditCommand(QDialog):
    def __init__(self, parent=None, trigger="", response="", cooldown=5):
        super().__init__(parent)
        self.trigger_result = trigger
        self.response_result = response
        self.cooldown_result = cooldown
        
        # Configuración de Ventana (Frameless / Sin bordes)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 480)
        
        self._setup_ui(trigger, response, cooldown)

    def _setup_ui(self, trigger, response, cooldown):
        # Contenedor Principal con Borde y Fondo
        container = QFrame(self)
        container.setGeometry(0, 0, 500, 480)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border: 1px solid {THEME_DARK['Black_N4']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])
        
        # 1. Título
        lbl_title = QLabel("Editar Comando" if trigger else "Nuevo Comando")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; border: none;")
        layout.addWidget(lbl_title)
        
        # 2. Trigger (Input)
        layout.addWidget(QLabel("Comando (Ej: !redes):", styleSheet="color: #AAA; border: none;"))
        self.txt_trigger = QLineEdit(trigger)
        self.txt_trigger.setPlaceholderText("!comando")
        self.txt_trigger.setStyleSheet(self._input_style())
        if trigger:
            self.txt_trigger.setReadOnly(True) # No permitir cambiar el trigger si ya existe (clave primaria)
            self.txt_trigger.setStyleSheet(self._input_style(readonly=True))
        layout.addWidget(self.txt_trigger)
        
        # 3. Respuesta (TextArea)
        layout.addWidget(QLabel("Respuesta del Bot:", styleSheet="color: #AAA; border: none;"))
        self.txt_response = QPlainTextEdit(response)
        self.txt_response.setPlaceholderText("Escribe aquí lo que dirá el bot...")
        self.txt_response.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {THEME_DARK['Black_N3']};
                color: white;
                border: 1px solid {THEME_DARK['Gray_Border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QPlainTextEdit:focus {{ border: 1px solid {THEME_DARK['Black_N4']}; }}
        """)
        layout.addWidget(self.txt_response)
        
        # Variables de ayuda
        lbl_vars = QLabel("Variables: {user}, {random}, {points}, {touser}, {coin}, {dice}", 
                          styleSheet=f"color: {THEME_DARK['Gray_N2']}; font-size: 11px; border: none;")
        layout.addWidget(lbl_vars)

        # 4. Cooldown (SpinBox)
        row_cd = QHBoxLayout()
        row_cd.addWidget(QLabel("Cooldown (segundos):", styleSheet="color: #AAA; border: none;"))
        
        self.spin_cd = QSpinBox()
        self.spin_cd.setRange(0, 3600)
        self.spin_cd.setValue(cooldown)
        self.spin_cd.setStyleSheet(STYLES["spinbox_modern"])
        row_cd.addWidget(self.spin_cd)
        row_cd.addStretch()
        layout.addLayout(row_cd)
        
        layout.addStretch()
        
        # 5. Botones (Cancelar / Guardar)
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_save.setStyleSheet(STYLES["btn_solid_primary"])
        
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        layout.addLayout(h_btns)

    def _input_style(self, readonly=False):
        bg = THEME_DARK['Black_N4'] if readonly else THEME_DARK['Black_N3']
        color = THEME_DARK['Gray_N1'] if readonly else "white"
        return f"""
            QLineEdit {{
                background-color: {bg};
                color: {color};
                border: 1px solid {THEME_DARK['Gray_Border']};
                border-radius: 8px;
                padding: 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME_DARK['Black_N4']}; }}
        """

    def _save(self):
        # Guardar valores en las variables de instancia para que el padre las lea
        self.trigger_result = self.txt_trigger.text().strip()
        self.response_result = self.txt_response.toPlainText().strip()
        self.cooldown_result = self.spin_cd.value()
        
        if self.trigger_result and self.response_result:
            self.accept()