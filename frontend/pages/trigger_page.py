# frontend/pages/trigger_page.py

from typing import List, Dict
from PyQt6.QtWidgets import (
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QApplication, QFileDialog, QCheckBox, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal

# --- MÓDULOS INTERNOS ---
from backend.services.triggers_service import TriggerService
from frontend.alerts.info_modal import InfoModal
from frontend.components.cards import Card
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.components.flow_layout import FlowLayout 
from frontend.components.trigger_card import MediaCard
from frontend.factories import (
    create_help_btn, create_nav_btn, create_page_header, 
    create_styled_input
)
from frontend.help_content import load_help_content
from frontend.utils import get_icon
from frontend.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style


# =========================================================================
# WORKERS ASÍNCRONOS (Evitan congelar la Interfaz de Usuario)
# =========================================================================
class SaveTriggerWorker(QThread):
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, service, filename, ftype, data, sync_kick):
        super().__init__()
        self.service = service
        self.filename = filename
        self.ftype = ftype
        self.data = data
        self.sync_kick = sync_kick

    def run(self):
        try:
            success, msg = self.service.save_trigger(
                self.filename, self.ftype, self.data, sync_kick=self.sync_kick
            )
            self.finished_signal.emit(success, msg, self.filename)
        except Exception as e:
            self.finished_signal.emit(False, str(e), self.filename)

class SyncKickWorker(QThread):
    finished = pyqtSignal(int)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        changes = self.service.sync_kick_states()
        self.finished.emit(changes)


