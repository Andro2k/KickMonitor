# frontend/alerts/startup_alert.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from frontend.theme import STYLES
from frontend.utils import resource_path # Importamos resource_path para la ruta segura

class AlreadyRunningDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Aumentamos el alto a 240 para acomodar la imagen cómodamente
        self.setFixedSize(320, 240)

        # Layout principal transparente
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Contenedor principal (el fondo visible)
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 12px;
            }
        """)

        # Layout interno del contenedor
        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        inner_layout.setSpacing(10)

        # 0. Imagen (face_disapprove)
        self.lbl_image = QLabel()
        pixmap = QPixmap(resource_path("assets/faces/face_disapprove.png"))
        
        # Verificamos si la imagen existe, si es así la escalamos suavemente
        if not pixmap.isNull():
            pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_image.setPixmap(pixmap)
        else:
            # Fallback por si la imagen no se encuentra
            self.lbl_image.setText("🤨") 
            self.lbl_image.setStyleSheet("color: #fff; font-size: 48px; border: none;")
            
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Evitamos que herede el borde del QFrame padre
        self.lbl_image.setStyleSheet("border: none; background: transparent;") 

        # 1. Título
        lbl_title = QLabel("KickMonitor")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Mensaje
        lbl_msg = QLabel("La aplicación ya se está ejecutando en segundo plano.")
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #bbbbbb; font-size: 13px; border: none;")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Botón de Aceptar
        btn_ok = QPushButton("Entendido")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedHeight(32)
        btn_ok.setStyleSheet(STYLES["btn_primary"])
        btn_ok.clicked.connect(self.accept)

        # Añadimos los elementos al layout en orden descendente
        inner_layout.addWidget(self.lbl_image)
        inner_layout.addWidget(lbl_title)
        inner_layout.addWidget(lbl_msg)
        inner_layout.addStretch() # Empuja el botón hacia abajo
        inner_layout.addWidget(btn_ok)

        layout.addWidget(self.container)