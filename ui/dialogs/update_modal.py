# ui/dialogs/update_modal.py

from PyQt6.QtWidgets import (QLabel, QPushButton, 
                             QHBoxLayout, QTextBrowser)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, STYLES, THEME_DARK
from ui.components.base_modal import BaseModal

class UpdateModal(BaseModal):
    """
    Diálogo modal para confirmar actualización.
    """
    def __init__(self, new_version, changelog, parent=None):
        # 1. Configurar BaseModal (Tamaño 400x450)
        super().__init__(parent, width=500, height=450)
        
        self.new_version = new_version
        self.changelog = changelog
        
        self.init_ui()

    def init_ui(self):
        # 2. Usar el layout del cuerpo provisto por BaseModal
        layout = self.body_layout
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        # 1. Título e Icono (Texto simple por ahora)
        lbl_title = QLabel("¡Nueva Actualización!")
        lbl_title.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 22px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # 2. Información de versión
        lbl_ver = QLabel(f"Versión {self.new_version} disponible")
        lbl_ver.setObjectName("h4")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)

        # 3. Changelog (Área de texto scrolleable)
        lbl_changes = QLabel("Novedades:")
        lbl_changes.setStyleSheet("color: #AAA; font-size: 12px; border: none; margin-top: 10px;")
        layout.addWidget(lbl_changes)

        txt_log = QTextBrowser()
        txt_log.setHtml(self.changelog)
        txt_log.setStyleSheet(STYLES["text_browser"])
        layout.addWidget(txt_log)

        # 4. Botones
        h_btns = QHBoxLayout()
        h_btns.setSpacing(LAYOUT["spacing"])

        btn_later = QPushButton("Más tarde")
        btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_later.setStyleSheet(STYLES["btn_outlined"])
        btn_later.clicked.connect(self.reject)

        btn_update = QPushButton("ACTUALIZAR")
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.setStyleSheet(STYLES["btn_primary"])
        btn_update.clicked.connect(self.accept)

        h_btns.addWidget(btn_later)
        h_btns.addWidget(btn_update)
        layout.addLayout(h_btns)