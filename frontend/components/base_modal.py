# frontend/components/base_modal.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from frontend.theme import THEME_DARK, LAYOUT

class BaseModal(QDialog):
    """
    Clase base para todos los diálogos modales.
    """
    def __init__(self, parent=None, width=400, height=450):
        super().__init__(parent)
        
        # 1. Configuración de Ventana
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(width, height)
        
        # 2. Setup UI Base
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Contenedor Visual (El "Cuerpo" del modal)
        self.body = QFrame()
        self.body.setObjectName("ModalBody")
        self.body.setStyleSheet(f"""
            QFrame#ModalBody {{
                background-color: {THEME_DARK['Black_N2']};
                border: 1px solid {THEME_DARK['Black_N4']}; 
                border-radius: 16px;
            }}
        """)
        
        # Layout interno donde las clases hijas pondrán sus widgets
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(*LAYOUT["level_03"])
        self.body_layout.setSpacing(LAYOUT["space_01"])
        
        self.main_layout.addWidget(self.body)
        
        # 3. Iniciar Animación de Entrada
        self._animate_entry()

    def _animate_entry(self):
        """Animación suave de opacidad al abrir."""
        self.opacity_effect = QGraphicsOpacityEffect(self.body)
        self.body.setGraphicsEffect(self.opacity_effect)
        
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(250)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_in.start()

    def close_with_animation(self, result_code):
        """
        Llamar a este método en lugar de accept() o reject() 
        si quieres animación de salida.
        """
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(lambda: self.done(result_code))
        self.anim_out.start()

    # Métodos rápidos para cerrar con animación
    def accept(self):
        self.close_with_animation(QDialog.DialogCode.Accepted)

    def reject(self):
        self.close_with_animation(QDialog.DialogCode.Rejected)