# ui/pages/settings_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, 
    QCheckBox, QDialog, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from backend.utils.paths import get_app_data_path
from ui.factories import (
    create_header_page,
    create_section_header,
    create_setting_row,
    create_styled_input,
    create_styled_button,  
    create_styled_combobox 
)
from ui.theme import get_switch_style
from ui.components.toast import ToastNotification
from ui.components.modals import ModalConfirm
from ui.dialogs.connection_modal import ConnectionModal
from backend.services.settings_service import SettingsService

class SettingsPage(QWidget):
    user_changed = pyqtSignal()
    # Señal para avisar al MainController que busque actualizaciones
    check_updates_signal = pyqtSignal() 

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller
        self.db = db_handler 
        
        # Versión actual (puedes moverla a una constante global luego)
        self.app_version = "1.8.0" 
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. HEADER
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
        self.content_layout.setSpacing(5)

        # --- SECCIONES ---
        self._setup_app_section()
        self._setup_integrations_section()
        self._setup_economy_section()
        self._setup_danger_section()
        self._setup_system_section() # <--- NUEVA SECCIÓN
        
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

    # ==========================================
    # SECCIÓN 1: APLICACIÓN
    # ==========================================
    def _setup_app_section(self):
        self.content_layout.addWidget(create_section_header("Aplicación"))

        # 1. Auto-Connect
        self.chk_auto = QCheckBox()
        self.chk_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto.setStyleSheet(get_switch_style())
        self.chk_auto.toggled.connect(lambda v: self.service.set_setting("auto_connect", "1" if v else "0"))
        
        self.content_layout.addWidget(create_setting_row(
            "Conexión Automática",
            "Si se activa, el bot intentará conectarse al chat inmediatamente al abrir la aplicación.",
            self.chk_auto
        ))

        # 2. Minimizar a la bandeja (NUEVO)
        self.chk_tray = QCheckBox()
        self.chk_tray.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_tray.setStyleSheet(get_switch_style())
        self.chk_tray.toggled.connect(lambda v: self.service.set_setting("minimize_to_tray", "1" if v else "0"))

        self.content_layout.addWidget(create_setting_row(
            "Minimizar a la Bandeja",
            "Mantiene la aplicación ejecutándose en segundo plano al cerrar o minimizar.",
            self.chk_tray
        ))

        # 3. Formato Hora
        self.combo_time = create_styled_combobox(
            ["Sistema", "12-hour (02:30 PM)", "24-hour (14:30)"], 
            width=200
        )
        
        # Conectar señal de cambio
        self.combo_time.currentIndexChanged.connect(self._handle_time_fmt_changed)
        
        self.content_layout.addWidget(create_setting_row(
            "Formato de Hora",
            "Configura cómo se muestran las fechas en el chat.",
            self.combo_time
        ))

    # ==========================================
    # SECCIÓN 2: INTEGRACIONES
    # ==========================================
    def _setup_integrations_section(self):
        self.content_layout.addWidget(create_section_header("Integraciones"))

        btn_kick = create_styled_button("Conectar Kick", "btn_outlined", self._handle_kick_auth)
        self.content_layout.addWidget(create_setting_row(
            "Cuenta de Kick",
            "Vincula tu cuenta de streamer para leer el chat y gestionar eventos.",
            btn_kick
        ))

        btn_spot = create_styled_button("Conectar Spotify", "btn_outlined", self._handle_spotify_auth)
        self.content_layout.addWidget(create_setting_row(
            "Cuenta de Spotify",
            "Permite mostrar la canción actual y aceptar pedidos (!sr) mediante Spotify.",
            btn_spot
        ))

    # ==========================================
    # SECCIÓN 3: ECONOMÍA
    # ==========================================
    def _setup_economy_section(self):
        self.content_layout.addWidget(create_section_header("Economía"))

        self.inp_p_cmd = create_styled_input("!puntos", is_cmd=True, callback=lambda: self.service.set_setting("points_command", self.inp_p_cmd.text()))
        self.inp_p_cmd.setFixedWidth(150)
        
        self.content_layout.addWidget(create_setting_row(
            "Comando de Puntos",
            "El comando que usarán los usuarios para ver su saldo.",
            self.inp_p_cmd
        ))

        self.inp_p_msg = create_styled_input("10", is_cmd=False, callback=lambda v: self.service.set_setting("points_per_msg", v))
        self.inp_p_msg.setFixedWidth(100)

        self.content_layout.addWidget(create_setting_row(
            "Recompensa por Chat",
            "Cantidad de puntos otorgados por cada mensaje enviado.",
            self.inp_p_msg
        ))

    # ==========================================
    # SECCIÓN 4: ZONA DE PELIGRO
    # ==========================================
    def _setup_danger_section(self):
        self.content_layout.addWidget(create_section_header("Gestión de Datos"))
        
        btn_backup = create_styled_button("Crear Backup", "btn_outlined", self._handle_backup)
        self.content_layout.addWidget(create_setting_row(
            "Copia de Seguridad",
            "Exporta toda la base de datos a un archivo local.",
            btn_backup
        ))

        btn_reset = create_styled_button("Reiniciar Puntos", "btn_danger_outlined", self._handle_reset_economy)
        self.content_layout.addWidget(create_setting_row(
            "Reiniciar Economía",
            "Establece los puntos de TODOS los usuarios a 0. Irreversible.",
            btn_reset
        ))

        btn_unlink = create_styled_button("Desvincular Cuenta", "btn_danger_outlined", self._handle_unlink_account)
        self.content_layout.addWidget(create_setting_row(
            "Cerrar Sesión",
            "Elimina las credenciales de Kick/Spotify y desconecta el bot.",
            btn_unlink
        ))

    # ==========================================
    # SECCIÓN 5: SISTEMA (NUEVO)
    # ==========================================
    def _setup_system_section(self):
        self.content_layout.addWidget(create_section_header("Información del Sistema"))

        # Botón Abrir Logs
        btn_logs = create_styled_button("Abrir Carpeta", "btn_outlined", self._handle_open_logs_folder)
        self.content_layout.addWidget(create_setting_row(
            "Registros de Errores (Logs)",
            "Abre la carpeta donde se guardan los archivos de texto con errores.",
            btn_logs
        ))

        # Botón Actualizar
        btn_update = create_styled_button("Buscar Actualizaciones", "btn_solid_primary", self._handle_check_updates)
        self.content_layout.addWidget(create_setting_row(
            f"Versión Actual: {self.app_version}",
            "Comprueba si hay una nueva versión disponible en GitHub.",
            btn_update
        ))

    # ==========================================
    # LÓGICA DE CARGA DE DATOS
    # ==========================================
    def load_data(self):
        self.chk_auto.setChecked(self.db.get_bool("auto_connect"))
        self.chk_tray.setChecked(self.db.get_bool("minimize_to_tray")) # Cargar estado del tray
        
        pts = self.service.get_points_config()
        self.inp_p_cmd.setText(pts["command"])
        self.inp_p_msg.setText(str(pts["per_msg"]))

        current_fmt = self.db.get("time_fmt", "Sistema")
        index = self.combo_time.findText(current_fmt)
        if index >= 0:
            self.combo_time.setCurrentIndex(index)

    # ==========================================
    # HANDLERS
    # ==========================================
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

    def _handle_open_logs_folder(self):
        """Abre la carpeta real donde se guardan los logs y la DB."""
        folder_path = get_app_data_path()
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def _handle_check_updates(self):
        # Aquí emitimos la señal para que el Controller (que tiene la lógica de red) haga el trabajo
        # O si tienes la lógica aquí, la llamas directo.
        ToastNotification(self, "Sistema", "Buscando actualizaciones...", "info").show_toast()
        
        # Si tienes el método en el controller:
        if hasattr(self.controller, 'check_for_updates'):
            self.controller.check_for_updates()
        else:
            # Placeholder si aún no conectas el backend
            self.check_updates_signal.emit()

    def _handle_time_fmt_changed(self):
        # Guardamos el texto seleccionado para leerlo fácil en MainWindow
        val = self.combo_time.currentText()
        self.service.set_setting("time_fmt", val)