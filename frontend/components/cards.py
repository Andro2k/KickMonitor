# frontend/components/cards.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QSizePolicy
from frontend.theme import LAYOUT, STYLES

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