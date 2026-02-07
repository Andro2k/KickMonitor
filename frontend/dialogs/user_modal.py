# frontend/dialogs/user_modal.py

import cloudscraper
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QWidget, QFrame, QStackedLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from frontend.utils import get_icon, crop_to_square, get_rounded_pixmap
from frontend.theme import STYLES, THEME_DARK
from frontend.components.base_modal import BaseModal

# ==========================================
# WORKER
# ==========================================
class UserCheckWorker(QThread):
    found = pyqtSignal(dict, bytes)
    error = pyqtSignal(str)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.scraper = cloudscraper.create_scraper()

    def run(self):
        try:
            formatted_user = self.username.strip().replace(" ", "-")
            url = f"https://kick.com/api/v1/channels/{formatted_user}"
            resp = self.scraper.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                user_data = {
                    "slug": data.get("slug"),
                    "username": data.get("user", {}).get("username"),
                    "followers": data.get("followersCount", 0),
                    "profile_pic": data.get("user", {}).get("profile_pic")
                }
                
                img_bytes = None
                if user_data["profile_pic"]:
                    try:
                        img_resp = self.scraper.get(user_data["profile_pic"], timeout=5)
                        if img_resp.status_code == 200: img_bytes = img_resp.content
                    except: pass
                
                self.found.emit(user_data, img_bytes or b"")
            elif resp.status_code == 404:
                self.error.emit(f"Usuario '{formatted_user}' no encontrado.")
            else:
                self.error.emit(f"Error API ({resp.status_code})")
        except Exception:
            self.error.emit("Error de conexión.")

