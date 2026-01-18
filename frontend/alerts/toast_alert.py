# frontend/components/toast.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGraphicsOpacityEffect, QPushButton)
from PyQt6.QtCore import (Qt, QPropertyAnimation, pyqtProperty, 
                          QRectF, QPoint, QEvent, QEasingCurve)
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from frontend.theme import LAYOUT, STYLES
from frontend.utils import get_icon_colored

# ==========================================
# CONFIGURACIÓN LOCAL DEL TOAST
# ==========================================
TOAST_CONFIG = {
    "global": {
        "background": "#1E1E1E",   # Fondo de la tarjeta
        "text_title": "#FFFFFF",   # Color título
        "text_body":  "#9CA3AF",   # Color mensaje
        "border_radius": 8
    },
    "types": {
        "success": {
            "color": "#32D74B",    # Verde Kick
            "icon": "check.svg"    # Nombre del archivo en assets/icons
        },
        "error": {
            "color": "#FF453A",    # Rojo
            "icon": "error.svg" 
        },
        "warning": {
            "color": "#FFD60A",    # Amarillo
            "icon": "warning.svg"
        },
        "info": {
            "color": "#0A84FF",    # Azul
            "icon": "info.svg"
        }
    }
}

class ToastIcon(QWidget):
    """
    Dibuja un círculo de color y superpone un SVG blanco en el centro.
    """
    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        
        # 1. Obtener configuración
        config = TOAST_CONFIG["types"].get(tipo, TOAST_CONFIG["types"]["info"])
        self.bg_color = QColor(config["color"])
        icon_name = config["icon"]

        # 2. Generar el icono SVG en BLANCO para que contraste con el fondo de color
        icon_obj = get_icon_colored(icon_name, "#FFFFFF", size=18)
        self.icon_pixmap = icon_obj.pixmap(18, 18)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Dibujar Círculo de Fondo (Color del estado)
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        rect_circle = self.rect()
        painter.drawEllipse(rect_circle)
        
        # 2. Dibujar Icono SVG (Blanco) Centrado
        if not self.icon_pixmap.isNull():
            x = (self.width() - self.icon_pixmap.width()) // 2
            y = (self.height() - self.icon_pixmap.height()) // 2
            painter.drawPixmap(x, y, self.icon_pixmap)


class ToastNotification(QWidget):
    _active_toasts = []
    MAX_VISIBLE = 4 

    def __init__(self, parent, titulo, mensaje, tipo="info"):
        super().__init__(parent)
        self.parent_ref = parent
        self._progress = 0.0
        
        clean_type = tipo.replace("status_", "")
        if clean_type not in TOAST_CONFIG["types"]:
            clean_type = "info"
        self.tipo = clean_type
        
        self.titulo_text = titulo
        self.mensaje_text = mensaje
        
        self._setup_vars()
        self._configure_window()
        self._setup_ui()
        self._setup_animations()

        if self.parent_ref:
            self.parent_ref.installEventFilter(self)

    def _setup_vars(self):
        # Extraer colores de la configuración local
        glob = TOAST_CONFIG["global"]
        type_conf = TOAST_CONFIG["types"][self.tipo]
        
        self.bg_color = QColor(glob["background"])
        self.title_color = glob["text_title"]
        self.body_color = glob["text_body"]
        self.accent_color = QColor(type_conf["color"])
        self.radius = glob["border_radius"]

    def _configure_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(340)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(*LAYOUT["margins"])
        main_layout.setSpacing(LAYOUT["spacing"])

        # 1. ICONO VISUAL (SVG + Círculo)
        icon_widget = ToastIcon(self.tipo, self)
        main_layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignTop)

        # 2. TEXTOS
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        lbl_title = QLabel(self.titulo_text)
        lbl_title.setStyleSheet(f"color: {self.title_color}; font-weight: bold; font-size: 12px; background: transparent;")
        
        lbl_msg = QLabel(self.mensaje_text)
        lbl_msg.setStyleSheet(f"color: {self.body_color}; font-size: 11px; background: transparent;")
        lbl_msg.setWordWrap(True)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_msg)
        
        main_layout.addWidget(text_container, 1)

        # 3. BOTÓN CERRAR
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(STYLES["btn_icon_ghost"])
        btn_close.clicked.connect(self.close_toast)
        main_layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignTop)

    def _setup_animations(self):
        # Fade In/Out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_fade.setDuration(250)
        
        # Barra de progreso (Tiempo de vida)
        self.anim_bar = QPropertyAnimation(self, b"progress")
        self.anim_bar.setDuration(4000)
        self.anim_bar.setStartValue(0.0)
        self.anim_bar.setEndValue(1.0)
        self.anim_bar.finished.connect(self.close_toast)

        # Movimiento suave al reposicionar
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
        path.addRoundedRect(rect, self.radius, self.radius)
        
        # 1. Fondo de la tarjeta
        painter.fillPath(path, self.bg_color)
        
        # 2. Barra de progreso inferior (recortada al borde redondeado)
        if self._progress > 0:
            painter.setClipPath(path)
            bar_height = 3
            bar_width = self.width() * (1 - self._progress)
            rect_bar = QRectF(0, self.height() - bar_height, bar_width, bar_height)
            painter.fillRect(rect_bar, self.accent_color)

    def show_toast(self):
        # Gestionar cola de notificaciones
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