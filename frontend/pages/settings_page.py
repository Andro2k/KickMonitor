# frontend/pages/settings_page.py

from PyQt6.QtWidgets import (
    QHBoxLayout, QWidget, QVBoxLayout, QScrollArea, QFrame, 
    QCheckBox, QDialog, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from backend.utils.paths import get_app_data_path
from backend.workers.update_worker import INTERNAL_VERSION, UpdateCheckerWorker
from frontend.dialogs.update_modal import UpdateModal
from frontend.factories import (
    create_header_page,
    create_section_header,
    create_setting_row,
    create_styled_input,
    create_styled_button,  
    create_styled_combobox 
)
from frontend.theme import get_switch_style
from frontend.alerts.toast_alert import ToastNotification
from frontend.alerts.modal_alert import ModalConfirm
from frontend.dialogs.connection_modal import ConnectionModal
from backend.services.settings_service import SettingsService

class SettingsPage(QWidget):
    user_changed = pyqtSignal()
    check_updates_signal = pyqtSignal() 

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller
        self.db = db_handler 
        self.app_version = INTERNAL_VERSION 
        
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
            "Gestiona el comportamiento de la aplicación y sus integraciones."
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
        self._setup_debug_section()

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
            ["Sistema", "12-hour (02:30 PM)", "24-hour (14:30)"], width=200)
        self.combo_time.currentIndexChanged.connect(self._handle_time_fmt_changed)
        self.content_layout.addWidget(create_setting_row(
            "Formato de Hora",
            "Configura cómo se muestran las fechas en el chat.",
            self.combo_time
        ))

        # Botón Abrir Logs
        btn_logs = create_styled_button("Abrir Carpeta", "btn_outlined", self._handle_open_logs_folder)
        self.content_layout.addWidget(create_setting_row(
            "Registros de Errores (Logs)",
            "Abre la carpeta donde se registran todos registros de consola.",
            btn_logs
        ))

        # Botón Actualizar
        btn_update = create_styled_button("Buscar Actualizaciones", "btn_primary", self._handle_check_updates)
        self.content_layout.addWidget(create_setting_row(
            f"Versión Actual: {self.app_version}",
            "Comprueba si hay una nueva versión disponible en GitHub.",
            btn_update
        ))

    # ==========================================
    # SECCIÓN 2: INTEGRACIONES
    # ==========================================
    def _setup_integrations_section(self):
        self.content_layout.addWidget(create_section_header("Integraciones"))

        btn_kick = create_styled_button("Conectar Kick", "btn_outlined", self._handle_kick_auth)
        self.content_layout.addWidget(create_setting_row(
            "Credenciales de Kick",
            "Vincula tus propias credenciales de streamer para leer el chat y gestionar eventos.",
            btn_kick
        ))

        btn_spot = create_styled_button("Conectar Spotify", "btn_outlined", self._handle_spotify_auth)
        self.content_layout.addWidget(create_setting_row(
            "Credenciales deSpotify",
            "Vincula tus propias credenciales de Developer Spotify para poder personalizar y controlar la musica.",
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
        
        # --- FILA DE BACKUP (MODIFICADA) ---
        # Creamos un widget contenedor para poner los dos botones (Crear y Restaurar) juntos
        backup_container = QWidget()
        l_backup = QHBoxLayout(backup_container)
        l_backup.setContentsMargins(0,0,0,0)
        l_backup.setSpacing(10)
        l_backup.setAlignment(Qt.AlignmentFlag.AlignRight) # Botones a la derecha

        btn_create = create_styled_button("Exportar", "btn_outlined", self._handle_backup)
        btn_restore = create_styled_button("Importar", "btn_outlined", self._handle_restore_backup)
        
        l_backup.addWidget(btn_create)
        l_backup.addWidget(btn_restore)

        self.content_layout.addWidget(create_setting_row(
            "Copia de Seguridad",
            "Exporta tus datos o restaura un archivo .db anterior.",
            backup_container
        ))
        # -----------------------------------

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
    # SECCIÓN 5: DEBUG AVANZADO (NUEVA)
    # ==========================================
    def _setup_debug_section(self):
        self.content_layout.addWidget(create_section_header("Herramientas de Depuración (Avanzado)"))

        # Switch para activar/desactivar Debug en terminal
        self.chk_debug = QCheckBox()
        self.chk_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_debug.setStyleSheet(get_switch_style())
        self.chk_debug.setChecked(self.controller.debug_enabled)
        self.chk_debug.toggled.connect(self.controller.set_debug_mode)

        # 1. Logs en Terminal
        self.content_layout.addWidget(create_setting_row(
            "Ver Logs de Depuración",
            "Muestra mensajes técnicos de Handlers y Workers en la consola del Dashboard.",
            self.chk_debug
        ))

        # 2. Reset de Base de Datos (Limpieza técnica)
        btn_db_check = create_styled_button("Verificar Integridad DB", "btn_outlined", self._debug_check_db)
        self.content_layout.addWidget(create_setting_row(
            "Mantenimiento de Datos",
            "Ejecuta un PRAGMA integrity_check y optimiza el archivo de base de datos.",
            btn_db_check
        ))

        # 3. Estado de Workers (Threads)
        btn_threads = create_styled_button("Refrescar Hilos", "btn_outlined", self._debug_show_threads)
        self.content_layout.addWidget(create_setting_row(
            "Monitor de Workers",
            "Verifica cuántos procesos secundarios (Spotify, Bot, TTS) están activos.",
            btn_threads
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
            ToastNotification(self, "Sistema", "Credenciales guardadas", "status_success").show_toast()

    def _handle_spotify_auth(self):
        modal = ConnectionModal(self.db, service_type="spotify", worker=self.controller.spotify, parent=self)
        if modal.exec() == QDialog.DialogCode.Accepted:
             ToastNotification(self, "Spotify", "Configuración guardada", "status_success").show_toast()

    def _handle_backup(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            try:
                path = self.service.create_backup(folder)
                ToastNotification(self, "Backup", f"Guardado en: {path}", "status_success").show_toast()
            except Exception as e:
                ToastNotification(self, "Error", str(e), "status_error").show_toast()

    def _handle_reset_economy(self):
        if ModalConfirm(self, "¿Reiniciar Economía?", "¿Seguro? Puntos a 0.").exec():
            self.service.reset_economy()
            ToastNotification(self, "Economía", "Reiniciada", "status_success").show_toast()

    def _handle_unlink_account(self):
        if ModalConfirm(self, "¿Desvincular?", "Se borrarán credenciales y cerrará el bot.").exec():
            self.service.reset_user_data()
            self.user_changed.emit() 
            ToastNotification(self, "Cuenta", "Desvinculada correctamente", "status_success").show_toast()

    def _handle_open_logs_folder(self):
        """Abre la carpeta real donde se guardan los logs y la DB."""
        folder_path = get_app_data_path()
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def _handle_check_updates(self):
        """Inicia el worker para consultar el JSON de GitHub."""
        ToastNotification(self, "Sistema", "Buscando actualizaciones...", "status_info").show_toast()
        
        # 1. Crear el worker
        self.check_worker = UpdateCheckerWorker()
        
        # 2. Conectar las señales del worker a nuestros métodos
        self.check_worker.update_available.connect(self._on_update_available)
        self.check_worker.no_update.connect(self._on_up_to_date)
        self.check_worker.error.connect(self._on_update_error)
        
        # 3. Arrancar el hilo
        self.check_worker.start()

    def _on_update_available(self, new_version, url, changelog):
        """Se ejecuta si el worker detecta una versión mayor."""
        # Mostrar el UpdateModal que creaste
        modal = UpdateModal(new_version, changelog, parent=self)
        
        if modal.exec():
            # Si el usuario da click en "ACTUALIZAR" (accept)
            ToastNotification(self, "Actualizador", "Iniciando descarga...", "status_success").show_toast()
            
            # Opcional: Aquí llamarías a tu worker de descarga si lo tienes en el controller
            if hasattr(self.controller, 'start_download_update'):
                self.controller.start_download_update(url)
            else:
                # Si quieres probarlo rápido sin controller, podrías emitir una señal
                print(f"URL de descarga: {url}")

    def _on_up_to_date(self):
        """Se ejecuta si la versión es igual o menor."""
        ToastNotification(self, "Todo al día", f"Ya tienes la última versión ({self.app_version}).", "status_success").show_toast()

    def _on_update_error(self, msg):
        """Se ejecuta si falla la conexión o el JSON."""
        ToastNotification(self, "Error de Actualización", msg, "status_error").show_toast()

    def _handle_time_fmt_changed(self):
        val = self.combo_time.currentText()
        self.service.set_setting("time_fmt", val)

    def _handle_restore_backup(self):
        """Permite al usuario seleccionar un archivo .db para restaurar."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar Copia de Seguridad", 
            "", 
            "Database Files (*.db);;All Files (*)"
        )
        
        if not file_path:
            return

        # Advertencia de seguridad
        if ModalConfirm(self, "⚠ Restaurar Datos", 
                        "Esta acción REEMPLAZARÁ todos tus datos actuales por los del respaldo.\n"
                        "La aplicación se cerrará al finalizar.\n¿Continuar?").exec():
            try:
                # Llamamos al servicio (Asumiendo que agregas este método en SettingsService)
                self.service.restore_backup(file_path)
                
                ToastNotification(self, "Éxito", "Base de datos restaurada.", "status_success").show_toast()
                
                self.load_data() 
                
            except Exception as e:
                ToastNotification(self, "Error", f"No se pudo restaurar: {str(e)}", "status_error").show_toast()

    def _debug_check_db(self):
        """Ejecuta comandos de mantenimiento en la conexión SQLite."""
        path = self.db.get_db_path()
        ToastNotification(self, "DB Debug", f"Archivo: {path}", "status_info").show_toast()
        # Aquí podrías llamar a self.db.execute_query("VACUUM") o similares

    def _debug_show_threads(self):
        """Muestra el conteo de hilos activos de la aplicación."""
        import threading
        count = threading.active_count()
        ToastNotification(self, "Threads", f"Hilos activos: {count}", "status_info").show_toast()    