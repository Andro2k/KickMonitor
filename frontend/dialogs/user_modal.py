# frontend/dialogs/user_modal.py

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton)
from PyQt6.QtCore import Qt
from frontend.utils import get_icon
from frontend.theme import STYLES, THEME_DARK, LAYOUT
from frontend.components.base_modal import BaseModal

class UsernameInputDialog(BaseModal):
    def __init__(self, parent=None):
        # Inicializamos BaseModal con el tamaño específico para este diálogo
        super().__init__(parent, width=360, height=430)
        self.username = None
        self._setup_ui()

    def _setup_ui(self):
        # Usamos el layout del cuerpo provisto por BaseModal
        layout = self.body_layout

        # 1. Imagen
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("border: none; background: transparent;")
        pixmap = get_icon("kick.svg").pixmap(90, 90)
        lbl_img.setPixmap(pixmap)
        layout.addWidget(lbl_img)

        # 2. Texto Título
        lbl_msg = QLabel("Configuración Inicial")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 18px; font-weight: bold; border:none;")
        layout.addWidget(lbl_msg)

        # 3. Texto Descripción
        lbl_desc = QLabel("Ingresa el nombre de tu canal tal cual aparece en la URL de Kick.\n(Ej: kick.com/rebeca-arenas)")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-size: 12px; border: none;")
        layout.addWidget(lbl_desc)

        layout.addSpacing(LAYOUT["spacing"])

        # 4. Input
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Nombre del canal (Ej: rebeca arenas)")
        self.txt_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_user.setFixedHeight(40)
        self.txt_user.returnPressed.connect(self._on_save)
        self.txt_user.setStyleSheet(STYLES["input_cmd"])
        layout.addWidget(self.txt_user)

        layout.addSpacing(LAYOUT["spacing"])

        # 5. BOTONES (Layout Horizontal)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(LAYOUT["spacing"])

        # Botón CANCELAR
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        # BaseModal se encarga de la animación al rechazar
        btn_cancel.clicked.connect(self.reject) 

        # Botón GUARDAR
        btn_save = QPushButton("Confirmar")
        btn_save.setDefault(True)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_save(self):
        text = self.txt_user.text().strip()
        if text:
            formatted_slug = text.lower().replace(" ", "-")
            self.username = formatted_slug
            self.accept()
        else:
            self.txt_user.setStyleSheet(self.txt_user.styleSheet().replace("#444", "#ff453a"))