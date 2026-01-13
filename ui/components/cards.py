# ui/components/cards.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QSizePolicy
from ui.theme import LAYOUT, STYLES

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
        self.layout.setContentsMargins(*LAYOUT["margins"])
        self.layout.setSpacing(LAYOUT["spacing"])