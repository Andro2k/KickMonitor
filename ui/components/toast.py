# ui/components/toast.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QRectF, QPoint, QEvent, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPen
from ui.theme import LAYOUT, TOAST_THEME

class ToastNotification(QWidget):
    _active_toasts = []
    MAX_VISIBLE = 4 

    def __init__(self, parent, titulo, mensaje, tipo="info"):
        super().__init__(parent)
        self.parent_ref = parent
        self._progress = 0.0
        
        # Guardamos datos para recalcular tamaño después
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
        
        # Ancho fijo, altura libre
        self.setFixedWidth(300)

    def _setup_colors(self, tipo):
        state_color = TOAST_THEME["states"].get(tipo, TOAST_THEME["states"]["info"])
        self.bg_color = QColor(35, 35, 36)
        self.accent_color = QColor(state_color)
        self.border_color = QColor(60, 60, 60)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 15) 
        layout.setSpacing(4)
        
        lbl_title = QLabel(self.titulo_text)
        lbl_title.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent;")
        
        lbl_msg = QLabel(self.mensaje_text)
        lbl_msg.setStyleSheet("color: #CCC; font-size: 11px; background: transparent;")
        lbl_msg.setWordWrap(True) # ¡Vital para que crezca verticalmente!
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_msg)

    def _setup_animations(self):
        # 1. Animación de Opacidad (Fade In/Out)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_fade.setDuration(300)
        
        # 2. Animación de Barra de Progreso
        self.anim_bar = QPropertyAnimation(self, b"progress")
        self.anim_bar.setDuration(3500)
        self.anim_bar.setStartValue(0.0)
        self.anim_bar.setEndValue(1.0)
        self.anim_bar.finished.connect(self.close_toast)

        # 3. Animación de Movimiento (Posición fluida)
        self.anim_pos = QPropertyAnimation(self, b"pos")
        self.anim_pos.setDuration(300)
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic) # Movimiento suave al frenar

    @pyqtProperty(float)
    def progress(self): return self._progress

    @progress.setter
    def progress(self, value): 
        self._progress = value
        self.update()

    def eventFilter(self, source, event):
        if source == self.parent_ref and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            # Si se mueve la ventana principal, recolocamos todos instantáneamente (sin animación lenta)
            ToastNotification.reposition_all(animate=False)
        return super().eventFilter(source, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect())
        draw_rect = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        
        # Fondo y Borde
        painter.setBrush(self.bg_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(draw_rect, 10, 10)
        
        # Barra de Progreso (Siempre abajo del todo)
        if self._progress > 0:
            bar_width = (self.width() - 30) * (1 - self._progress)
            if bar_width > 0:
                rect_bar = QRectF(15, self.height() - 6, bar_width, 3)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self.accent_color)
                painter.drawRoundedRect(rect_bar, 1.5, 1.5)

    def show_toast(self):
        # 1. Limpieza de cola si hay demasiados
        if len(ToastNotification._active_toasts) >= self.MAX_VISIBLE:
            # Eliminamos el más viejo (índice 0)
            oldest = ToastNotification._active_toasts.pop(0)
            oldest.close_toast_immediate()
        
        # 2. Agregar a la lista
        ToastNotification._active_toasts.append(self)
        
        # 3. Calcular tamaño real basado en el texto
        self.adjustSize() 
        
        # 4. Posicionar inicialmente (fuera de pantalla o en su sitio)
        # Lo calcularemos en reposition_all
        self.show()
        self.raise_()
        
        # 5. Recolocar TODOS para hacer hueco
        ToastNotification.reposition_all(animate=True)
        
        # 6. Iniciar animaciones visuales
        self.anim_fade.setStartValue(0); self.anim_fade.setEndValue(1); self.anim_fade.start()
        self.anim_bar.start()

    def close_toast(self):
        """Cierre suave con fade out."""
        if self.anim_fade.direction() == QPropertyAnimation.Direction.Backward: return
        self.anim_fade.setDirection(QPropertyAnimation.Direction.Backward)
        self.anim_fade.finished.connect(self._cleanup)
        self.anim_fade.start()

    def close_toast_immediate(self):
        """Cierre forzado (cuando hay overflow)."""
        self._cleanup()

    def _cleanup(self):
        if self.parent_ref: self.parent_ref.removeEventFilter(self)
        
        # Remover de la lista si sigue ahí
        if self in ToastNotification._active_toasts: 
            ToastNotification._active_toasts.remove(self)
        
        # Reacomodar los restantes
        ToastNotification.reposition_all(animate=True)
        self.close()

    def move_to(self, target_pos: QPoint, animate=True):
        """Mueve el toast a una posición. Si animate=True, lo hace fluido."""
        if animate:
            if self.anim_pos.state() == QPropertyAnimation.State.Running:
                self.anim_pos.stop()
            self.anim_pos.setEndValue(target_pos)
            self.anim_pos.start()
        else:
            self.move(target_pos)

    @staticmethod
    def reposition_all(animate=True):
        """
        Recalcula la posición de TODOS los toasts activos.
        Apila desde abajo hacia arriba (el más nuevo abajo).
        """
        active = ToastNotification._active_toasts
        if not active: return

        # Tomamos referencia del padre (asumimos que todos tienen el mismo padre)
        parent = active[0].parent_ref
        if not parent: return

        parent_geo = parent.geometry()
        screen_pos = parent.mapToGlobal(QPoint(0,0))
        
        # Márgenes
        margin_bottom = 20
        margin_right = 20
        spacing = 10
        
        # Cursor Y empieza en el fondo de la ventana
        current_y = screen_pos.y() + parent_geo.height() - margin_bottom

        # Iteramos INVERSO (del más nuevo al más viejo)
        # El último de la lista es el más reciente -> Va abajo del todo.
        # El primero de la lista es el más viejo -> Va arriba.
        for toast in reversed(active):
            w = toast.width()
            h = toast.height()
            
            # Calculamos Coordenadas
            # X: Alineado a la derecha (Cambia esto si quieres izquierda)
            target_x = screen_pos.x() + parent_geo.width() - w - margin_right
            
            # Y: Posición actual menos mi altura (crezco hacia arriba)
            target_y = current_y - h
            
            toast.move_to(QPoint(target_x, target_y), animate)
            
            # Subimos el cursor para el siguiente toast
            current_y = target_y - spacing