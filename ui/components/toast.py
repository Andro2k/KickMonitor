# ui/components/toast.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGraphicsOpacityEffect, QPushButton)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QRectF, QPoint, QEvent, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QFont, QPainterPath
from ui.theme import TOAST_THEME  # <--- Importamos tu tema

class ToastIcon(QWidget):
    """
    Widget para el icono circular.
    Obtiene el color del TOAST_THEME pero mantiene los símbolos definidos aquí.
    """
    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.tipo = tipo
        
        # Mapeo de símbolos (Lógica visual)
        self.symbols = {
            "status_success": "✓",
            "status_error":   "✕",
            "status_warning": "!",
            "status_info":    "i",
        }
        self.symbol = self.symbols.get(tipo, "i")

        # Recuperar color desde el TEMA
        # Si no encuentra el tipo, usa 'info' como fallback
        color_hex = TOAST_THEME["states"].get(tipo, TOAST_THEME["states"]["status_info"])
        self.bg_color = QColor(color_hex)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Círculo con el color del tema
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 24, 24)
        
        # 2. Símbolo
        painter.setPen(QColor("white"))
        font = QFont("Arial", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.symbol)


class ToastNotification(QWidget):
    _active_toasts = []
    MAX_VISIBLE = 4 

    def __init__(self, parent, titulo, mensaje, tipo="status_info"):
        super().__init__(parent)
        self.parent_ref = parent
        self._progress = 0.0
        self.tipo = tipo
        
        self.titulo_text = titulo
        self.mensaje_text = mensaje
        
        self._configure_window()
        self._setup_colors(tipo)
        self._setup_ui()
        self._setup_animations()

        if self.parent_ref:
            self.parent_ref.installEventFilter(self)

    def _configure_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(340)

    def _setup_colors(self, tipo):
        # 1. Fondo: Intentamos buscarlo en el tema, si no existe, usamos el gris oscuro de la imagen
        bg_hex = TOAST_THEME.get("background", "#1E1E1E") 
        self.bg_color = QColor(bg_hex)
        
        # 2. Color de Estado (Acento): Viene estrictamente de TOAST_THEME["states"]
        state_hex = TOAST_THEME["states"].get(tipo, TOAST_THEME["states"]["status_info"])
        self.accent_color = QColor(state_hex)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ICONO (Usando la clase que consulta el tema)
        icon_widget = ToastIcon(self.tipo, self)
        main_layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignTop)

        # TEXTOS
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        # Título
        lbl_title = QLabel(self.titulo_text)
        # Usamos color de texto del tema si existe, sino blanco
        title_color = TOAST_THEME.get("text_title", "#FFFFFF")
        lbl_title.setStyleSheet(f"color: {title_color}; font-weight: bold; font-size: 13px; background: transparent;")
        
        # Mensaje
        lbl_msg = QLabel(self.mensaje_text)
        # Usamos color de subtexto del tema si existe, sino gris
        msg_color = TOAST_THEME.get("text_body", "#9CA3AF")
        lbl_msg.setStyleSheet(f"color: {msg_color}; font-size: 12px; background: transparent;")
        lbl_msg.setWordWrap(True)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_msg)
        
        main_layout.addWidget(text_container, 1)

        # BOTÓN CERRAR
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {msg_color}; 
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {title_color};
            }}
        """)
        btn_close.clicked.connect(self.close_toast)
        main_layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignTop)

    def _setup_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_fade.setDuration(250)
        
        self.anim_bar = QPropertyAnimation(self, b"progress")
        self.anim_bar.setDuration(4000)
        self.anim_bar.setStartValue(0.0)
        self.anim_bar.setEndValue(1.0)
        self.anim_bar.finished.connect(self.close_toast)

        self.anim_pos = QPropertyAnimation(self, b"pos")
        self.anim_pos.setDuration(300)
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def progress(self): return self._progress

    @progress.setter
    def progress(self, value): 
        self._progress = value
        self.update()

    def eventFilter(self, source, event):
        if source == self.parent_ref and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            ToastNotification.reposition_all(animate=False)
        return super().eventFilter(source, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        
        # Fondo
        painter.fillPath(path, self.bg_color)
        
        # Barra de progreso
        if self._progress > 0:
            painter.setClipPath(path)
            bar_height = 3
            bar_width = self.width() * (1 - self._progress)
            rect_bar = QRectF(0, self.height() - bar_height, bar_width, bar_height)
            painter.fillRect(rect_bar, self.accent_color)

    def show_toast(self):
        if len(ToastNotification._active_toasts) >= self.MAX_VISIBLE:
            oldest = ToastNotification._active_toasts.pop(0)
            oldest.close_toast_immediate()
        
        ToastNotification._active_toasts.append(self)
        self.adjustSize() 
        self.show()
        self.raise_()
        ToastNotification.reposition_all(animate=True)
        
        self.anim_fade.setStartValue(0); self.anim_fade.setEndValue(1); self.anim_fade.start()
        self.anim_bar.start()

    def close_toast(self):
        if self.anim_fade.direction() == QPropertyAnimation.Direction.Backward: return
        self.anim_fade.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim_fade.finished.connect(self._cleanup)
        self.anim_fade.start()

    def close_toast_immediate(self):
        self._cleanup()

    def _cleanup(self):
        if self.parent_ref: self.parent_ref.removeEventFilter(self)
        if self in ToastNotification._active_toasts: 
            ToastNotification._active_toasts.remove(self)
        ToastNotification.reposition_all(animate=True)
        self.close()

    def move_to(self, target_pos: QPoint, animate=True):
        if animate:
            if self.anim_pos.state() == QPropertyAnimation.State.Running:
                self.anim_pos.stop()
            self.anim_pos.setEndValue(target_pos)
            self.anim_pos.start()
        else:
            self.move(target_pos)

    @staticmethod
    def reposition_all(animate=True):
        active = ToastNotification._active_toasts
        if not active: return

        parent = active[0].parent_ref
        if not parent: return

        parent_geo = parent.geometry()
        screen_pos = parent.mapToGlobal(QPoint(0,0))
        
        margin_bottom = 20
        margin_right = 20
        spacing = 10
        
        current_y = screen_pos.y() + parent_geo.height() - margin_bottom

        for toast in reversed(active):
            w = toast.width()
            h = toast.height()
            
            target_x = screen_pos.x() + parent_geo.width() - w - margin_right
            target_y = current_y - h
            
            toast.move_to(QPoint(target_x, target_y), animate)
            current_y = target_y - spacing