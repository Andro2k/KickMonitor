# frontend/components/accordion_cards.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame, QCheckBox, 
    QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from frontend.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from frontend.alerts.toast_alert import ToastNotification
from frontend.utils import get_icon_colored

# =========================================================================
# CLASE BASE (Acordeón Optimizado)
# =========================================================================
class BaseAccordionCard(QFrame):
    """
    Clase padre con animación fluida y corrección de estilos.
    """
    def __init__(self, title, subtitle, is_active):
        super().__init__()
        self.setObjectName("AccordionCard")
        
        # --- CONFIG RESPONSIVA ---
        self.setMinimumWidth(320)  # Ancho mínimo antes de bajar de línea
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        # -------------------------
        
        self.is_expanded = False
        self.is_active = is_active
        
        self.setStyleSheet(f"""
            QFrame#AccordionCard {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['Black_N1']};
            }}
            QFrame#AccordionCard:hover {{
                border: 1px solid {THEME_DARK['Black_N4']};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)
        
        # 1. CABECERA (Siempre visible)
        self.header = QFrame()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.mousePressEvent = self.toggle_expand
        
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(*LAYOUT["level_03"])
        
        # Icono Estado
        self.status_indicator = QLabel("●")
        self._update_status_color()
        
        # Textos
        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; font-size: 11px;")
        
        text_container.addWidget(self.lbl_title)
        text_container.addWidget(self.lbl_subtitle)
        
        h_layout.addWidget(self.status_indicator)
        h_layout.addLayout(text_container)
        h_layout.addStretch()
        
        self.main_layout.addWidget(self.header)
        
        # 2. CONTENIDO (Oculto por defecto)
        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0) # Inicia colapsado
        self.content_area.setClipsChildren = lambda x: None
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(15, 0, 15, 15)
        self.content_layout.setSpacing(10)
        
        self.main_layout.addWidget(self.content_area)

        # Animación
        self.anim = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)

    def _update_status_color(self):
        color = THEME_DARK['NeonGreen_Main'] if self.is_active else THEME_DARK['Gray_N2']
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 12px;")

    def toggle_expand(self, event):
        if self.is_expanded:
            self.anim.setStartValue(self.content_area.height())
            self.anim.setEndValue(0)
        else:
            # Calcular altura necesaria
            target_h = self.content_layout.sizeHint().height() + 20
            self.anim.setStartValue(0)
            self.anim.setEndValue(target_h)
            
        self.anim.start()
        self.is_expanded = not self.is_expanded

    def add_content_widget(self, widget):
        self.content_layout.addWidget(widget)

# =========================================================================
# COMPONENTE 1: TARJETA DE ALERTA (Follow, Sub, Host)
# =========================================================================
class AlertCard(BaseAccordionCard):
    def __init__(self, service, title, event_type, desc, default_vars):
        self.service = service
        self.event_type = event_type
        
        msg, active = self.service.get_alert_config(event_type)
        super().__init__(title, desc, active)
        
        self.txt_msg = QTextEdit()
        self.txt_msg.setPlainText(msg)
        self.txt_msg.setPlaceholderText(f"Variables disponibles: {default_vars}")
        self.txt_msg.setFixedHeight(60)
        self.txt_msg.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 6px; padding: 6px; border: 1px solid {THEME_DARK['Gray_Border']};")
        
        # Switch Activar
        self.chk_active = QCheckBox("Activar Alerta")
        self.chk_active.setChecked(active)
        self.chk_active.setStyleSheet(get_switch_style())
        self.chk_active.toggled.connect(self._toggle_active)

        # 🔴 NUEVO: Botón Probar (Estilo secundario)
        btn_test = QPushButton(" Probar")
        btn_test.setIcon(get_icon_colored("play-circle.svg", THEME_DARK['White_N1']))
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N3']}; 
                color: {THEME_DARK['White_N1']}; 
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
                border: 1px solid {THEME_DARK['border']};
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['Black_N2']}; }}
        """)
        btn_test.clicked.connect(self._test_alert)

        # Botón Guardar
        btn_save = QPushButton(" Guardar Cambios")
        btn_save.setIcon(get_icon_colored("save.svg", THEME_DARK['NeonGreen_Main']))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        btn_save.clicked.connect(self._save)

        # Layout Contenido
        row = QHBoxLayout()
        row.addWidget(self.chk_active)
        row.addStretch()
        row.addWidget(btn_test)  # 🔴 Lo agregamos antes del botón de guardar
        row.addWidget(btn_save)

        self.add_content_widget(QLabel("Mensaje del Chat:", styleSheet="color:#AAA; font-size:11px;"))
        self.add_content_widget(self.txt_msg)
        self.add_content_widget(QLabel(f"Variables: {default_vars}", styleSheet="color:#666; font-size:10px; margin-bottom:4px;"))
        self.add_content_widget(QWidget()) # Spacer
        self.content_layout.addLayout(row)

    def _toggle_active(self, checked):
        self.is_active = checked
        self._update_status_color()

    def _save(self):
        txt = self.txt_msg.toPlainText()
        if self.service.save_alert(self.event_type, txt, self.is_active):
            ToastNotification(self, "Guardado", "Configuración actualizada", "status_success").show_toast()

    # 🔴 NUEVA FUNCIÓN: Lógica de prueba
    def _test_alert(self):
        # 1. Forzamos un guardado rápido para probar exactamente el texto que acabas de modificar
        self._save()
        
        # 2. Si la alerta no está activa en el Switch, el servicio la ignorará. Avisamos al usuario:
        if not self.chk_active.isChecked():
            ToastNotification(self, "Aviso", "Activa la alerta para poder probarla.", "status_warning").show_toast()
            return

        # 3. Creamos datos falsos para que las variables {count}, {months} o {viewers} tengan sentido
        mock_data = {
            "count": 120,      # Simula ser el seguidor número 120
            "months": 6,       # Simula una sub de 6 meses
            "viewers": 450     # Simula un raid de 450 personas
        }
        
        # 4. Disparamos la alerta mediante el servicio (Llegará a OBS mágicamente)
        self.service.trigger_alert(self.event_type, "UsuarioTest", mock_data)
        ToastNotification(self, "Prueba Enviada", "¡Revisa tu OBS!", "info").show_toast()

