# ui/dialogs/user_modal.py

from PyQt6.QtWidgets import (QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton)
from PyQt6.QtCore import Qt
from ui.utils import get_icon
from ui.theme import THEME_DARK, LAYOUT

class UsernameInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Configurar Canal")
        self.setFixedSize(360, 430)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Contenedor principal
        container = QFrame(self)
        container.setGeometry(0, 0, 360, 430)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border: 1px solid {THEME_DARK['NeonGreen_Main']}; 
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(LAYOUT["spacing"])
        layout.setContentsMargins(*LAYOUT["margins"])

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
        self.txt_user.setStyleSheet(f"""
            QLineEdit {{
                background-color: {THEME_DARK['Black_N4']};
                color: white;
                border: 1px solid #444;
                border-radius: 8px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME_DARK['NeonGreen_Main']}; }}
        """)
        layout.addWidget(self.txt_user)

        layout.addSpacing(LAYOUT["spacing"])

        # 5. BOTONES (Layout Horizontal)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(LAYOUT["spacing"])

        # Botón CANCELAR (Estilo Outline / Fantasma)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME_DARK['White_N1']};
                border: 1px solid {THEME_DARK['Gray_N2']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {THEME_DARK['Black_N4']};
                border: 1px solid {THEME_DARK['White_N1']};
            }}
        """)
        btn_cancel.clicked.connect(self.reject) # Cierra el diálogo retornando "Rejected"

        # Botón GUARDAR (Estilo Sólido / Primario)
        btn_save = QPushButton("Confirmar")
        btn_save.setDefault(True)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['NeonGreen_Main']};
                color: black;
                font-weight: bold;
                font-size: 13px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Light']}; }}
        """)
        btn_save.clicked.connect(self._on_save)

        # Añadir botones al layout horizontal
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        # Añadir layout de botones al layout principal
        layout.addLayout(btn_layout)

    def _on_save(self):
        text = self.txt_user.text().strip()
        if text:
            # Formateo automático: minúsculas y espacios por guiones
            formatted_slug = text.lower().replace(" ", "-")
            self.username = formatted_slug
            self.accept()
        else:
            # Feedback de error visual
            self.txt_user.setStyleSheet(self.txt_user.styleSheet().replace("#444", "#ff453a"))