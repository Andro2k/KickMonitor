# ui/pages/alerts_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea
)
from ui.factories import create_page_header
from ui.theme import LAYOUT
from backend.services.alerts_service import AlertsService
from ui.components.flow_layout import FlowLayout
from ui.components.alert_cards import AlertCard, TimerCard

class AlertsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = AlertsService(db_handler)
        self.init_ui()

    def init_ui(self):
        # 1. SCROLL AREA
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(20)
        
        # -----------------------------------------------------------------
        # SECCIÓN 1: EVENTOS (Grid Responsivo)
        # -----------------------------------------------------------------
        layout.addWidget(create_page_header("Alertas de Chat", "Alertas en Mensajes del chat."))

        events_container = QWidget()
        events_container.setStyleSheet("background: transparent;")
        # Usamos FlowLayout para que las cards se acomoden solas
        events_flow = FlowLayout(events_container, margin=0, spacing=(LAYOUT["spacing"]))
        # Tarjetas de Eventos
        events_flow.addWidget(AlertCard(self.service, "Nuevo Seguidor", "follow", "Mensaje al seguir.", "{user}, {count}"))
        events_flow.addWidget(AlertCard(self.service, "Suscripción", "subscription", "Mensaje al suscribirse.", "{user}, {months}"))
        events_flow.addWidget(AlertCard(self.service, "Host / Raid", "host", "Mensaje al alojar.", "{user}, {viewers}"))
        
        layout.addWidget(events_container)

        # -----------------------------------------------------------------
        # SECCIÓN 2: TIMERS (Grid Responsivo)
        # -----------------------------------------------------------------
        layout.addWidget(create_page_header("Timers", "Mensajes Recurrentes en el chat."))
        timers_container = QWidget()
        timers_container.setStyleSheet("background: transparent;")
        # Otro FlowLayout independiente para esta sección
        timers_flow = FlowLayout(timers_container, margin=0, spacing=(LAYOUT["spacing"]))
        # Tarjetas de Timers
        timers_flow.addWidget(TimerCard(self.service, "Redes Sociales", "redes", "Ej: Sígueme en Twitter..."))
        timers_flow.addWidget(TimerCard(self.service, "Discord / Comunidad", "discord", "Ej: Únete al server..."))
        timers_flow.addWidget(TimerCard(self.service, "Promo / Reglas", "promo", "Ej: Respetar normas..."))
        
        layout.addWidget(timers_container)
        
        # Spacer Final
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)