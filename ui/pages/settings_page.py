# ui/pages/settings_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QScrollArea, QDialog, QFrame, QSpinBox, QFileDialog, QGridLayout,
    QSizePolicy
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl

from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.dialogs.connection_modal import ConnectionModal
from ui.factories import create_card_header, create_nav_btn, create_page_header
from ui.utils import get_icon
from ui.theme import LAYOUT, THEME_DARK, STYLES
from backend.services.settings_service import SettingsService
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
        outer_layout.setContentsMargins(*LAYOUT["margins"])
        
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
        outer_layout.addWidget(self._create_header())
        self._setup_cards()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_header(self):
        h_frame = QFrame()
        l = QVBoxLayout(h_frame)
        l.addWidget(create_page_header("Ajustes del Sistema", "Gestiona conexiones, actualizaciones y economía del bot."))
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

        # 5. GESTIÓN DE DATOS (NUEVO)
        card_data = self._create_data_card()
        card_data.setMinimumWidth(400)
        card_data.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_data)

    # ==========================================
    # 2. CREADORES DE TARJETAS
    # ==========================================
    def _create_kick_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        l.addWidget(create_card_header("Credenciales Kick", "kick.svg"))
        
        l.addWidget(QLabel("Client ID / Secret para conectar.", styleSheet="color:#888; font-size:12px; border:none;"))
        
        l.addStretch()
        
        btn = QPushButton("Gestionar Keys")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(STYLES["btn_outlined"])
        btn.clicked.connect(self._handle_kick_auth)
        l.addWidget(btn)
        return card

    def _create_system_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        l.addWidget(create_card_header("Sistema", "settings.svg"))

        ver = getattr(self.controller, "VERSION", "Dev")
        l.addWidget(QLabel(f"Versión Actual: v{ver}", styleSheet="color:#888; font-size:12px; border:none;"))
        
        l.addStretch()

        btn = QPushButton("Buscar Actualizaciones")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(STYLES["btn_outlined"])
        btn.clicked.connect(lambda: self.controller.check_updates(manual=True))
        l.addWidget(btn)
        return card

    def _create_spotify_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        l.addWidget(create_card_header("Spotify", "spotify.svg"))

        self.lbl_spot_status = QLabel("Estado: Desconocido")
        self.lbl_spot_status.setStyleSheet("color: #1DB954; font-weight: bold; font-size:12px; border:none;")
        l.addWidget(self.lbl_spot_status)
        
        l.addStretch()
        
        btn = QPushButton("Configurar Acceso")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(STYLES["btn_outlined"])
        btn.clicked.connect(self._handle_spotify_auth)
        l.addWidget(btn)
        return card

    def _create_points_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(15)
        l.addWidget(create_card_header("Sistema de Puntos", "users.svg"))

        grid = QGridLayout()
        grid.setSpacing(LAYOUT["spacing"])

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

    def _create_data_card(self):
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        l.addWidget(create_card_header("Gestión de Datos", "database.svg"))

        # A. INFORMACIÓN DE RUTA
        db_info = self.service.get_database_info()
        
        lbl_path_title = QLabel("Ubicación de la Base de Datos:")
        lbl_path_title.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        l.addWidget(lbl_path_title)

        row_path = QHBoxLayout()
        self.txt_path = QLineEdit(db_info["path"])
        self.txt_path.setReadOnly(True)
        self.txt_path.setStyleSheet(STYLES["input_cmd"] + "color: #AAA;")
        
        btn_open = QPushButton()
        btn_open.setIcon(get_icon("folder.svg"))
        btn_open.setToolTip("Abrir carpeta")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedSize(32, 32)
        btn_open.setStyleSheet(STYLES["btn_nav"])
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(db_info["folder"])))

        row_path.addWidget(self.txt_path)
        row_path.addWidget(btn_open)
        l.addLayout(row_path)

        l.addSpacing(10)
        
        # B. ACCIONES PELIGROSAS (GRID)
        grid = QGridLayout()
        grid.setSpacing(LAYOUT["spacing"])

        # Botón 1: Backup
        btn_backup = create_nav_btn("Crear Backup", "save.svg", self._handle_backup)
        grid.addWidget(btn_backup, 0, 0)

        # Botón 2: Reiniciar Economía
        btn_reset_eco = create_nav_btn("Reiniciar Economía", "refresh-cw.svg", self._handle_reset_economy)
        grid.addWidget(btn_reset_eco, 0, 1)

        # Botón 3: Desvincular Cuenta (ROJO)
        btn_unlink = self._create_action_btn("Desvincular Cuenta", "log-out.svg", is_danger=True)
        btn_unlink.clicked.connect(self._handle_unlink_account)
        grid.addWidget(btn_unlink, 1, 0, 1, 2)

        l.addLayout(grid)
        l.addStretch()
        return card
    
    def _create_action_btn(self, text, icon, is_danger=False):
        btn = QPushButton(text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_danger:
             base_style = (STYLES["btn_danger_outlined"])
            
        btn.setStyleSheet(base_style)
        return btn
    
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

    def _handle_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para Backup")
        if folder:
            try:
                path = self.service.create_backup(folder)
                ToastNotification(self, "Backup", f"Guardado en: {path}", "Status_Green").show_toast()
            except Exception as e:
                ToastNotification(self, "Error", str(e), "Status_Red").show_toast()

    def _handle_reset_economy(self):
        dlg = ModalConfirm(
            self, 
            "¿Reiniciar Economía?", 
            "Esto pondrá a 0 los puntos de TODOS los usuarios y borrará el historial del casino.\n\n¿Estás seguro?"
        )
        if dlg.exec():
            self.service.reset_economy()
            ToastNotification(self, "Economía", "Puntos reiniciados correctamente", "Status_Green").show_toast()

    def _handle_unlink_account(self):
        dlg = ModalConfirm(
            self, 
            "¿Desvincular Cuenta?", 
            "Se borrarán tus credenciales de Kick y Spotify.\nEl bot se desconectará.\n\nEsta acción no se puede deshacer.",
        )
        # Hack visual para que el modal parezca peligroso (opcional)
        dlg.setStyleSheet(dlg.styleSheet() + "QLabel { color: #ef5350; }") 
        
        if dlg.exec():
            # 1. Detener bot si está corriendo
            if self.controller.worker:
                self.controller.stop_bot()
            
            # 2. Borrar datos
            self.service.reset_user_data()
            
            # 3. Notificar y emitir señal para que la UI principal se actualice (ej: Dashboard)
            ToastNotification(self, "Sistema", "Cuenta desvinculada. Reinicia para aplicar cambios completos.", "Status_Yellow").show_toast()
            self.user_changed.emit() # Puedes conectar esto en MainWindow para ir a la Home o mostrar el Login