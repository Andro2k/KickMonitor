# ui/components/strict_flow_layout.py

from PyQt6.QtWidgets import QLayout
from PyQt6.QtCore import Qt, QRect, QSize, QPoint

class StrictFlowLayout(QLayout):
    """
    Layout de flujo estricto (estilo Grid/Galería).
    - NO estira los elementos (mantiene su tamaño fijo).
    - Alinea todo a la izquierda y arriba.
    - Ideal para galerías de imágenes o tarjetas de medios.
    """
    def __init__(self, parent=None, margin=0, spacing=0):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        width = rect.width()

        # --- FASE 1: PROCESAMIENTO ---
        for item in self.itemList:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            
            # Si el elemento se sale del ancho, bajamos a nueva línea
            if (x + w > rect.x() + width) and (line_height > 0):
                x = rect.x() 
                y += line_height + spacing
                line_height = 0 
            
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, h)))
            
            x += w + spacing
            line_height = max(line_height, h)
            
        return y + line_height - rect.y()