# ui/dialogs/command_modal.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSpinBox, 
    QPlainTextEdit
)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.components.base_modal import BaseModal

class ModalEditCommand(BaseModal):
    def __init__(self, parent=None, trigger="", response="", cooldown=5):
        super().__init__(parent, width=500, height=480)
        
        self.original_trigger = trigger
        self.trigger_result = trigger
        self.response_result = response
        self.cooldown_result = cooldown
        
        self._setup_ui(trigger, response, cooldown)

    def _setup_ui(self, trigger, response, cooldown):
        layout = self.body_layout
        
        # Título
        lbl_title = QLabel("Editar Comando" if trigger else "Nuevo Comando")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; border: none;")
        layout.addWidget(lbl_title)
        
        # Trigger (Input)
        layout.addWidget(QLabel("Comando (Ej: !redes):", styleSheet="color: #AAA; border: none;"))
        self.txt_trigger = QLineEdit(trigger)
        self.txt_trigger.setPlaceholderText("!comando")
        self.txt_trigger.setStyleSheet(STYLES["input"])
        
        layout.addWidget(self.txt_trigger)
        
        # Respuesta (TextArea)
        layout.addWidget(QLabel("Respuesta del Bot:", styleSheet="color: #AAA; border: none;"))
        self.txt_response = QPlainTextEdit(response)
        self.txt_response.setPlaceholderText("Escribe aquí lo que dirá el bot.")
        self.txt_response.setStyleSheet(STYLES["textarea"])
        
        layout.addWidget(self.txt_response)
        
        # Variables de ayuda
        lbl_vars = QLabel("Variables: {user}, {random}, {points}, {touser}, {coin}, {dice}", 
                          styleSheet=f"color: {THEME_DARK['Gray_N2']}; font-size: 11px; border: none;")
        layout.addWidget(lbl_vars)

        # Cooldown (SpinBox)
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
        
        # Botones
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        layout.addLayout(h_btns)

    def _save(self):
        self.trigger_result = self.txt_trigger.text().strip()
        self.response_result = self.txt_response.toPlainText().strip()
        self.cooldown_result = self.spin_cd.value()
        
        if self.trigger_result and self.response_result:
            self.accept()