# =========================================================================
# CLASE PRINCIPAL: PÁGINA DE TRIGGERS
# =========================================================================
class TriggerPage(QWidget):
    def __init__(self, server_worker, db_handler, parent=None):
        super().__init__(parent)
        
        # 1. Inicialización de Servicios y Estado
        self.service = TriggerService(db_handler, server_worker)
        self.full_media_list: List[Dict] = [] 
        self.search_text: str = ""
        self.filter_mode: str = "Todos"
        self._active_workers = []
        
        # 2. Configuración de Sincronización Automática
        self.sync_worker = SyncKickWorker(self.service)
        self.sync_worker.finished.connect(self._on_sync_finished)

        # 3. Construcción de UI
        self.init_ui()
        
        # 4. Carga de datos inicial (Con ligero retraso para renderizado fluido)
        QTimer.singleShot(100, self.load_data)
        QTimer.singleShot(1000, self.sync_worker.start)

    # =========================================================================
    # SECCIÓN 1: CONSTRUCCIÓN DE LA INTERFAZ (UI)
    # =========================================================================
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll principal
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        # Contenedor de contenido
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(*LAYOUT["level_03"])
        self.content_layout.setSpacing(LAYOUT["space_01"])

        # Secciones de la página
        self._setup_header()
        self._setup_config_section()
        self._setup_toolbar()
        self._setup_media_grid()

        self.content_layout.addStretch() 
        self.scroll.setWidget(content_widget)
        main_layout.addWidget(self.scroll)

    def _setup_header(self):
        h_layout = QHBoxLayout()
        h_layout.addWidget(create_page_header("Control de Triggers", "Configura tus alertas visuales y sonoras."))
        h_layout.addSpacing(10)
        h_layout.addWidget(create_help_btn(self._show_help_modal))
        h_layout.addStretch()
        
        # Botones de Acción Globales
        h_layout.addWidget(create_nav_btn("Sincronizar", "refresh-cw.svg", self._handle_manual_sync))
        h_layout.addWidget(create_nav_btn("Importar", "upload.svg", self._handle_import))
        h_layout.addWidget(create_nav_btn("Exportar", "download.svg", self._handle_export))
        
        self.content_layout.addLayout(h_layout)

    def _setup_config_section(self):
        """
        Panel de control unificado: Añadir Archivos, Copiar URL y Estado Global del Overlay.
        """
        card = Card(self)
        card.setFixedHeight(70)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 15, 0)
        layout.setSpacing(5)

        # 1. Botón Añadir Archivo (Principal)
        btn_add = QPushButton("Añadir Archivo")
        btn_add.setIcon(get_icon("plus.svg"))
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(STYLES["btn_primary"])
        btn_add.setFixedWidth(180)
        btn_add.clicked.connect(self._handle_add_file)

        # 2. Botón Copiar URL (Secundario/Nav)
        btn_copy = create_nav_btn("Copiar URL Overlay", "copy.svg", self._handle_copy_url)

        # 3. Estado Global (Switch)
        title = QLabel("Estado Global:")
        title.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-weight: bold; font-size: 13px;")

        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)

        # Ensamblamos la tarjeta
        layout.addWidget(btn_add)
        layout.addWidget(btn_copy)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.chk_on)

        card.layout.addLayout(layout)
        self.content_layout.addWidget(card)

    def _setup_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 10px; border: 1px solid {THEME_DARK['Black_N1']};")

        layout = QHBoxLayout(bar)
        layout.setSpacing(LAYOUT["space_01"])

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("search.svg").pixmap(16, 16))
        icon_lbl.setStyleSheet("border:none; opacity:0.5;")
        
        self.inp_search = create_styled_input("Buscar por archivo o recompensa...", is_cmd=False, callback=self._handle_search_changed)

        lbl_filter = QLabel("Filtrar:")
        lbl_filter.setStyleSheet("border:none; color:#888;")
        
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"])
        self.combo_filter.addItems(["Todos", "Activos", "Desactivados", "Video", "Audio"])
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)

        layout.addWidget(icon_lbl)
        layout.addWidget(self.inp_search, stretch=1)
        layout.addWidget(lbl_filter)
        layout.addWidget(self.combo_filter)
        
        self.content_layout.addWidget(bar)

    def _setup_media_grid(self):
        self.media_container = QWidget()
        self.media_container.setStyleSheet("background: transparent;")
        self.media_layout = FlowLayout(self.media_container, margin=0, spacing=10)
        self.content_layout.addWidget(self.media_container)

    # =========================================================================
    # SECCIÓN 2: LÓGICA DE DATOS Y RENDERIZADO
    # =========================================================================
    def load_data(self):
        self.full_media_list = self.service.get_media_files_with_config()
        self._render_grid()

    def _render_grid(self):
        # 1. Limpiar grid actual de forma segura
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 2. Renderizar tarjetas filtradas
        count = 0
        search_term = self.search_text.lower()

        for item in self.full_media_list:
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            if search_term and (search_term not in fname) and (search_term not in cmd):
                continue
            
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            card = MediaCard(item["filename"], item["type"], item["config"], self)
            self.media_layout.addWidget(card)
            count += 1

        # 3. Mostrar estado vacío si no hay resultados
        if count == 0:
            self._show_empty_state()

    def _show_empty_state(self):
        empty_widget = QWidget()
        empty_widget.setMinimumWidth(400) 
        layout = QVBoxLayout(empty_widget)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("background: transparent; border: none;")
        lbl_img.setPixmap(get_icon("UI_media.svg").pixmap(200, 200))
        
        lbl_msg = QLabel("No hay triggers configurados o encontrados")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-size: 16px; font-weight: bold;")
        
        lbl_sub = QLabel("Añade archivos multimedia usando el botón superior.")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #666; font-size: 13px;")

        layout.addWidget(lbl_img)
        layout.addWidget(lbl_msg)
        layout.addWidget(lbl_sub)

        self.media_layout.addWidget(empty_widget)

    def check_filter_refresh(self):
        # Forzar repintado si el cambio de estado afecta al filtro actual
        if self.filter_mode in ["Activos", "Desactivados"]:
            self._render_grid()

    # =========================================================================
    # SECCIÓN 3: API ASÍNCRONA (GUARDADO Y SINCRONIZACIÓN)
    # =========================================================================
    def save_item(self, filename: str, ftype: str, data: dict, silent: bool = False, sync_kick: bool = True):
        worker = SaveTriggerWorker(self.service, filename, ftype, data, sync_kick)
        worker.finished_signal.connect(lambda s, m, f: self._on_save_finished(s, m, f, silent))
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        
        self._active_workers.append(worker)
        worker.start()

    def _on_save_finished(self, success, msg, filename, silent):
        if not silent:
            type_msg = "status_success" if success else "status_error"
            title = "Guardado" if success else "Error"
            ToastNotification(self, title, msg, type_msg).show_toast()
        
        self._refresh_all_cards_ui()

    def _refresh_all_cards_ui(self):
        fresh_data = self.service.db.get_all_triggers()
        
        for item in self.full_media_list:
            fname = item["filename"]
            if fname in fresh_data:
                item["config"] = fresh_data[fname]

        for i in range(self.media_layout.count()):
            widget = self.media_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'filename') and widget.filename in fresh_data:
                widget.refresh_state_from_config(fresh_data[widget.filename])

    def _cleanup_worker(self, worker):
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()

    def _on_sync_finished(self, changes_count):
        if changes_count > 0:
            self.load_data()
            ToastNotification(self, "Sincronizado", f"Se actualizaron {changes_count} estados desde Kick.", "info").show_toast()

    def preview_item(self, filename: str, ftype: str, config: dict):
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior para probar.", "status_warning").show_toast()
        self.service.preview_media(filename, ftype, config)

    # =========================================================================
    # SECCIÓN 4: MANEJADORES DE EVENTOS DE INTERFAZ
    # =========================================================================
    def _show_help_modal(self):
        content = load_help_content("overlay_page")
        InfoModal(self, "Guía de Overlays", content).exec()

    def _handle_toggle_global(self, checked: bool):
        self.service.set_overlay_active(checked)
        ToastNotification(self, "Overlay", "Activado" if checked else "Desactivado", "info").show_toast()
    
    def _handle_manual_sync(self):
        ToastNotification(self, "Sincronizando", "Verificando estado en Kick...", "info").show_toast()
        self.load_data()      
        if not self.sync_worker.isRunning():
            self.sync_worker.start()

    def _handle_copy_url(self):
        url = self.service.get_local_ip_url()
        QApplication.clipboard().setText(url)
        ToastNotification(self, "Copiado", "URL copiada al portapapeles", "status_success").show_toast()

    def _handle_search_changed(self, text: str):
        self.search_text = text.lower().strip()
        self._render_grid()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self._render_grid()

    def _handle_add_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo Multimedia", "", "Media Files (*.mp4 *.webm *.mp3 *.wav *.ogg)"
        )
        if path:
            self.service.add_single_media(path)
            self.load_data()

    def _handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Configuración", "alertas.csv", "CSV Files (*.csv)")
        if path:
            if self.service.export_csv(path): 
                ToastNotification(self, "Éxito", "Configuración exportada correctamente", "status_success").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo exportar el archivo", "status_error").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Configuración", "", "CSV Files (*.csv)")
        if not path: return

        if not ModalConfirm(self, "Importar", "¿Estás seguro? Esto sobrescribirá la configuración actual.").exec():
            return

        ok_count, fail_count, missing_files = self.service.import_csv(path)
        self.load_data()

        if missing_files:
            msg_missing = "\n".join(missing_files[:5])
            if len(missing_files) > 5: msg_missing += "\n... y más."
            ModalConfirm(self, "Archivos Faltantes", f"La configuración referencia archivos que no tienes:\n{msg_missing}").exec()
        
        ToastNotification(self, "Importación Finalizada", f"Éxito: {ok_count} | Errores: {fail_count}", "status_success").show_toast()