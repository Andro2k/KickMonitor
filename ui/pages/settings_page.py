# ui/pages/settings_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QScrollArea, QDialog, QFrame, QSpinBox, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from ui.components.toast import ToastNotification
from ui.dialogs.connection_modal import ConnectionModal
from ui.utils import get_icon
from ui.theme import LAYOUT, THEME_DARK, STYLES
from services.settings_service import SettingsService
from ui.components.flow_layout import FlowLayout

class SettingsPage(QWidget):
    user_changed = pyqtSignal()

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller
        self.spotify = self.controller.spotify
        
        self.init_ui()
        self.load_data()
        
        self.spotify.status_msg.connect(self._update_spotify_status)

    # ==========================================
    # 1. SETUP UI (RESPONSIVE)
    # ==========================================
    def init_ui(self):
        # 1. SCROLL AREA EXTERNO
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # 2. FLOW LAYOUT
        self.flow_layout = FlowLayout(content, margin=LAYOUT["margins"][0], spacing=LAYOUT["spacing"])

        # 3. CONSTRUCCIÓN
        # Header Fijo
        outer_layout.addWidget(self._create_header())
        
        # Tarjetas al Flow
        self._setup_cards()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_header(self):
        h_frame = QFrame()
        l = QVBoxLayout(h_frame)
        l.setContentsMargins(*LAYOUT["margins"])
        l.addWidget(QLabel("Ajustes del Sistema", objectName="h2"))
        l.addWidget(QLabel("Gestiona conexiones, actualizaciones y economía del bot.", objectName="subtitle"))
        return h_frame

    def _setup_cards(self):
        """Crea y añade las tarjetas al layout fluido."""
        
        # 1. Tarjeta API Kick
        card_kick = self._create_kick_card()
        card_kick.setMinimumWidth(300)
        card_kick.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_kick)

        # 2. Tarjeta Sistema
        card_sys = self._create_system_card()
        card_sys.setMinimumWidth(300)
        card_sys.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_sys)

        # 3. Tarjeta Spotify
        card_spot = self._create_spotify_card()
        card_spot.setMinimumWidth(300)
        card_spot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_spot)

        # 4. Tarjeta Economía (Puntos) - Más ancha
        card_pts = self._create_points_card()
        card_pts.setMinimumWidth(450)
        card_pts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_pts)

    # ==========================================
    # 2. CREADORES DE TARJETAS
    # ==========================================
    def _create_kick_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(10)

        self._add_card_header(l, "kick.svg", "Credenciales Kick")
        
        l.addWidget(QLabel("Client ID / Secret para conectar.", styleSheet="color:#888; font-size:12px; border:none;"))
        
        l.addStretch()
        
        btn = QPushButton("Gestionar Keys")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 8px; padding: 8px;
            }} 
            QPushButton:hover {{ border-color: {THEME_DARK['NeonGreen_Main']}; }}
        """)
        btn.clicked.connect(self._handle_kick_auth)
        l.addWidget(btn)
        return card

    def _create_system_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(10)

        self._add_card_header(l, "settings.svg", "Sistema")
        
        ver = getattr(self.controller, "VERSION", "Dev")
        l.addWidget(QLabel(f"Versión Actual: v{ver}", styleSheet="color:#888; font-size:12px; border:none;"))
        
        l.addStretch()

        btn = QPushButton("Buscar Actualizaciones")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 8px; padding: 8px;
            }} 
            QPushButton:hover {{ 
                border-color: {THEME_DARK['NeonGreen_Main']}; color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(lambda: self.controller.check_updates(manual=True))
        l.addWidget(btn)
        return card

    def _create_spotify_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(10)

        self._add_card_header(l, "spotify.svg", "Spotify")
        
        self.lbl_spot_status = QLabel("Estado: Desconocido")
        self.lbl_spot_status.setStyleSheet("color: #1DB954; font-weight: bold; font-size:12px; border:none;")
        l.addWidget(self.lbl_spot_status)
        
        l.addStretch()
        
        btn = QPushButton("Configurar Acceso")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 8px; padding: 8px;
            }} 
            QPushButton:hover {{ border-color: #1DB954; }}
        """)
        btn.clicked.connect(self._handle_spotify_auth)
        l.addWidget(btn)
        return card

    def _create_points_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(15)

        self._add_card_header(l, "users.svg", "Sistema de Puntos")
        
        grid = QGridLayout()
        grid.setSpacing(10)

        # Helpers interno
        def add_field(row, col, label, widget):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #ccc; font-weight: bold; border: none; font-size:11px;")
            grid.addWidget(lbl, row, col)
            grid.addWidget(widget, row + 1, col)

        # 1. Comando
        self.inp_p_cmd = QLineEdit()
        self.inp_p_cmd.setStyleSheet(STYLES["input_cmd"])
        self.inp_p_cmd.editingFinished.connect(lambda: self.service.set_setting("points_command", self.inp_p_cmd.text()))
        add_field(0, 0, "Nombre Comando:", self.inp_p_cmd)

        # 2. Puntos por Mensaje
        self.spin_p_msg = QSpinBox()
        self.spin_p_msg.setRange(0, 1000)
        self.spin_p_msg.setStyleSheet(STYLES["spinbox_modern"])
        self.spin_p_msg.valueChanged.connect(lambda v: self.service.set_setting("points_per_msg", v))
        add_field(0, 1, "Puntos/Mensaje:", self.spin_p_msg)
        
        # 3. Puntos por Tiempo
        self.spin_p_time = QSpinBox()
        self.spin_p_time.setRange(0, 10000)
        self.spin_p_time.setStyleSheet(STYLES["spinbox_modern"])
        self.spin_p_time.valueChanged.connect(lambda v: self.service.set_setting("points_per_min", v))
        add_field(0, 2, "Puntos/Minuto:", self.spin_p_time)

        l.addLayout(grid)
        l.addStretch()
        return card

    def _add_card_header(self, layout, icon_name, title):
        h = QHBoxLayout()
        ico = QLabel()
        ico.setStyleSheet("border: none; opacity: 0.8;")
        ico.setPixmap(get_icon(icon_name).pixmap(QSize(20, 20)))
        lbl = QLabel(title)
        lbl.setObjectName("h3")
        lbl.setStyleSheet("border: none;")
        h.addWidget(ico)
        h.addWidget(lbl)
        h.addStretch()
        layout.addLayout(h)

    # ==========================================
    # 3. CARGA DE DATOS
    # ==========================================
    def load_data(self):
        pts = self.service.get_points_config()
        self.inp_p_cmd.setText(pts["command"])
        self.spin_p_msg.setValue(pts["per_msg"])
        self.spin_p_time.setValue(pts["per_min"])

    # ==========================================
    # 4. HANDLERS
    # ==========================================
    def _handle_kick_auth(self):
        modal = ConnectionModal(self.service.db, service_type="kick", parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
            ToastNotification(self, "Sistema", "Credenciales guardadas", "Status_Green").show_toast()

    def _handle_spotify_auth(self):
        modal = ConnectionModal(self.service.db, service_type="spotify", worker=self.spotify, parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
             ToastNotification(self, "Spotify", "Configuración guardada", "Status_Green").show_toast()

    def _update_spotify_status(self, msg):
        self.lbl_spot_status.setText(f"Estado: {msg}")