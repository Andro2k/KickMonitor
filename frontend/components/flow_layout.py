# frontend/components/flow_layout.py

from PyQt6.QtWidgets import QLayout
from PyQt6.QtCore import Qt, QRect, QSize, QPoint

class FlowLayout(QLayout):
    """
    Layout personalizado tipo CSS Flexbox.
    """
    def __init__(self, parent=None, margin=0, spacing=-1):
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
        
        # Añadir márgenes
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        width = rect.width()

        # 1. Agrupar items en filas
        rows = []
        current_row = []
        current_row_width = 0
        
        for item in self.itemList:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            
            space = spacing if current_row else 0
            
            # Si el elemento no cabe, cambiamos de fila
            if current_row and (current_row_width + space + w > width):
                rows.append((current_row, current_row_width, line_height))
                current_row = []
                current_row_width = 0
                line_height = 0
                space = 0 

            current_row.append(item)
            current_row_width += space + w
            line_height = max(line_height, h)
            
        # Añadir la última fila
        if current_row:
            rows.append((current_row, current_row_width, line_height))

        # 2. Posicionar items (Estirando para llenar huecos)
        y = rect.y()
        
        for row_items, used_width, row_height in rows:
            x = rect.x()
            count = len(row_items)
            
            available_space = width - used_width
            extra_per_item = int(available_space / count) if count > 0 else 0
            
            for i, item in enumerate(row_items):
                w = item.sizeHint().width() + extra_per_item
                
                if i == count - 1:
                    remaining_width = (rect.x() + width) - x
                    w = remaining_width
                
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), QSize(w, row_height)))
                
                x += w + spacing
                
            y += row_height + spacing

        return y - rect.y()