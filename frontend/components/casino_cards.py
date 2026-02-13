# frontend/components/casino_cards.py

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, 
    QDoubleSpinBox
)
from frontend.components.accordion_cards import BaseAccordionCard
from frontend.utils import get_icon
from frontend.theme import STYLES

class GameConfigCard(BaseAccordionCard):
    """
    Tarjeta acordeón para configurar un juego específico (Dados, Slots, etc).
    """
    def __init__(self, service, icon_name, title, settings):
        super().__init__(title, "Configuración de pagos", is_active=True)
        self.service = service

        header_layout = self.header.layout()
        
        ico = QLabel()
        ico.setPixmap(get_icon(icon_name).pixmap(24, 24))
        ico.setStyleSheet("border:none; margin-right: 8px; opacity: 0.9;")

        header_layout.insertWidget(0, ico)

        self.status_indicator.hide() 

        for lbl_text, key, default, is_int in settings:
            self.add_content_widget(self._create_content_row(lbl_text, key, default, is_int))

    def _create_content_row(self, text, key, default, is_int):
        """Crea una fila horizontal: Etiqueta ----------- Input"""
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        l = QHBoxLayout(row_widget)
        l.setContentsMargins(0, 2, 0, 2)
        
        # Etiqueta
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#aaa; font-size:12px; border:none;")
        
        # Input (SpinBox o DoubleSpinBox)
        if is_int:
            inp = QSpinBox()
            val = self.service.get_int_setting(key, default)
            inp.setRange(1, 100000)
            inp.setValue(val)
            if "%" in text: inp.setSuffix("%")
            elif "x" in text: inp.setSuffix(" x")
            inp.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))
        else:
            inp = QDoubleSpinBox()
            val = self.service.get_float_setting(key, default)
            inp.setRange(0.1, 1000.0)
            inp.setValue(val)
            inp.setSingleStep(0.1)
            if "x" in text: inp.setSuffix(" x")
            inp.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))

        inp.setStyleSheet(STYLES["spinbox_modern"])
        inp.setFixedWidth(110)

        l.addWidget(lbl)
        l.addStretch()
        l.addWidget(inp)
        
        return row_widget


class LimitsCard(BaseAccordionCard):
    """
    Tarjeta acordeón especial para los Límites Globales.
    """
    def __init__(self, service):
        super().__init__("Límites Globales", "Restricciones de apuestas", is_active=True)
        self.service = service
        
        # Icono
        header_layout = self.header.layout()
        ico = QLabel()
        ico.setPixmap(get_icon("sliders.svg").pixmap(24, 24))
        ico.setStyleSheet("border:none; margin-right: 8px;")
        header_layout.insertWidget(0, ico)
        self.status_indicator.hide()

        # Min Bet
        row_min = self._create_row("Apuesta Mínima:", self.service.get_min_bet(), self.service.set_min_bet)
        self.add_content_widget(row_min)

        # Max Bet
        row_max = self._create_row("Apuesta Máxima:", self.service.get_max_bet(), self.service.set_max_bet)
        self.add_content_widget(row_max)

    def _create_row(self, text, val, callback):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,2,0,2)
        
        lbl = QLabel(text); lbl.setStyleSheet("color:#aaa; font-size:12px; border:none;")
        
        inp = QSpinBox()
        inp.setRange(1, 1000000)
        inp.setValue(val)
        inp.setStyleSheet(STYLES["spinbox_modern"])
        inp.setFixedWidth(110)
        inp.valueChanged.connect(callback)
        
        l.addWidget(lbl); l.addStretch(); l.addWidget(inp)
        return w