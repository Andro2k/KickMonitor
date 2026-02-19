# frontend/dialogs/update_modal.py

import os
from PyQt6.QtWidgets import (QLabel, QPushButton, QHBoxLayout, 
                             QVBoxLayout, QTextBrowser, QProgressBar, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from frontend.theme import LAYOUT, STYLES, THEME_DARK
from frontend.components.base_modal import BaseModal

class UpdateModal(BaseModal):
    """
    Diálogo modal unificado para confirmar y visualizar la descarga de la actualización.
    """
    request_download = pyqtSignal()

    def __init__(self, new_version, changelog, parent=None):
        super().__init__(parent, width=750, height=480)
        
        self.new_version = new_version
        self.changelog = changelog
        self.is_downloading = False
        
        self.init_ui()

    def init_ui(self):
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(*LAYOUT["level_02"])
        main_h_layout.setSpacing(8)
        self.body_layout.addLayout(main_h_layout)

        # ==========================================
        # COLUMNA IZQUIERDA: INFORMACIÓN (Stretch=3)
        # ==========================================
        left_layout = QVBoxLayout()
        
        lbl_title = QLabel("¡Nueva Actualización!")
        lbl_title.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 26px; font-weight: bold; border: none;")
        left_layout.addWidget(lbl_title)

        lbl_ver = QLabel(f"Versión {self.new_version} disponible")
        lbl_ver.setStyleSheet("color: white; font-size: 15px; font-weight: bold; margin-bottom: 10px;")
        left_layout.addWidget(lbl_ver)

        txt_log = QTextBrowser()
        txt_log.setHtml(self.changelog)
        txt_log.setStyleSheet(STYLES["text_browser"])
        left_layout.addWidget(txt_log)
        
        main_h_layout.addLayout(left_layout, stretch=4)

        # ==========================================
        # COLUMNA DERECHA: IMAGEN Y CONTROLES (Stretch=2)
        # ==========================================
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Imagen (Escalada proporcionalmente)
        self.img_label = QLabel()
        img_path = os.path.join("assets", "install_bg.png") 
        
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaledToHeight(360, Qt.TransformationMode.SmoothTransformation)
            self.img_label.setPixmap(scaled_pixmap)
        else:
            self.img_label.setText("Imagen no encontrada")
            self.img_label.setStyleSheet("background: #222; color: #555; border-radius: 12px;")
            self.img_label.setMinimumSize(168, 320)
            
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.img_label)

        right_layout.addSpacing(15)

        # 2. Etiqueta de Estado (Oculta por defecto)
        self.lbl_status = QLabel("Descargando actualización...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #AAA;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.hide()
        right_layout.addWidget(self.lbl_status)

        # 3. Barra de Progreso (Oculta por defecto)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {THEME_DARK['border']};
                border-radius: 6px;
                text-align: center;
                background-color: {THEME_DARK['Black_N4']};
                color: white;
                font-weight: bold;
                height: 25px;
            }}
            QProgressBar::chunk {{
                background-color: {THEME_DARK['NeonGreen_Main']};
                border-radius: 5px;
            }}
        """)
        self.progress.hide()
        right_layout.addWidget(self.progress)

        # 4. Botones
        self.btns_widget = QWidget()
        self.btns_widget.setStyleSheet("background: transparent;")
        h_btns = QHBoxLayout(self.btns_widget)
        h_btns.setContentsMargins(0, 0, 0, 0)
        h_btns.setSpacing(5)

        self.btn_later = QPushButton("Más tarde")
        self.btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_later.setStyleSheet(STYLES["btn_outlined"])
        self.btn_later.clicked.connect(self.reject)

        self.btn_update = QPushButton("ACTUALIZAR")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(STYLES["btn_primary"])
        self.btn_update.clicked.connect(self._start_download_ui)

        h_btns.addWidget(self.btn_later)
        h_btns.addWidget(self.btn_update)
        right_layout.addWidget(self.btns_widget)

        main_h_layout.addLayout(right_layout, stretch=2)

    def _start_download_ui(self):
        """Oculta los botones y muestra la barra de progreso."""
        self.is_downloading = True
        
        self.btns_widget.hide()
        self.lbl_status.show()
        self.progress.show()
        
        self.request_download.emit()

    def update_progress(self, value):
        if value == -1:
            # Modo indeterminado (la barra rebotará de lado a lado)
            self.progress.setRange(0, 0)
            self.lbl_status.setText("Descargando... (Tamaño desconocido)")
        else:
            # Modo normal (0% a 100%)
            self.progress.setRange(0, 100)
            self.progress.setValue(value)
            self.lbl_status.setText(f"Descargando actualización... {value}%")

    def reject(self):
        if not self.is_downloading:
            super().reject()