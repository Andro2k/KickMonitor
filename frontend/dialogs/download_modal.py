# frontend/dialogs/download_modal.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from frontend.theme import THEME_DARK

class DownloadModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Actualizador de KickMonitor")
        self.setFixedSize(350, 120)
        
        # TRUCO: Quitamos el botón de "Cerrar (X)" para que el usuario no interrumpa la descarga
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; color: {THEME_DARK['White_N1']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.lbl_status = QLabel("Descargando actualización, por favor espera...")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold;")
        
        # Barra de progreso estilizada
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
            }}
            QProgressBar::chunk {{
                background-color: {THEME_DARK['NeonGreen_Main']};
                border-radius: 5px;
            }}
        """)
        
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress)
        
    def update_progress(self, value):
        self.progress.setValue(value)