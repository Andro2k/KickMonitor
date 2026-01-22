# frontend/dialogs/user_modal.py

import cloudscraper
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QWidget, QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QSize
from PyQt6.QtGui import QPixmap, QColor

from frontend.utils import get_icon, crop_to_square, get_rounded_pixmap
from frontend.theme import STYLES, THEME_DARK, LAYOUT
from frontend.components.base_modal import BaseModal

# ==========================================
# WORKER: BUSCAR USUARIO EN SEGUNDO PLANO
# ==========================================
class UserCheckWorker(QThread):
    found = pyqtSignal(dict, bytes) # Datos del usuario, Bytes de la imagen
    error = pyqtSignal(str)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.scraper = cloudscraper.create_scraper()

    def run(self):
        try:
            # 1. Consultar API de Kick
            url = f"https://kick.com/api/v1/channels/{self.username}"
            resp = self.scraper.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 2. Extraer datos clave
                user_data = {
                    "slug": data.get("slug"),
                    "username": data.get("user", {}).get("username"),
                    "followers": data.get("followersCount", 0),
                    "profile_pic": data.get("user", {}).get("profile_pic")
                }

                # 3. Descargar imagen de perfil (si existe)
                img_bytes = None
                if user_data["profile_pic"]:
                    try:
                        img_resp = self.scraper.get(user_data["profile_pic"], timeout=5)
                        if img_resp.status_code == 200:
                            img_bytes = img_resp.content
                    except:
                        pass # Si falla la imagen, no importa, mandamos datos igual
                
                self.found.emit(user_data, img_bytes or b"")
            elif resp.status_code == 404:
                self.error.emit("Usuario no encontrado.")
            else:
                self.error.emit(f"Error de conexión ({resp.status_code})")
                
        except Exception as e:
            self.error.emit("Error de red. Intenta nuevamente.")

# ==========================================
# DIÁLOGO PRINCIPAL
# ==========================================
class UsernameInputDialog(BaseModal):
    def __init__(self, parent=None):
        super().__init__(parent, width=400, height=500)
        self.username = None
        self.check_worker = None
        
        self._setup_ui()

    def _setup_ui(self):
        layout = self.body_layout
        
        # 1. Encabezado
        header = QLabel("Conectar Canal")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {THEME_DARK['White_N1']}; font-size: 20px; font-weight: bold; border:none;")
        layout.addWidget(header)
        
        desc = QLabel("Busca tu usuario de Kick para verificar la cuenta.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; font-size: 12px; border:none; margin-bottom: 10px;")
        layout.addWidget(desc)

        # 2. Input y Botón de Búsqueda
        input_container = QWidget()
        input_container.setStyleSheet(f"""
            QWidget {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 8px;
                border: 1px solid {THEME_DARK['border']};
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ej: trainwreckstv")
        self.txt_user.setStyleSheet("border: none; color: white; font-size: 14px; background: transparent;")
        self.txt_user.returnPressed.connect(self._start_check)
        
        self.btn_search = QPushButton()
        self.btn_search.setIcon(get_icon("search.svg")) # Asegúrate de tener este icono o usa otro
        self.btn_search.setFixedSize(36, 36)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self._start_check)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['NeonGreen_Main']};
                border-radius: 6px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #00CC00; }}
        """)

        input_layout.addWidget(self.txt_user)
        input_layout.addWidget(self.btn_search)
        layout.addWidget(input_container)

        # 3. Mensaje de Estado
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 12px; margin-top: 5px; border:none;")
        layout.addWidget(self.lbl_status)

        layout.addSpacing(10)

        # 4. Tarjeta de Resultado (Oculta al inicio)
        self.result_card = QFrame()
        self.result_card.setVisible(False)
        self.result_card.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['border']};
            }}
        """)
        card_layout = QHBoxLayout(self.result_card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(15)

        # Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(60, 60)
        self.lbl_avatar.setStyleSheet("background-color: #333; border-radius: 30px; border:none;")
        self.lbl_avatar.setScaledContents(True)

        # Textos de la tarjeta
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_res_name = QLabel("Username")
        self.lbl_res_name.setStyleSheet("font-weight: bold; font-size: 16px; color: white; border:none; background:transparent;")
        
        self.lbl_res_followers = QLabel("0 Followers")
        self.lbl_res_followers.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-size: 12px; border:none; background:transparent;")

        info_col.addWidget(self.lbl_res_name)
        info_col.addWidget(self.lbl_res_followers)

        card_layout.addWidget(self.lbl_avatar)
        card_layout.addLayout(info_col)
        
        layout.addWidget(self.result_card)
        layout.addStretch()

        # 5. Botones Finales
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("Confirmar")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setFixedHeight(45)
        self.btn_confirm.setStyleSheet(STYLES["btn_primary"])
        self.btn_confirm.clicked.connect(self._on_confirm)
        self.btn_confirm.setEnabled(False) # Deshabilitado hasta verificar
        self.btn_confirm.setAlpha = 0.5 # Visualmente deshabilitado

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    # ==========================================
    # LÓGICA
    # ==========================================
    def _start_check(self):
        user = self.txt_user.text().strip()
        if not user: return

        # Reset UI
        self.result_card.setVisible(False)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setStyleSheet(STYLES["btn_primary"].replace("rgba(0, 231, 1, 0.9)", "gray")) # Hack visual simple
        self.lbl_status.setText("🔍 Buscando en Kick...")
        self.lbl_status.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; border:none;")
        
        # Deshabilitar input mientras busca
        self.txt_user.setEnabled(False)
        self.btn_search.setEnabled(False)

        # Iniciar Worker
        self.check_worker = UserCheckWorker(user)
        self.check_worker.found.connect(self._on_user_found)
        self.check_worker.error.connect(self._on_error)
        self.check_worker.finished.connect(self._on_worker_finished)
        self.check_worker.start()

    def _on_user_found(self, data, img_bytes):
        self.found_data = data # Guardamos data temporalmente
        
        # Actualizar Tarjeta
        self.lbl_res_name.setText(data["username"])
        self.lbl_res_followers.setText(f"{data['followers']:,} seguidores")
        
        # Procesar Imagen
        pixmap = QPixmap()
        if img_bytes:
            pixmap.loadFromData(img_bytes)
        
        if not pixmap.isNull():
            # Recortar en círculo
            square = crop_to_square(pixmap, 60)
            rounded = get_rounded_pixmap(square, is_circle=True)
            self.lbl_avatar.setPixmap(rounded)
        else:
            self.lbl_avatar.setPixmap(get_icon("user.svg").pixmap(60, 60))

        # Mostrar UI de Éxito
        self.result_card.setVisible(True)
        self.lbl_status.setText("✅ Usuario verificado")
        self.lbl_status.setStyleSheet("color: #32D74B; border:none;")
        
        # Habilitar Confirmar
        self.btn_confirm.setEnabled(True)
        self.btn_confirm.setStyleSheet(STYLES["btn_primary"])
        self.btn_confirm.setFocus()

    def _on_error(self, msg):
        self.lbl_status.setText(f"❌ {msg}")
        self.lbl_status.setStyleSheet("color: #FF453A; border:none;")
        self.result_card.setVisible(False)

    def _on_worker_finished(self):
        self.txt_user.setEnabled(True)
        self.txt_user.setFocus()
        self.btn_search.setEnabled(True)

    def _on_confirm(self):
        if hasattr(self, 'found_data'):
            self.username = self.found_data["slug"]
            self.accept()