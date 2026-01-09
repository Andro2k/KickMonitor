# ui/utils.py

import sys
import os
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

def resource_path(relative_path):
    """Obtiene ruta absoluta para recursos en modo DEV y EXE"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_icon(name):
    full_path = resource_path(os.path.join("assets", "icons", name))
    return QIcon(full_path)

# --- NUEVA FUNCIÓN ---
def get_colored_icon(name, color_str, size=24):
    """
    Carga un SVG y lo pinta de un color específico.
    """
    full_path = resource_path(os.path.join("assets", "icons", name))
    
    # 1. Cargar el SVG en un Pixmap
    pixmap = QPixmap(full_path)
    if not pixmap.isNull() and size:
        pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    # 2. Crear un lienzo transparente del mismo tamaño
    colored_pixmap = QPixmap(pixmap.size())
    colored_pixmap.fill(Qt.GlobalColor.transparent)  
    # 3. Pintar usando composición (Masking)
    painter = QPainter(colored_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)  
    # A. Dibujar la máscara (el icono negro original)
    painter.drawPixmap(0, 0, pixmap)  
    # B. Configurar modo para "pintar solo donde hay pixeles" (SourceIn)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    # C. Llenar con el color deseado
    painter.fillRect(colored_pixmap.rect(), QColor(color_str))
    painter.end()
    
    return QIcon(colored_pixmap)