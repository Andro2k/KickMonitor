# ui/utils.py

import sys
import os
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt

def resource_path(relative_path):
    """ Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def get_icon(name):
    full_path = resource_path(os.path.join("assets", "icons", name))
    return QIcon(full_path)

def get_colored_icon(name, color_str, size=24):
    """
    Carga un SVG, lo pinta de color y maneja errores si el archivo no existe.
    """
    full_path = resource_path(os.path.join("assets", "icons", name))
    
    pixmap = QPixmap(full_path)
    if pixmap.isNull():
        return QIcon()

    if size:
        pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    colored_pixmap = QPixmap(pixmap.size())
    colored_pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(colored_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(colored_pixmap.rect(), QColor(color_str))
    painter.end()
    
    return QIcon(colored_pixmap)

def get_rounded_pixmap(pixmap: QPixmap, radius: int = 0, is_circle: bool = False) -> QPixmap:
    """
    Recorta un QPixmap en forma de círculo o rectángulo redondeado.
    """
    if pixmap.isNull(): 
        return pixmap
        
    size = pixmap.size()
    result = QPixmap(size)
    result.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    path = QPainterPath()
    if is_circle:
        # Asumimos que la imagen ya viene cuadrada o queremos un círculo centrado
        s = min(size.width(), size.height())
        path.addEllipse(0, 0, s, s)
    else:
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
        
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    
    return result

def crop_to_square(pixmap: QPixmap, size: int) -> QPixmap:
    """Escala y recorta la imagen al centro para que sea un cuadrado perfecto."""
    return pixmap.scaled(
        size, size, 
        Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
        Qt.TransformationMode.SmoothTransformation
    )