# ui/dialogs/update_modal.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QFrame, QTextBrowser)
from PyQt6.QtCore import Qt
from ui.theme import THEME_DARK

class UpdateModal(QDialog):
    """
    Diálogo modal para confirmar actualización.
    Muestra la versión detectada y el changelog.
    """
    def __init__(self, new_version, changelog, parent=None):
        super().__init__(parent)
        self.new_version = new_version
        self.changelog = changelog
        
        # Configuración de ventana (sin bordes nativos)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 450)
        
        self.init_ui()

    def init_ui(self):
        # Contenedor principal con estilo
        container = QFrame(self)
        container.setGeometry(10, 10, 380, 430)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border: 1px solid {THEME_DARK['Black_N4']}; 
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(25, 30, 25, 30)
        layout.setSpacing(15)

        # 1. Título e Icono (Texto simple por ahora)
        lbl_title = QLabel("¡Nueva Actualización!")
        lbl_title.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 22px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # 2. Información de versión
        lbl_ver = QLabel(f"Versión {self.new_version} disponible")
        lbl_ver.setStyleSheet("color: #FFF; font-size: 14px; font-weight: bold; border: none;")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)

        # 3. Changelog (Área de texto scrolleable)
        lbl_changes = QLabel("Novedades:")
        lbl_changes.setStyleSheet("color: #AAA; font-size: 12px; border: none; margin-top: 10px;")
        layout.addWidget(lbl_changes)

        txt_log = QTextBrowser()
        txt_log.setHtml(self.changelog) # Permite HTML simple en el JSON
        txt_log.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {THEME_DARK['Black_N4']};
                color: #DDD;
                border: 1px solid {THEME_DARK['Gray_Border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }}
        """)
        layout.addWidget(txt_log)

        # 4. Botones
        h_btns = QHBoxLayout()
        h_btns.setSpacing(15)

        btn_later = QPushButton("Más tarde")
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                color: {THEME_DARK['Gray_N1']};
                border: 1px solid {THEME_DARK['Gray_Border']};
                border-radius: 8px; padding: 10px; font-weight: bold;
            }}
            QPushButton:hover {{ border-color: #FFF; color: #FFF; }}
        """)
        btn_later.clicked.connect(self.reject)

        btn_update = QPushButton("ACTUALIZAR")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['NeonGreen_Main']}; 
                color: {THEME_DARK['Black_N1']};
                border: none; border-radius: 8px; padding: 10px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Light']}; }}
        """)
        btn_update.clicked.connect(self.accept)

        h_btns.addWidget(btn_later)
        h_btns.addWidget(btn_update)
        layout.addLayout(h_btns)