# frontend/components/features/alerts.py

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt

# Importamos la clase base visual desde nuestro nuevo CORE
from frontend.components.core.cards import BaseAccordionCard

# Importaciones del resto de la app
from frontend.theme import THEME_DARK, STYLES, get_switch_style
from frontend.notifications.toast_alert import ToastNotification
from frontend.utils import get_icon_colored

# =========================================================================
# COMPONENTE 1: TARJETA DE ALERTA (Follow, Sub, Host)
# =========================================================================
class AlertCard(BaseAccordionCard):
    """
    Tarjeta interactiva para configurar las alertas que van hacia el OBS/Chat.
    """
    def __init__(self, service, title, event_type, desc, default_vars):
        self.service = service
        self.event_type = event_type
        
        msg, active = self.service.get_alert_config(event_type)
        super().__init__(title, desc, active)
        
        self.txt_msg = QTextEdit()
        self.txt_msg.setPlainText(msg)
        self.txt_msg.setPlaceholderText(f"Variables disponibles: {default_vars}")
        self.txt_msg.setFixedHeight(60)
        self.txt_msg.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 6px; padding: 6px;")
        
        # Switch Activar
        self.chk_active = QCheckBox("Activar Alerta")
        self.chk_active.setChecked(active)
        self.chk_active.setStyleSheet(get_switch_style())
        self.chk_active.toggled.connect(self._toggle_active)

        # Botón Probar
        btn_test = QPushButton(" Probar")
        btn_test.setIcon(get_icon_colored("play-circle.svg", THEME_DARK['White_N1']))
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N3']}; 
                color: {THEME_DARK['White_N1']}; 
                border-radius: 6px; padding: 6px 12px; font-weight: bold;               
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
        row.addWidget(btn_test)  
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

    def _test_alert(self):
        self._save()

        if not self.chk_active.isChecked():
            ToastNotification(self, "Aviso", "Activa la alerta para poder probarla.", "status_warning").show_toast()
            return

        mock_data = {
            "count": 120,      
            "months": 6,       
            "viewers": 450     
        }
        self.service.trigger_alert(self.event_type, "UsuarioTest", mock_data)
        ToastNotification(self, "Prueba Enviada", "¡Revisa tu OBS!", "info").show_toast()

# =========================================================================
# COMPONENTE 2: TARJETA DE TIMER (Mensajes Recurrentes)
# =========================================================================
class TimerCard(BaseAccordionCard):
    """
    Tarjeta interactiva para configurar mensajes recurrentes (Timers) en el chat.
    """
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
        self.txt_msg.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 6px; padding: 6px; ")

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