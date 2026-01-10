# ui/pages/alerts_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame, QCheckBox, 
    QScrollArea, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from ui.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from ui.components.toast import ToastNotification
from ui.utils import get_icon, get_colored_icon
from services.alerts_service import AlertsService
from ui.components.flow_layout import FlowLayout  # <--- IMPORTAMOS

# =========================================================================
# REGIÓN 1: CLASE BASE (Acordeón Optimizado)
# =========================================================================
class BaseAccordionCard(QFrame):
    """
    Clase padre con animación fluida y corrección de estilos.
    Adaptada para funcionar en Grid/Flow Layout.
    """
    def __init__(self, title, subtitle, is_active):
        super().__init__()
        self.setObjectName("AccordionCard")
        
        # --- CONFIG RESPONSIVA ---
        self.setMinimumWidth(320)  # Ancho mínimo antes de bajar de línea
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # -------------------------
        
        self.is_expanded = False
        self.is_active = is_active
        
        self._setup_base_style()
        self._build_header(title, subtitle)
        self._build_content_container()
        
        # Animación
        self.anim = QPropertyAnimation(self.content, b"maximumHeight")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.finished.connect(self._on_anim_finished)

    def _setup_base_style(self):
        self.setStyleSheet(f"""
            QFrame#AccordionCard {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['border']};
            }}
            QFrame#Content {{
                background-color: {THEME_DARK['Black_N3']};
                border-top: 1px solid {THEME_DARK['border']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)

    def _build_header(self, title, subtitle):
        self.header = QFrame()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.mousePressEvent = self.toggle_expand
        self.header.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Icono Flecha
        self.arrow = QPushButton()
        self.arrow.setIcon(get_icon("chevron-right.svg"))
        self.arrow.setStyleSheet("border:none; background:transparent;")
        self.arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Textos
        v_box = QVBoxLayout()
        v_box.setSpacing(2)
        self.lbl_title = QLabel(title, styleSheet=f"font-size:14px; font-weight:bold; color:{THEME_DARK['White_N1']}; border:none;")
        self.lbl_sub = QLabel(subtitle, styleSheet=f"font-size:12px; color:{THEME_DARK['Gray_N1']}; border:none;")
        v_box.addWidget(self.lbl_title)
        v_box.addWidget(self.lbl_sub)

        # Switch
        self.chk = QCheckBox()
        self.chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk.setStyleSheet(get_switch_style())
        self.chk.setChecked(self.is_active)
        self.chk.clicked.connect(self.on_switch_toggle)

        layout.addWidget(self.arrow)
        layout.addLayout(v_box, stretch=1)
        layout.addWidget(self.chk)
        
        # Layout principal del frame
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header)

    def _build_content_container(self):
        self.content = QFrame()
        self.content.setObjectName("Content")
        self.content.setMaximumHeight(0)
        self.content.setVisible(False) 
        
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)
        
        self.layout().addWidget(self.content)

    def toggle_expand(self, event=None):
        if self.anim.state() == QPropertyAnimation.State.Running:
            return

        self.is_expanded = not self.is_expanded
        
        icon = "chevron-down.svg" if self.is_expanded else "chevron-right.svg"
        self.arrow.setIcon(get_icon(icon))
        
        # Calculamos la altura necesaria
        self.content.setVisible(True) # Hacemos visible para calcular sizeHint
        h = self.content_layout.sizeHint().height()
        
        if self.is_expanded:
            self.anim.setStartValue(0)
            self.anim.setEndValue(h)
        else:
            self.anim.setStartValue(self.content.height())
            self.anim.setEndValue(0)
            
        self.anim.start()

    def _on_anim_finished(self):
        if not self.is_expanded:
            self.content.setVisible(False)
        else:
            # Liberamos la altura para que se ajuste si cambia el contenido dinámicamente
            self.content.setMaximumHeight(16777215)

    def on_switch_toggle(self): pass
    def save_data(self): pass

# =========================================================================
# REGIÓN 2: IMPLEMENTACIONES (AlertCard y TimerCard)
# =========================================================================
class AlertCard(BaseAccordionCard):
    def __init__(self, service, title, event_key, subtitle, help_text):
        self.service = service
        self.event_key = event_key
        msg, active = self.service.get_alert_config(event_key)
        super().__init__(title, subtitle, active)
        self._setup_content(msg, help_text)

    def _setup_content(self, msg, help_text):
        self.content_layout.addWidget(QLabel("Mensaje:", styleSheet="color:#aaa; font-weight:bold; border:none;"))
        self.txt = QTextEdit()
        self.txt.setPlainText(msg)
        self.txt.setFixedHeight(70)
        self.txt.setStyleSheet(f"QTextEdit {{ background:{THEME_DARK['Black_N1']}; color:white; border-radius:6px; padding:8px; border:none; }}")
        self.content_layout.addWidget(self.txt)

        row = QHBoxLayout()
        row.addWidget(QLabel(help_text, styleSheet="color:#666; font-size:11px; font-style:italic; border:none;"), stretch=1)
        row.addWidget(self._create_save_btn())
        self.content_layout.addLayout(row)

    def _create_save_btn(self):
        c_green = THEME_DARK['NeonGreen_Main']
        btn = QPushButton(" Guardar")
        btn.setIcon(get_colored_icon("save.svg", c_green))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(100, 32)
        btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{c_green}; border:1px solid {c_green}; border-radius:6px; font-weight:bold; }}
            QPushButton:hover {{ background:{c_green}; color:black; }}
        """)
        btn.clicked.connect(lambda: self.save_data(notify=True))
        return btn

    def on_switch_toggle(self):
        self.save_data(notify=True, only_state=True)

    def save_data(self, notify=False, only_state=False):
        msg = self.txt.toPlainText()
        active = self.chk.isChecked()
        self.service.save_alert(self.event_key, msg, active)
        if notify:
            txt = "Estado actualizado" if only_state else "Alerta guardada"
            ToastNotification(self, "Alertas", txt, "Status_Green").show_toast()

