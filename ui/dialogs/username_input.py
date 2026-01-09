# ui/dialogs/username_input.py

from PyQt6.QtWidgets import (QDialog, QFrame, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton)
from PyQt6.QtCore import Qt
from ui.utils import get_icon
from ui.theme import THEME_DARK, LAYOUT

class UsernameInputDialog(QDialog):
    """
    Diálogo modal independiente para solicitar el nombre de usuario.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Usuario Requerido")
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Contenedor principal
        container = QFrame(self)
        container.setGeometry(0, 0, 360, 420)
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

        # 1. Imagen SVG
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("border: none; background: transparent;")
        pixmap = get_icon("kick.svg").pixmap(180, 180)
        lbl_img.setPixmap(pixmap)
        layout.addWidget(lbl_img)

        # 2. Texto Explicativo
        lbl_msg = QLabel("No pudimos detectar tu usuario.\nPor favor ingrésalo manualmente:")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-size: 14px; border: none; font-weight: 500;")
        layout.addWidget(lbl_msg)

        # 3. Campo de Texto
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ej: TuUsuarioKick")
        self.txt_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_user.setFixedHeight(45)
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

        # 4. Botón Guardar
        btn_save = QPushButton("Guardar y Conectar")
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
        layout.addWidget(btn_save)

    def _on_save(self):
        text = self.txt_user.text().strip()
        if text:
            self.username = text
            self.accept()
        else:
            # Feedback visual de error (borde rojo temporal)
            self.txt_user.setStyleSheet(self.txt_user.styleSheet().replace("#444", "#ff453a"))