# ==========================================
# DIÁLOGO PRINCIPAL
# ==========================================
class UsernameInputDialog(BaseModal):
    def __init__(self, parent=None):
        super().__init__(parent, width=420, height=520) # Altura ajustada
        self.username = None
        self.check_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = self.body_layout
        layout.setSpacing(15)

        # 1. Encabezado
        header_box = QVBoxLayout()
        header_box.setSpacing(5)
        title = QLabel("Verificar Cuenta")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("h2") # Usa estilo del theme.py
        
        subtitle = QLabel("Ingresa el nombre de usuario de Kick para confirmar.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("normal") # Usa estilo del theme.py
        subtitle.setStyleSheet(f"color: {THEME_DARK['Gray_N1']};")

        header_box.addWidget(title)
        header_box.addWidget(subtitle)
        layout.addLayout(header_box)

        # 2. Barra de Búsqueda
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border: 1px solid {THEME_DARK['border']};
                border-radius: 8px;
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 5, 5, 5)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ej: trainwreckstv")
        self.txt_user.setStyleSheet(STYLES["input_cmd"])
        self.txt_user.textChanged.connect(self._reset_search_state)
        
        self.btn_search = QPushButton()
        self.btn_search.setIcon(get_icon("search.svg"))
        self.btn_search.setFixedSize(32, 32)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self._start_check)
        self.btn_search.setStyleSheet(STYLES["btn_primary"])
        
        search_layout.addWidget(self.txt_user)
        search_layout.addWidget(self.btn_search)
        layout.addWidget(search_container)

        # 3. ÁREA CENTRAL (CORRECCIÓN DE MINI VENTANA)
        # Creamos PRIMERO el contenedor padre
        stack_container = QWidget()
        stack_container.setMinimumHeight(280)

        self.profile_stack = QStackedLayout(stack_container)
        
        # --- VISTA 0: Placeholder ---
        placeholder_view = QWidget()
        placeholder_view.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']};")
        ph_layout = QVBoxLayout(placeholder_view)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_illustration = QLabel()
        pix = get_icon("UI_streamer.svg").pixmap(200, 200)
        if pix.isNull(): pix = get_icon("user.svg").pixmap(100, 100)
        
        lbl_illustration.setPixmap(pix)
        lbl_illustration.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_status = QLabel("Esperando usuario...") 
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; margin-top: 10px;")

        ph_layout.addStretch()
        ph_layout.addWidget(lbl_illustration)
        ph_layout.addWidget(self.lbl_status)
        ph_layout.addStretch()
        
        # --- VISTA 1: Resultado ---
        result_view = QFrame()
        result_view.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']};")
        res_layout = QVBoxLayout(result_view)
        res_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(120, 120)
        self.lbl_avatar.setStyleSheet(f"background-color: {THEME_DARK['Black_N4']}; border-radius: 60px;")
        self.lbl_avatar.setScaledContents(True)
        
        self.lbl_res_name = QLabel("")
        self.lbl_res_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_res_name.setStyleSheet("color: white; font-size: 22px; font-weight: bold; margin-top: 10px;")
        
        self.lbl_res_followers = QLabel("")
        self.lbl_res_followers.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_res_followers.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-weight: bold;")

        res_layout.addStretch()
        res_layout.addWidget(self.lbl_avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        res_layout.addWidget(self.lbl_res_name)
        res_layout.addWidget(self.lbl_res_followers)
        res_layout.addStretch()

        # Añadir al stack (ya tienen padre implícito por el layout)
        self.profile_stack.addWidget(placeholder_view)
        self.profile_stack.addWidget(result_view)
        
        layout.addWidget(stack_container)

        # 4. Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("Confirmar")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setFixedHeight(40)

        try: style_dis = STYLES["btn_primary_disabled"]
        except: style_dis = STYLES["btn_outlined"]
            
        self.btn_confirm.setStyleSheet(style_dis)
        self.btn_confirm.clicked.connect(self._on_confirm)
        self.btn_confirm.setEnabled(False)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    # ==========================================
    # LÓGICA DE CONTROL
    # ==========================================
    def _start_check(self):
        user = self.txt_user.text().strip()
        if not user: return

        self.profile_stack.setCurrentIndex(0)
        self.btn_confirm.setEnabled(False)
        try: self.btn_confirm.setStyleSheet(STYLES["btn_primary_disabled"])
        except: pass
        
        self.lbl_status.setText("Buscando...")
        self.lbl_status.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-weight: bold;")
        
        self.txt_user.setEnabled(False)
        self.btn_search.setEnabled(False)

        if self.check_worker and self.check_worker.isRunning():
            self.check_worker.terminate()

        self.check_worker = UserCheckWorker(user)
        self.check_worker.found.connect(self._on_user_found)
        self.check_worker.error.connect(self._on_error)
        self.check_worker.finished.connect(self._on_worker_finished)
        self.check_worker.start()

    def _on_user_found(self, data, img_bytes):
        self.found_data = data
        self.lbl_res_name.setText(data["username"])
        self.lbl_res_followers.setText(f"{data['followers']:,} seguidores")
        
        pixmap = QPixmap()
        if img_bytes: pixmap.loadFromData(img_bytes)
        
        if not pixmap.isNull():
            square = crop_to_square(pixmap, 120)
            rounded = get_rounded_pixmap(square, is_circle=True)
            self.lbl_avatar.setPixmap(rounded)
        else:
            self.lbl_avatar.setPixmap(get_icon("user.svg").pixmap(120, 120))

        self.profile_stack.setCurrentIndex(1)
        self.btn_confirm.setEnabled(True)
        self.btn_confirm.setStyleSheet(STYLES["btn_primary"])
        self.btn_confirm.setFocus()

    def _on_error(self, msg):
        self.profile_stack.setCurrentIndex(0)
        self.lbl_status.setText(f"{msg}")
        self.lbl_status.setStyleSheet("color: #FF453A; font-weight: bold;")

    def _on_worker_finished(self):
        self.txt_user.setEnabled(True)
        self.btn_search.setEnabled(True)
        self.txt_user.setFocus()

    def _on_confirm(self):
        if hasattr(self, 'found_data'):
            self.username = self.found_data["slug"]
            self.accept()

    def _reset_search_state(self):
        """Si el usuario cambia una letra, invalidamos el resultado anterior."""
        if self.btn_confirm.isEnabled():
            self.btn_confirm.setEnabled(False)
            # Intentamos poner estilo deshabilitado si existe
            try: self.btn_confirm.setStyleSheet(STYLES["btn_primary_disabled"])
            except: pass
            
            # Volvemos a la vista de "Esperando..."
            self.profile_stack.setCurrentIndex(0)
            self.lbl_status.setText("Usuario modificado, presiona Buscar.")
            