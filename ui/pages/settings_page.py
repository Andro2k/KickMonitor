# ui/pages/settings_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, 
    QCheckBox, QDialog, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.factories import (
    create_header_page,
    create_section_header,
    create_setting_row,
    create_styled_input,
    create_styled_button,  
    create_styled_combobox 
)
from ui.components.toast import ToastNotification
from ui.components.modals import ModalConfirm
from ui.dialogs.connection_modal import ConnectionModal
from backend.services.settings_service import SettingsService

class SettingsPage(QWidget):
    user_changed = pyqtSignal()

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller
        self.db = db_handler 
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HEADER (Usando Factory)
        header = create_header_page(
            "Preferencias", 
            "Gestiona el comportamiento de la aplicación y tus integraciones."
        )
        main_layout.addWidget(header)

        # --- Scroll Area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 20, 40, 40)
        self.content_layout.setSpacing(4)

        # ==========================================
        # SECCIÓN 1: APLICACIÓN
        # ==========================================
        self.content_layout.addWidget(create_section_header("Aplicación"))

        # Auto-Connect
        self.chk_auto = QCheckBox("Habilitar")
        self.chk_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto.toggled.connect(lambda v: self.service.set_setting("auto_connect", "1" if v else "0"))
        
        self.content_layout.addWidget(create_setting_row(
            "Conexión Automática",
            "Si se activa, el bot intentará conectarse al chat inmediatamente al abrir la aplicación.",
            self.chk_auto
        ))

        # Formato Hora (Usando Factory)
        self.combo_time = create_styled_combobox(
            ["Sistema", "12-hour: 2:34 PM", "24-hour: 14:34"], 
            width=200
        )
        
        self.content_layout.addWidget(create_setting_row(
            "Formato de Hora",
            "Configura cómo se muestran las fechas y horas en los logs y el chat.",
            self.combo_time
        ))

        # ==========================================
        # SECCIÓN 2: INTEGRACIONES
        # ==========================================
        self.content_layout.addWidget(create_section_header("Integraciones"))

        # Kick (Usando Factory)
        btn_kick = create_styled_button(
            "Conectar Kick", 
            "btn_outlined", 
            self._handle_kick_auth
        )
        
        self.content_layout.addWidget(create_setting_row(
            "Cuenta de Kick",
            "Vincula tu cuenta de streamer para leer el chat y gestionar eventos.",
            btn_kick
        ))

        # Spotify (Usando Factory)
        btn_spot = create_styled_button(
            "Conectar Spotify", 
            "btn_outlined", 
            self._handle_spotify_auth
        )

        self.content_layout.addWidget(create_setting_row(
            "Cuenta de Spotify",
            "Permite mostrar la canción actual y aceptar pedidos (!sr) mediante Spotify.",
            btn_spot
        ))

        # ==========================================
        # SECCIÓN 3: ECONOMÍA
        # ==========================================
        self.content_layout.addWidget(create_section_header("Economía"))

        # Comando
        self.inp_p_cmd = create_styled_input("!puntos", is_cmd=True)
        self.inp_p_cmd.setFixedWidth(150)
        self.inp_p_cmd.editingFinished.connect(lambda: self.service.set_setting("points_command", self.inp_p_cmd.text()))
        
        self.content_layout.addWidget(create_setting_row(
            "Comando de Puntos",
            "El comando que usarán los usuarios para ver su saldo.",
            self.inp_p_cmd
        ))

        # Puntos
        self.inp_p_msg = create_styled_input("10", is_cmd=False)
        self.inp_p_msg.setFixedWidth(100)
        self.inp_p_msg.textChanged.connect(lambda v: self.service.set_setting("points_per_msg", v))

        self.content_layout.addWidget(create_setting_row(
            "Recompensa por Chat",
            "Cantidad de puntos otorgados por cada mensaje enviado.",
            self.inp_p_msg
        ))

        # ==========================================
        # SECCIÓN 4: ZONA DE PELIGRO
        # ==========================================
        self.content_layout.addWidget(create_section_header("Gestión de Datos"))
        
        # Backup (Usando Factory)
        btn_backup = create_styled_button(
            "Crear Backup", 
            "btn_outlined", 
            self._handle_backup
        )
        
        self.content_layout.addWidget(create_setting_row(
            "Copia de Seguridad",
            "Exporta toda la base de datos a un archivo local.",
            btn_backup
        ))

        # Reset Economía (Usando Factory - Estilo Danger)
        btn_reset = create_styled_button(
            "Reiniciar Puntos", 
            "btn_danger_outlined", 
            self._handle_reset_economy
        )
        
        self.content_layout.addWidget(create_setting_row(
            "Reiniciar Economía",
            "Establece los puntos de TODOS los usuarios a 0. Irreversible.",
            btn_reset
        ))

        # Desvincular (Usando Factory - Estilo Danger)
        btn_unlink = create_styled_button(
            "Desvincular Cuenta", 
            "btn_danger_outlined", 
            self._handle_unlink_account
        )
        
        self.content_layout.addWidget(create_setting_row(
            "Cerrar Sesión",
            "Elimina las credenciales de Kick/Spotify y desconecta el bot.",
            btn_unlink
        ))
        
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

    def load_data(self):
        self.chk_auto.setChecked(self.db.get_bool("auto_connect"))
        pts = self.service.get_points_config()
        self.inp_p_cmd.setText(pts["command"])
        self.inp_p_msg.setText(str(pts["per_msg"]))

    def _handle_kick_auth(self):
        modal = ConnectionModal(self.db, service_type="kick", parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
            ToastNotification(self, "Sistema", "Credenciales guardadas", "Status_Green").show_toast()

    def _handle_spotify_auth(self):
        modal = ConnectionModal(self.db, service_type="spotify", worker=self.controller.spotify, parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
             ToastNotification(self, "Spotify", "Configuración guardada", "Status_Green").show_toast()

    def _handle_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            try:
                path = self.service.create_backup(folder)
                ToastNotification(self, "Backup", f"Guardado en: {path}", "Status_Green").show_toast()
            except Exception as e:
                ToastNotification(self, "Error", str(e), "Status_Red").show_toast()

    def _handle_reset_economy(self):
        if ModalConfirm(self, "¿Reiniciar Economía?", "¿Seguro? Puntos a 0.").exec():
            self.service.reset_economy()
            ToastNotification(self, "Economía", "Reiniciada", "Status_Green").show_toast()

    def _handle_unlink_account(self):
        if ModalConfirm(self, "¿Desvincular?", "Se borrarán credenciales y cerrará el bot.").exec():
            self.service.reset_user_data()
            self.user_changed.emit()
            ToastNotification(self, "Cuenta", "Desvinculada correctamente", "Status_Green").show_toast()