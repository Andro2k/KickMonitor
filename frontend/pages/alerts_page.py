# frontend/pages/alerts_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QApplication
)
from PyQt6.QtCore import QTimer, Qt

from backend.workers import alert_worker
from frontend.factories import create_page_header
from frontend.theme import LAYOUT, STYLES, THEME_DARK
from frontend.utils import get_icon

from backend.services.alerts_service import AlertsService
from frontend.components.flow_layout import FlowLayout
from frontend.components.accordion_cards import AlertCard, TimerCard

class AlertsPage(QWidget):
    def __init__(self, db_handler, alert_worker=None, parent=None):
        super().__init__(parent)
        self.service = AlertsService(db_handler, alert_worker) 
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
        layout.setContentsMargins(*LAYOUT["level_03"])
        layout.setSpacing(20)
        
        # -----------------------------------------------------------------
        # HEADER PRINCIPAL Y BOTÓN DE URL OBS
        # -----------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.addWidget(create_page_header("Alertas y Timers", "Gestión de Eventos visuales y mensajes."))
        header_layout.addStretch()

        # Botón para copiar URL
        self.btn_copy_url = QPushButton(" URL OBS")
        self.btn_copy_url.setIcon(get_icon("copy.svg"))
        self.btn_copy_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_url.setStyleSheet(STYLES["btn_nav"])
        self.btn_copy_url.clicked.connect(self._handle_copy_url)
        
        header_layout.addWidget(self.btn_copy_url)
        layout.addLayout(header_layout)

        # -----------------------------------------------------------------
        # SECCIÓN 1: EVENTOS (Grid Responsivo)
        # -----------------------------------------------------------------
        events_container = QWidget()
        events_container.setStyleSheet("background: transparent;")
        events_flow = FlowLayout(events_container, margin=0, spacing=(LAYOUT["space_01"]))
        
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
        timers_flow = FlowLayout(timers_container, margin=0, spacing=(LAYOUT["space_01"]))
        
        # Tarjetas de Timers
        timers_flow.addWidget(TimerCard(self.service, "Redes Sociales", "redes", "Ej: Sígueme en Twitter."))
        timers_flow.addWidget(TimerCard(self.service, "Discord / Comunidad", "discord", "Ej: Únete al server."))
        timers_flow.addWidget(TimerCard(self.service, "Promo / Reglas", "promo", "Ej: Respetar normas."))
        
        layout.addWidget(timers_container)
        
        # Spacer Final
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    # -----------------------------------------------------------------
    # LÓGICA DE COPIADO DE URL
    # -----------------------------------------------------------------
    def _handle_copy_url(self):
        # Copiamos la URL apuntando al puerto 6002 (Alertas)
        QApplication.clipboard().setText("http://localhost:6002/alerts")
        
        # Efecto visual de copiado exitoso
        self.btn_copy_url.setText("¡Copiado!")
        self.btn_copy_url.setStyleSheet(STYLES["btn_nav"] + f"color: {THEME_DARK['NeonGreen_Main']};")
        
        # Restauramos el botón a la normalidad después de 1.5 segundos
        QTimer.singleShot(1500, lambda: (self.btn_copy_url.setText(" URL OBS"), self.btn_copy_url.setStyleSheet(STYLES["btn_nav"])))