# frontend/pages/settings_page.py

import threading
from PyQt6.QtWidgets import (
    QHBoxLayout, QSpinBox, QWidget, QVBoxLayout, QScrollArea, QFrame, 
    QCheckBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from backend.utils.paths import get_app_data_path
from backend.workers.update_worker import INTERNAL_VERSION, UpdateCheckerWorker, UpdateDownloaderWorker
from frontend.factories import (
    create_header_page, create_section_header, create_setting_row,
    create_styled_input, create_styled_button, create_styled_combobox 
)
from frontend.theme import STYLES, get_switch_style
from frontend.alerts.toast_alert import ToastNotification
from frontend.alerts.modal_alert import ModalConfirm
from frontend.dialogs.download_modal import DownloadModal
from backend.services.settings_service import SettingsService

class SettingsPage(QWidget):
    user_changed = pyqtSignal()
    check_updates_signal = pyqtSignal() 

    def __init__(self, db_handler, controller, parent=None):
        super().__init__(parent)
        self.service = SettingsService(db_handler)
        self.controller = controller
        self.db = db_handler 
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(create_header_page("Preferencias", "Gestiona el comportamiento de la aplicación y sus configuraciones generales."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 20, 40, 40)
        self.content_layout.setSpacing(5)

        self._setup_app_section()
        self._setup_economy_section()
        self._setup_danger_section()
        self._setup_debug_section()

        self.content_layout.addStretch()
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

    # ==========================================
    # CREADORES MÁGICOS (DRY PATTERN)
    # ==========================================
    def _create_switch(self, title, description, db_key):
        chk = QCheckBox()
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setStyleSheet(get_switch_style())
        chk.setChecked(self.db.get_bool(db_key))
        chk.toggled.connect(lambda v: self.service.set_setting(db_key, "1" if v else "0"))
        
        self.content_layout.addWidget(create_setting_row(title, description, chk))
        return chk

    def _create_action_row(self, title, description, btn_text, btn_style, callback):
        btn = create_styled_button(btn_text, btn_style, callback)
        self.content_layout.addWidget(create_setting_row(title, description, btn))
        return btn

    # ==========================================
    # SECCIONES
    # ==========================================
    def _setup_app_section(self):
        self.content_layout.addWidget(create_section_header("Aplicación"))

        self._create_switch("Conexión Automática", "Conecta el bot al chat inmediatamente al abrir la aplicación.", "auto_connect")
        self._create_switch("Minimizar a la Bandeja", "Mantiene la app en segundo plano al cerrar.", "minimize_to_tray")

        self.combo_time = create_styled_combobox(["Sistema", "12-hour (02:30 PM)", "24-hour (14:30)"], width=200)
        current_fmt = self.db.get("time_fmt", "Sistema")
        self.combo_time.setCurrentIndex(self.combo_time.findText(current_fmt) if self.combo_time.findText(current_fmt) >= 0 else 0)
        self.combo_time.currentIndexChanged.connect(lambda: self.service.set_setting("time_fmt", self.combo_time.currentText()))
        self.content_layout.addWidget(create_setting_row("Formato de Hora", "Configura cómo se muestran las fechas en el chat.", self.combo_time))

        self._create_action_row("Registros de Errores (Logs)", "Abre la carpeta donde se registran los errores.", "Abrir Carpeta", "btn_outlined", self._handle_open_logs_folder)
        
        # NUEVO: Ahora el botón llama a _handle_check_updates internamente
        self._create_action_row(f"Versión Actual: {INTERNAL_VERSION}", "Comprueba si hay una nueva versión en GitHub.", "Buscar Actualizaciones", "btn_primary", self._handle_check_updates)

    def _setup_economy_section(self):
        self.content_layout.addWidget(create_section_header("Economía"))

        pts_cfg = self.service.get_points_config()
        inp_p_cmd = create_styled_input(pts_cfg["command"], is_cmd=True, callback=lambda: self.service.set_setting("points_command", inp_p_cmd.text()))
        inp_p_cmd.setFixedWidth(150)
        self.content_layout.addWidget(create_setting_row("Comando de Puntos", "El comando que usarán los usuarios.", inp_p_cmd))

        spin_points = QSpinBox()
        spin_points.setFixedWidth(100)
        spin_points.setRange(0, 10000) 
        spin_points.setSingleStep(5)   
        spin_points.setStyleSheet(STYLES["spinbox_modern"]) 
        try: val = int(pts_cfg["per_msg"])
        except: val = 10
        spin_points.setValue(val)
        spin_points.valueChanged.connect(lambda v: self.service.set_setting("points_per_msg", str(v)))
        
        self.content_layout.addWidget(create_setting_row("Recompensa por Chat", "Puntos otorgados por cada mensaje enviado.", spin_points))

    def _setup_danger_section(self):
        self.content_layout.addWidget(create_section_header("Gestión de Datos"))
        
        backup_container = QWidget()
        l_backup = QHBoxLayout(backup_container)
        l_backup.setContentsMargins(0,0,0,0)
        l_backup.setSpacing(10)
        l_backup.setAlignment(Qt.AlignmentFlag.AlignRight)
        l_backup.addWidget(create_styled_button("Exportar", "btn_outlined", self._handle_backup))
        l_backup.addWidget(create_styled_button("Importar", "btn_outlined", self._handle_restore_backup))

        self.content_layout.addWidget(create_setting_row("Copia de Seguridad", "Exporta tus datos o restaura un .db anterior.", backup_container))
        self._create_action_row("Reiniciar Economía", "Establece los puntos de TODOS a 0. Irreversible.", "Reiniciar Puntos", "btn_danger_outlined", self._handle_reset_economy)
        self._create_action_row("Cerrar Sesión", "Elimina las credenciales y desconecta el bot.", "Desvincular Cuenta", "btn_danger_outlined", self._handle_unlink_account)

    def _setup_debug_section(self):
        self.content_layout.addWidget(create_section_header("Herramientas de Depuración (Avanzado)"))
        
        chk_debug = self._create_switch("Ver Logs de Depuración", "Muestra mensajes técnicos en la consola.", "debug_mode")
        chk_debug.toggled.connect(self.controller.set_debug_mode) 
        
        self._create_action_row("Mantenimiento de Datos", "Optimiza el archivo de base de datos.", "Verificar Integridad DB", "btn_outlined", self._debug_check_db)
        self._create_action_row("Monitor de Workers", "Verifica cuántos procesos secundarios están activos.", "Refrescar Hilos", "btn_outlined", self._debug_show_threads)

    # ==========================================
    # HANDLERS GENERALES
    # ==========================================
    def _handle_backup(self):
        if folder := QFileDialog.getExistingDirectory(self, "Seleccionar carpeta"):
            try:
                path = self.service.create_backup(folder)
                ToastNotification(self, "Backup", f"Guardado en: {path}", "status_success").show_toast()
            except Exception as e:
                ToastNotification(self, "Error", str(e), "status_error").show_toast()

    def _handle_restore_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Copia de Seguridad", "", "Database Files (*.db);;All Files (*)")
        if not file_path: return
        mensaje = "Esta acción REEMPLAZARÁ todos tus datos actuales.<br><br><b>La aplicación se cerrará automáticamente</b> para aplicar los cambios.<br>¿Continuar?"
        
        if ModalConfirm(self, "Restaurar Datos", mensaje).exec():
            try:
                # 1. Restaurar el archivo (cierra la DB por debajo)
                self.service.restore_backup(file_path)
                
                # 2. Avisar al usuario que todo salió bien
                ToastNotification(self, "Éxito", "Restauración completada. Cerrando...", "status_success").show_toast()
                
                # 3. 🔴 FIX: Forzar el cierre de la app. 
                # Esto es obligatorio, de lo contrario la app intentaría buscar cosas en una base de datos que ya no existe en memoria.
                QApplication.quit()
                
            except Exception as e:
                ToastNotification(self, "Error", f"No se pudo restaurar: {str(e)}", "status_error").show_toast()

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
        QDesktopServices.openUrl(QUrl.fromLocalFile(get_app_data_path()))

    def _debug_check_db(self):
        ToastNotification(self, "DB Debug", f"Archivo: {self.db.get_db_path()}", "status_info").show_toast()

    def _debug_show_threads(self):
        ToastNotification(self, "Threads", f"Hilos activos: {threading.active_count()}", "status_info").show_toast()

    # ==========================================
    # LÓGICA DE ACTUALIZACIONES (NUEVO)
    # ==========================================
    def _handle_check_updates(self):
        """Lanza el buscador de actualizaciones silencioso."""
        ToastNotification(self, "Actualizador", "Buscando nuevas versiones...", "status_info").show_toast()
        
        self.checker = UpdateCheckerWorker()
        self.checker.update_available.connect(self._on_update_available)
        self.checker.no_update.connect(self._on_up_to_date)
        self.checker.error.connect(self._on_update_error)
        self.checker.start()

    def _on_update_available(self, new_version, url, changelog):
        """Se ejecuta si encontramos una versión más nueva en GitHub."""
        
        # Como tu changelog es HTML, ModalConfirm lo renderizará perfecto
        mensaje = f"¿Deseas descargar e instalar esta actualización ahora?<br><br>{changelog}"
        
        if ModalConfirm(self, f"¡Actualización v{new_version} Disponible!", mensaje).exec():
            # 1. Abrimos ventana de progreso bloqueante
            self.dl_modal = DownloadModal(self)
            self.dl_modal.show()
            
            # 2. Empezamos la descarga real
            self.dl_worker = UpdateDownloaderWorker(url)
            self.dl_worker.progress.connect(self.dl_modal.update_progress)
            self.dl_worker.finished.connect(self._on_download_finished)
            self.dl_worker.error.connect(self._on_update_error)
            self.dl_worker.start()

    def _on_download_finished(self):
        """Se ejecuta cuando la descarga terminó y se lanzó el EXE."""
        self.dl_modal.accept()
        QApplication.quit()

    def _on_up_to_date(self):
        ToastNotification(self, "Actualizador", f"Ya tienes la última versión ({INTERNAL_VERSION}).", "status_success").show_toast()

    def _on_update_error(self, msg):
        if hasattr(self, 'dl_modal'):
            self.dl_modal.accept()
        ToastNotification(self, "Error", msg, "status_error").show_toast()