class TimerCard(BaseAccordionCard):
    def __init__(self, service, title, timer_key, help_text):
        self.service = service
        self.timer_key = timer_key
        msg, interval, active = self.service.get_timer_config(timer_key)
        super().__init__(title, f"Cada {interval} min", active)
        self._setup_content(msg, interval, help_text)

    def _setup_content(self, msg, interval, help_text):
        row_time = QHBoxLayout()
        row_time.addWidget(QLabel("Intervalo (min):", styleSheet="color:#aaa; font-weight:bold; border:none;"))
        self.spin = QSpinBox()
        self.spin.setRange(1, 1440)
        self.spin.setValue(interval)
        self.spin.setFixedWidth(80)
        self.spin.setStyleSheet(STYLES["spinbox_modern"])
        row_time.addWidget(self.spin)
        row_time.addStretch()
        self.content_layout.addLayout(row_time)

        self.content_layout.addWidget(QLabel("Mensaje:", styleSheet="color:#aaa; font-weight:bold; border:none;"))
        self.txt = QTextEdit()
        self.txt.setPlainText(msg)
        self.txt.setFixedHeight(60)
        self.txt.setStyleSheet(f"QTextEdit {{ background:{THEME_DARK['Black_N1']}; color:white; border-radius:6px; padding:8px; border:none; }}")
        self.content_layout.addWidget(self.txt)

        row = QHBoxLayout()
        row.addWidget(QLabel(help_text, styleSheet="color:#666; font-size:11px; font-style:italic; border:none;"), stretch=1)
        
        c_green = THEME_DARK['NeonGreen_Main']
        btn = QPushButton(" Guardar")
        btn.setIcon(get_colored_icon("save.svg", c_green))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(100, 32)
        btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{c_green}; border:1px solid {c_green}; border-radius:6px; font-weight:bold; }}
            QPushButton:hover {{ background:{c_green}; color:black; }}
        """)
        btn.clicked.connect(lambda: self.save_data(notify=True))
        row.addWidget(btn)
        self.content_layout.addLayout(row)

    def on_switch_toggle(self):
        self.save_data(notify=True, only_state=True)

    def save_data(self, notify=False, only_state=False):
        msg = self.txt.toPlainText()
        mins = self.spin.value()
        active = self.chk.isChecked()
        self.service.save_timer(self.timer_key, msg, mins, active)
        self.lbl_sub.setText(f"Cada {mins} min")
        if notify:
            txt = "Timer actualizado" if only_state else "Timer guardado"
            ToastNotification(self, "Timers", txt, "Status_Green").show_toast()

# =========================================================================
# REGIÓN 3: PÁGINA PRINCIPAL (Layout Responsivo)
# =========================================================================
class AlertsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = AlertsService(db_handler)
        self.init_ui()

    def init_ui(self):
        # 1. SCROLL AREA
        main = QVBoxLayout(self)
        main.setContentsMargins(0,0,0,0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        
        # 2. LAYOUT PRINCIPAL DEL CONTENEDOR
        layout = QVBoxLayout(container)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(20) # Un poco más de espacio entre secciones

        # Header
        h = QHBoxLayout()
        v = QVBoxLayout()
        v.setSpacing(2)
        v.addWidget(QLabel("Alertas de Chat", objectName="h2"))
        v.addWidget(QLabel("Configura las respuestas automáticas del bot.", objectName="subtitle"))
        h.addLayout(v)
        h.addStretch()
        layout.addLayout(h)

        # -----------------------------------------------------------------
        # SECCIÓN 1: EVENTOS (Grid Responsivo)
        # -----------------------------------------------------------------
        layout.addWidget(QLabel("Eventos", styleSheet=f"color:{THEME_DARK['Gray_N2']}; font-weight:bold; border:none;"))
        
        events_container = QWidget()
        events_container.setStyleSheet("background: transparent;")
        # Usamos FlowLayout aquí para que las alertas se acomoden
        events_flow = FlowLayout(events_container, margin=0, spacing=15)
        
        events_flow.addWidget(AlertCard(self.service, "Nuevo Seguidor", "follow", "Mensaje al seguir.", "{user}, {count}"))
        events_flow.addWidget(AlertCard(self.service, "Suscripción", "subscription", "Mensaje al suscribirse.", "{user}, {months}"))
        events_flow.addWidget(AlertCard(self.service, "Host / Raid", "host", "Mensaje al alojar.", "{user}, {viewers}"))
        
        layout.addWidget(events_container)

        # -----------------------------------------------------------------
        # SECCIÓN 2: TIMERS (Grid Responsivo)
        # -----------------------------------------------------------------
        layout.addWidget(QLabel("Mensajes Recurrentes (Timers)", styleSheet=f"color:{THEME_DARK['Gray_N2']}; font-weight:bold; border:none;"))
        
        timers_container = QWidget()
        timers_container.setStyleSheet("background: transparent;")
        # Otro FlowLayout independiente para esta sección
        timers_flow = FlowLayout(timers_container, margin=0, spacing=15)
        
        timers_flow.addWidget(TimerCard(self.service, "Redes Sociales", "redes", "Ej: Sígueme en Twitter..."))
        timers_flow.addWidget(TimerCard(self.service, "Discord / Comunidad", "discord", "Ej: Únete al server..."))
        timers_flow.addWidget(TimerCard(self.service, "Promo / Reglas", "promo", "Ej: Respetar normas..."))
        
        layout.addWidget(timers_container)

        layout.addStretch()
        scroll.setWidget(container)
        main.addWidget(scroll)