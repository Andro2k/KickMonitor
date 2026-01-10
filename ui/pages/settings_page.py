# ui/pages/settings_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QScrollArea, QDialog, QFrame, QSpinBox, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal

# Componentes y Utilidades
from ui.components.cards import Card
from ui.components.toast import ToastNotification
from ui.dialogs.connection_modal import ConnectionModal
from ui.utils import get_icon
from ui.theme import LAYOUT, THEME_DARK, STYLES
from services.settings_service import SettingsService

class SettingsPage(QWidget):
    user_changed = pyqtSignal()

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller  # Referencia al controlador principal
        
        # Obtenemos el worker de Spotify desde el controlador
        self.spotify = self.controller.spotify
        
        self.init_ui()
        self.load_data()
        
        # Conexión externa (Status Spotify)
        self.spotify.status_msg.connect(self._update_spotify_status)

    # ==========================================
    # 1. SETUP UI
    # ==========================================
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Cabecera Fija
        self._setup_header(main_layout)

        # 2. Área de Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(content)
        # Margen externo definido en el tema
        self.content_layout.setContentsMargins(*LAYOUT["outer"]) 
        self.content_layout.setSpacing(LAYOUT["spacing"])

        # --- SECCIONES ---
        
        # Fila 1: Credenciales API y Sistema (Nueva ubicación)
        self._setup_top_row()
        
        # Fila 2: Economía
        self.content_layout.addWidget(self._create_points_card())

        # Fila 3: Spotify
        self.content_layout.addWidget(self._create_spotify_card())
        
        self.content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _setup_header(self, layout):
        header = QFrame()
        l = QVBoxLayout(header)
        l.setContentsMargins(*LAYOUT["margins"])
        l.addWidget(QLabel("Ajustes", objectName="h2"))
        l.addWidget(QLabel("Gestiona conexiones, actualizaciones y economía del bot.", objectName="subtitle"))
        layout.addWidget(header)

    def _setup_top_row(self):
        """Fila superior con APIs y Sistema."""
        row = QHBoxLayout()
        row.setSpacing(LAYOUT["spacing"])
        row.addWidget(self._create_api_card())
        row.addWidget(self._create_system_card())
        self.content_layout.addLayout(row)

    # ==========================================
    # 2. CREADORES DE TARJETAS
    # ==========================================
    def _create_api_card(self):
        """Tarjeta pequeña para credenciales técnicas."""
        card = Card()
        self._add_card_header(card, "kick.svg", "Credenciales Kick")
        
        lbl_info = QLabel("Client ID / Secret para conectar el bot.")
        lbl_info.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-weight: bold; margin-bottom: 5px; border: none;")
        lbl_info.setWordWrap(True)
        card.layout.addWidget(lbl_info)
        
        btn = QPushButton("Gestionar Keys")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 6px; padding: 8px;
            }} 
            QPushButton:hover {{ border-color: {THEME_DARK['NeonGreen_Main']}; }}
        """)
        btn.clicked.connect(self._handle_kick_auth)
        card.layout.addWidget(btn)
        return card

    def _create_system_card(self):
        """Nueva tarjeta para actualizaciones y versión."""
        card = Card()
        # Puedes usar un icono genérico, aquí reutilizo settings.svg
        self._add_card_header(card, "settings.svg", "Sistema") 
        
        # Versión actual obtenida del Controller
        ver = getattr(self.controller, "VERSION", "0.0.0")
        if ver == "0.0.0":
            ver = "Dev / No detectada"
        lbl_ver = QLabel(f"Versión Actual: v{ver}")
        lbl_ver.setStyleSheet("color: #AAA; font-size: 13px; border: none; margin-bottom: 5px;")
        card.layout.addWidget(lbl_ver)

        # Botón de búsqueda manual
        btn = QPushButton("Buscar Actualizaciones")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 6px; padding: 8px;
            }} 
            QPushButton:hover {{ 
                border-color: {THEME_DARK['NeonGreen_Main']}; 
                color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        # Conectamos indicando que es una búsqueda manual
        btn.clicked.connect(lambda: self.controller.check_updates(manual=True))
        
        card.layout.addWidget(btn)
        return card

    def _create_spotify_card(self):
        card = Card()
        self._add_card_header(card, "spotify.svg", "Spotify")
        
        self.lbl_spot_status = QLabel("Estado: Desconocido")
        # Color verde Spotify
        self.lbl_spot_status.setStyleSheet("color: #1DB954; font-weight: bold; margin-bottom: 5px; border: none;")
        card.layout.addWidget(self.lbl_spot_status)
        
        btn = QPushButton("Configurar Acceso")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['Black_N4']}; color: {THEME_DARK['White_N1']}; 
                border: 1px solid {THEME_DARK['Gray_Border']}; border-radius: 6px; padding: 8px;
            }} 
            QPushButton:hover {{ border-color: #1DB954; }}
        """)
        btn.clicked.connect(self._handle_spotify_auth)
        card.layout.addWidget(btn)
        return card

    def _create_points_card(self):
        card = Card()
        self._add_card_header(card, "users.svg", "Sistema de Puntos")
        
        # Grid para inputs
        grid = QGridLayout()
        grid.setSpacing(10)

        # Helpers
        def add_field(row, col, label, widget):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #ccc; font-weight: bold; border: none;")
            grid.addWidget(lbl, row, col)
            grid.addWidget(widget, row + 1, col)

        # 1. Comando
        self.inp_p_cmd = QLineEdit()
        self.inp_p_cmd.setStyleSheet(STYLES["input_cmd"])
        self.inp_p_cmd.editingFinished.connect(lambda: self.service.set_setting("points_command", self.inp_p_cmd.text()))
        add_field(0, 0, "Nombre de Puntos:", self.inp_p_cmd)

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

        card.layout.addLayout(grid)
        return card

    def _add_card_header(self, card, icon_name, title):
        h = QHBoxLayout()
        ico = QLabel()
        ico.setStyleSheet("border: none;")
        ico.setPixmap(get_icon(icon_name).pixmap(QSize(20, 20)))
        lbl = QLabel(title)
        lbl.setObjectName("h3")
        lbl.setStyleSheet("border: none;")
        h.addWidget(ico)
        h.addWidget(lbl)
        h.addStretch()
        card.layout.addLayout(h)

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