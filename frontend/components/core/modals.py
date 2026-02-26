# frontend/components/core/modals.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFrame, QGraphicsOpacityEffect, 
    QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from frontend.theme import THEME_DARK, LAYOUT
from frontend.utils import get_icon

class BaseModal(QDialog):
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
                background-color: {THEME_DARK['Black_N1']};
                border: 1px solid {THEME_DARK['Gray_N1']};
                border-radius: 12px;
            }}
        """)
        
        # Layout interno donde las clases hijas pondrán sus widgets
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(*LAYOUT["level_03"])
        self.body_layout.setSpacing(LAYOUT["space_01"])
        
        # --- NUEVO: BOTÓN DE CERRAR GLOBAL CON SVG (X) ---
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.addStretch() # Empuja el botón hacia la derecha
        
        btn_close_global = QPushButton()
        btn_close_global.setIcon(get_icon("x.svg"))
        btn_close_global.setIconSize(QSize(14, 14)) # Tamaño interno del SVG
        btn_close_global.setFixedSize(26, 26)       # Tamaño del área clickeable
        btn_close_global.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_global.clicked.connect(self.reject) # Llama a la animación de cierre
        
        btn_close_global.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                border: none; 
                border-radius: 13px; 
            }
            QPushButton:hover { 
                background: #ff4c4c; 
            }
        """)
        
        top_bar_layout.addWidget(btn_close_global)

        self.body_layout.insertLayout(0, top_bar_layout)

        self.main_layout.addWidget(self.body)
        
        self._animate_entry()

        self._is_dragging = False
        self._drag_start_position = None

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

    # =========================================================================
    # LÓGICA PARA ARRASTRAR LA VENTANA (DRAG & DROP)
    # =========================================================================
    def mousePressEvent(self, event):
        """Detecta cuando el usuario hace clic izquierdo sobre el modal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            # Guardamos la posición exacta donde hizo clic respecto a la ventana
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Mueve la ventana si el usuario mantiene presionado el clic izquierdo."""
        if self._is_dragging:
            # Calculamos la nueva posición y movemos la ventana
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Detecta cuando el usuario suelta el clic."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()