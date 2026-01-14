# ui/dialogs/connection_modal.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QHBoxLayout, QFrame, QApplication)
from PyQt6.QtCore import Qt
from ui.theme import THEME_DARK, STYLES, LAYOUT

class ConnectionModal(QDialog):
    """
    Diálogo para configurar credenciales de API (Kick, Spotify, etc).
    """
    
    SERVICE_CONFIG = {
        "kick": {
            "title": "Configuración Kick API",
            "btn_color": THEME_DARK["NeonGreen_Main"],
            "btn_hover": THEME_DARK["NeonGreen_Light"],
            "keys": { 
                "id": "client_id", 
                "secret": "client_secret", 
                "uri": "redirect_uri" 
            },
            "uri_readonly": True,
            "show_copy": True
        },
        "spotify": {
            "title": "Configuración Spotify",
            "btn_color": "#1db954",
            "btn_hover": "#1ed760",
            "keys": { 
                "id": "spotify_client_id", 
                "secret": "spotify_secret", 
                "uri": "spotify_redirect_uri" 
            },
            "uri_readonly": False,
            "show_copy": False
        }
    }

    def __init__(self, db, service_type: str, worker=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.service = service_type
        self.worker = worker
        
        self.current_conf = self.SERVICE_CONFIG.get(service_type, self.SERVICE_CONFIG["kick"])
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(450, 420)
        
        self.init_ui()

    def _get_display_value(self, key: str) -> str:
        """
        Retorna el valor solo si es DIFERENTE al default.
        Esto hace que si el valor es el default (ej: localhost:8080), 
        el campo aparezca vacío para que se vea el placeholder.
        """
        current_val = self.db.get(key)
        default_val = self.db.DEFAULT_SETTINGS.get(key, "")
        
        # Si son iguales, retornamos vacío para "ocultarlo"
        if current_val == default_val:
            return ""
        return current_val

    def init_ui(self):
        container = QFrame(self)
        container.setGeometry(10, 10, 430, 400)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border: 1px solid {THEME_DARK['Black_N4']}; 
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        margins = LAYOUT.get("margins", (30, 30, 30, 30))
        layout.setContentsMargins(*margins)
        layout.setSpacing(LAYOUT["spacing"])

        # Título
        lbl_tit = QLabel(self.current_conf["title"])
        lbl_tit.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-size: 20px; font-weight: bold; border: none;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tit)

        keys = self.current_conf["keys"]

        # 1. Client ID
        # CAMBIO: Usamos _get_display_value y EchoMode.Password para seguridad
        layout.addWidget(self._create_label("Client ID:"))
        self.txt_id = QLineEdit(self._get_display_value(keys["id"]))
        self.txt_id.setPlaceholderText("Client ID (Oculto)")
        self.txt_id.setEchoMode(QLineEdit.EchoMode.Password) # <--- Ahora se oculta como password
        self.txt_id.setStyleSheet(STYLES["input"])
        layout.addWidget(self.txt_id)

        # 2. Client Secret
        # CAMBIO: Usamos _get_display_value
        layout.addWidget(self._create_label("Client Secret:"))
        self.txt_secret = QLineEdit(self._get_display_value(keys["secret"]))
        self.txt_secret.setPlaceholderText("Client Secret (Oculto)")
        self.txt_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_secret.setStyleSheet(STYLES["input"])
        layout.addWidget(self.txt_secret)

        # 3. Redirect URI
        layout.addWidget(self._create_label("Redirect URI:"))
        h_uri = QHBoxLayout()
        
        # CAMBIO: Usamos _get_display_value. 
        self.txt_uri = QLineEdit(self._get_display_value(keys["uri"]))
        
        # Mostramos el valor por defecto EN EL PLACEHOLDER como sugerencia
        default_uri = self.db.DEFAULT_SETTINGS.get(keys["uri"], "")
        self.txt_uri.setPlaceholderText(default_uri or "Redirect URI")
        
        self.txt_uri.setStyleSheet(STYLES["input"])
        
        if self.current_conf["uri_readonly"]:
            self.txt_uri.setReadOnly(True)
            self.txt_uri.setStyleSheet(STYLES["input"] + "background-color: #2a2a2a; color: #666;")
        
        h_uri.addWidget(self.txt_uri)

        if self.current_conf["show_copy"]:
            btn_copy = QPushButton("Copiar")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setFixedSize(60, 38)
            btn_copy.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 5px; color: #ccc;")
            btn_copy.clicked.connect(self.copy_uri)
            h_uri.addWidget(btn_copy)
            
        layout.addLayout(h_uri)
        layout.addStretch()

        self._setup_action_buttons(layout)

    def _create_label(self, text: str) -> QLabel:
        return QLabel(text, styleSheet="border:none; color:#888; font-size:12px;")

    def _setup_action_buttons(self, parent_layout: QVBoxLayout):
        h_btns = QHBoxLayout()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        
        text_color = THEME_DARK['White_N1'] if self.service == 'kick' else 'black'
        btn_save.setStyleSheet(STYLES["btn_solid_primary"])
        btn_save.clicked.connect(self.save_data)
        
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        parent_layout.addLayout(h_btns)

    def copy_uri(self):
        # Si el campo está vacío (porque es default), copiamos el default real de la DB, no el texto vacío
        text = self.txt_uri.text()
        if not text:
            keys = self.current_conf["keys"]
            text = self.db.DEFAULT_SETTINGS.get(keys["uri"], "")
            
        QApplication.clipboard().setText(text)
        
        sender = self.sender()
        if sender: 
            sender.setText("OK")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: sender.setText("Copiar"))

    def save_data(self):
        keys = self.current_conf["keys"]
        
        def get_val_to_save(input_widget, key_name):
            text = input_widget.text().strip()
            if not text:
                return self.db.DEFAULT_SETTINGS.get(key_name, "")
            return text

        self.db.set(keys["id"], get_val_to_save(self.txt_id, keys["id"]))
        self.db.set(keys["secret"], get_val_to_save(self.txt_secret, keys["secret"]))
        self.db.set(keys["uri"], get_val_to_save(self.txt_uri, keys["uri"]))
        
        if self.service == "spotify" and self.worker:
            self.worker.authenticate()
            
        self.accept()