# =========================================================================
# COMPONENTE 2: TARJETA DE TIMER (Mensajes Recurrentes)
# =========================================================================
class TimerCard(BaseAccordionCard):
    def __init__(self, service, title, name, desc):
        self.service = service
        self.name = name
        
        msg, interval, active = self.service.get_timer_config(name)
        super().__init__(title, desc, active)

        # 1. Intervalo
        row_conf = QHBoxLayout()
        self.spin = QSpinBox()
        self.spin.setRange(1, 120)
        self.spin.setValue(interval)
        self.spin.setSuffix(" min")
        self.spin.setStyleSheet(f"{STYLES['spinbox_modern']};")
        
        row_conf.addWidget(QLabel("Intervalo:"))
        row_conf.addWidget(self.spin)
        row_conf.addStretch()
        
        # 2. Mensaje
        self.txt_msg = QTextEdit()
        self.txt_msg.setPlainText(msg)
        self.txt_msg.setFixedHeight(60)
        self.txt_msg.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 6px; padding: 6px; border: 1px solid {THEME_DARK['Gray_Border']};")

        # 3. Footer (Switch + Guardar)
        self.chk_active = QCheckBox("Activar")
        self.chk_active.setChecked(active)
        self.chk_active.setStyleSheet(get_switch_style())
        self.chk_active.toggled.connect(lambda c: setattr(self, 'is_active', c) or self._update_status_color())

        btn_save = QPushButton(" Guardar")
        btn_save.setIcon(get_icon_colored("save.svg", THEME_DARK['NeonGreen_Main']))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        btn_save.clicked.connect(self._save)
        
        footer = QHBoxLayout()
        footer.addWidget(self.chk_active)
        footer.addStretch()
        footer.addWidget(btn_save)

        self.add_content_widget(QLabel("Texto del mensaje:", styleSheet="color:#AAA; font-size:11px;"))
        self.add_content_widget(self.txt_msg)
        self.content_layout.addLayout(row_conf)
        self.content_layout.addLayout(footer)

    def _save(self):
        if self.service.save_timer(self.name, self.txt_msg.toPlainText(), self.spin.value(), self.chk_active.isChecked()):
             ToastNotification(self, "Timer", "Guardado correctamente", "status_success").show_toast()