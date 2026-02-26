# frontend/components/core/cards.py

from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from frontend.theme import LAYOUT, THEME_DARK, STYLES

# =========================================================================
# TARJETA BÁSICA
# =========================================================================
class Card(QFrame):
    """
    Contenedor básico optimizado con estilo de tarjeta.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Política de Tamaño
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # 2. Estilo Visual
        self.setStyleSheet(STYLES["card"])
        
        # 3. Layout Interno
        self.layout = QVBoxLayout(self) 
        self.layout.setContentsMargins(*LAYOUT["level_03"])
        self.layout.setSpacing(LAYOUT["space_01"])

# =========================================================================
# TARJETA ACORDEÓN (Clase Base Visual)
# =========================================================================
class BaseAccordionCard(QFrame):
    """
    Clase padre con animación fluida y corrección de estilos.
    Solo maneja la UI y el comportamiento de expandir/colapsar.
    """
    def __init__(self, title, subtitle, is_active):
        super().__init__()
        self.setObjectName("AccordionCard")
        
        # --- CONFIG RESPONSIVA ---
        self.setMinimumWidth(320)  # Ancho mínimo antes de bajar de línea
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # -------------------------
        
        self.is_expanded = False
        self.is_active = is_active
        
        self.setStyleSheet(f"""
            QFrame#AccordionCard {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['Black_N1']};
            }}
            QFrame#AccordionCard:hover {{
                border: 1px solid {THEME_DARK['Black_N4']};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)
        
        # 1. CABECERA (Siempre visible)
        self.header = QFrame()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.mousePressEvent = self.toggle_expand
        
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(*LAYOUT["level_03"])
        
        # Icono Estado
        self.status_indicator = QLabel("●")
        self._update_status_color()
        
        # Textos
        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; font-size: 12px;")
        
        text_container.addWidget(self.lbl_title)
        text_container.addWidget(self.lbl_subtitle)
        
        h_layout.addWidget(self.status_indicator)
        h_layout.addLayout(text_container)
        h_layout.addStretch()
        
        self.main_layout.addWidget(self.header)
        
        # 2. CONTENIDO (Oculto por defecto)
        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0) # Inicia colapsado
        self.content_area.setClipsChildren = lambda x: None
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 0, 15, 15)
        self.content_layout.setSpacing(10)
        
        self.main_layout.addWidget(self.content_area)

        # Animación
        self.anim = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)

    def _update_status_color(self):
        color = THEME_DARK['NeonGreen_Main'] if self.is_active else THEME_DARK['Gray_N2']
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 12px;")

    def toggle_expand(self, event):
        if self.is_expanded:
            self.anim.setStartValue(self.content_area.height())
            self.anim.setEndValue(0)
        else:
            # Calcular altura necesaria
            target_h = self.content_layout.sizeHint().height() + 20
            self.anim.setStartValue(0)
            self.anim.setEndValue(target_h)
            
        self.anim.start()
        self.is_expanded = not self.is_expanded

    def add_content_widget(self, widget):
        self.content_layout.addWidget(widget)