# frontend/pages/trigger_page.py

from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QApplication, QFileDialog, 
    QCheckBox, QFrame, QScrollArea, QSizePolicy
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
    create_styled_input, create_icon_btn
)
from frontend.help_content import load_help_content
from frontend.utils import get_icon
from frontend.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style


# =========================================================================
# WORKER: GUARDADO ASÍNCRONO (Para evitar Lag UI)
# =========================================================================
class SaveTriggerWorker(QThread):
    """
    Hilo secundario que maneja la conexión con la API de Kick y la DB
    """
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
    """
    Hilo que descarga el estado de las recompensas de Kick
    """
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
        
        self.service = TriggerService(db_handler, server_worker)
        self.full_media_list: List[Dict] = [] 
        self.search_text: str = ""
        self.filter_mode: str = "Todos"
        
        self._active_workers = []
        
        self.sync_worker = SyncKickWorker(self.service)
        self.sync_worker.finished.connect(self._on_sync_finished)

        self.init_ui()
        
        QTimer.singleShot(100, self.load_data)
        QTimer.singleShot(1000, self.sync_worker.start)

    # =========================================================================
    # SECCIÓN 1: CONSTRUCCIÓN DE LA INTERFAZ (UI)
    # =========================================================================
    def init_ui(self):
        """Configura el layout principal y el área de scroll."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Configuración del ScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        # Contenedor principal de contenido
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(*LAYOUT["level_03"])
        self.content_layout.setSpacing(LAYOUT["space_01"])

        # Construcción de secciones
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
        h_layout.addWidget(create_nav_btn("Importar", "upload.svg", self._handle_import))
        h_layout.addWidget(create_nav_btn("Exportar", "download.svg", self._handle_export))
        self.content_layout.addLayout(h_layout)

    # =========================================================================
    # SECCIÓN 2: MODIFICACIÓN DE LA CONFIGURACIÓN (UI)
    # =========================================================================
    def _setup_config_section(self):
        """
        MODIFICADO: Usa FlowLayout para que las tarjetas de configuración
        """
        config_container = QWidget()
        config_container.setStyleSheet("background: transparent;")
        
        self.config_layout = FlowLayout(config_container, margin=0, spacing=10)

        # Creamos las tarjetas
        card_url = self._create_url_card()
        card_path = self._create_path_card()
        card_options = self._create_options_card()

        # Añadimos al FlowLayout
        self.config_layout.addWidget(card_url)
        self.config_layout.addWidget(card_path)
        self.config_layout.addWidget(card_options)

        # Añadimos el contenedor a la layout principal de la página
        self.content_layout.addWidget(config_container)

    def _create_url_card(self) -> Card:
        card = Card(self)
        card.setMinimumWidth(300) 
        card.setFixedHeight(60)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0) 
        
        self.txt_url = QLineEdit(self.service.get_local_ip_url())
        self.txt_url.setReadOnly(True)
        self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addWidget(self.txt_url, stretch=1)
        layout.addWidget(create_icon_btn("eye.svg", self._handle_toggle_eye))
        layout.addWidget(create_icon_btn("copy.svg", self._handle_copy_url))
        
        card.layout.addLayout(layout)
        return card

    def _create_path_card(self) -> Card:
        card = Card(self)
        card.setMinimumWidth(300)
        card.setFixedHeight(60)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0) 

        current_path = self.service.get_media_folder() or "Sin carpeta seleccionada"
        self.lbl_path = QLabel(current_path)
        lbl_style = STYLES["input_cmd"]
        self.lbl_path.setStyleSheet(lbl_style)
        self.lbl_path.setWordWrap(False)

        layout.addWidget(self.lbl_path, stretch=1)
        layout.addWidget(create_icon_btn("folder.svg", self._handle_pick_folder))
        layout.addWidget(create_icon_btn("refresh-cw.svg", self._handle_manual_sync))
        
        card.layout.addLayout(layout)
        return card

    def _create_options_card(self) -> Card:
        card = Card(self)
        card.setMinimumWidth(380) 
        card.setFixedHeight(60)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(5)
        
        # Título
        title = QLabel("Globales:")
        title.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-weight: bold; font-size: 12px;")
        
        # Checkbox 1: Posición Aleatoria
        self.chk_rand = QCheckBox("Pos. Aleatoria")
        self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_rand.setStyleSheet(get_switch_style())
        self.chk_rand.setChecked(self.service.db.get_bool("random_pos"))
        self.chk_rand.toggled.connect(self.service.set_random_pos)

        # Checkbox 2: Overlay Activo
        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)

        # Añadimos los elementos en orden horizontal
        h_layout.addWidget(title)
        h_layout.addWidget(self.chk_rand)
        h_layout.addWidget(self.chk_on)
        h_layout.addStretch()

        card.layout.addLayout(h_layout)
        
        return card

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
        
        self.inp_search = create_styled_input("Buscar archivo.", is_cmd=False, callback=self._handle_search_changed)

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
        """Carga datos del servicio y refresca la grilla."""
        self.full_media_list = self.service.get_media_files_with_config()
        self._render_grid()

    def _render_grid(self):
        """Filtra y dibuja las tarjetas multimedia."""
        # Limpiar grid actual
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = 0
        search_term = self.search_text.lower()

        for item in self.full_media_list:
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            # Filtros
            if search_term and (search_term not in fname) and (search_term not in cmd):
                continue
            
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            card = MediaCard(item["filename"], item["type"], item["config"], self)
            self.media_layout.addWidget(card)
            count += 1

        if count == 0:
            self._show_empty_state()

    def _show_empty_state(self):
        # Contenedor para el estado vacío
        empty_widget = QWidget()
        # Le damos un ancho mínimo para que intente centrarse visualmente en el FlowLayout
        empty_widget.setMinimumWidth(400) 
        
        layout = QVBoxLayout(empty_widget)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Imagen SVG
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_img.setStyleSheet("background: transparent; border: none;")
        
        # Usamos get_icon para cargar el SVG y lo escalamos
        pixmap = get_icon("UI_media.svg").pixmap(200, 200)
        lbl_img.setPixmap(pixmap)
        
        # 2. Texto Principal
        lbl_msg = QLabel("No hay triggers configurados")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-size: 16px; font-weight: bold;")
        
        # 3. Subtítulo / Instrucción
        lbl_sub = QLabel("Importa archivos o coloca medios en la carpeta seleccionada.")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #666; font-size: 13px;")

        layout.addWidget(lbl_img)
        layout.addWidget(lbl_msg)
        layout.addWidget(lbl_sub)

        self.media_layout.addWidget(empty_widget)

    def check_filter_refresh(self):
        if self.filter_mode in ["Activos", "Desactivados"]:
            self._render_grid()

    # =========================================================================
    # SECCIÓN 3: API PÚBLICA & ASYNC (CORE LOGIC)
    # =========================================================================
    def save_item(self, filename: str, ftype: str, data: dict, silent: bool = False, sync_kick: bool = True):
        """
        Guarda el item usando un hilo secundario para evitar el LAG de la UI.
        """
        worker = SaveTriggerWorker(self.service, filename, ftype, data, sync_kick)

        worker.finished_signal.connect(lambda s, m, f: self._on_save_finished(s, m, f, silent))
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        
        self._active_workers.append(worker)
        worker.start()

    def _on_save_finished(self, success, msg, filename, silent):
        """
        Callback cuando termina de guardar en la DB/Kick.
        """
        if not silent:
            type_msg = "status_success" if success else "status_error"
            title = "Guardado" if success else "Error"
            ToastNotification(self, title, msg, type_msg).show_toast()
        
        self._refresh_all_cards_ui()

    def _refresh_all_cards_ui(self):
        """
        Actualiza el estado visual de las tarjetas existentes leyendo la DB.
        """
        fresh_data = self.service.db.get_all_triggers()
        
        # 1. Actualizar lista en memoria
        for item in self.full_media_list:
            fname = item["filename"]
            if fname in fresh_data:
                item["config"] = fresh_data[fname]

        # 2. Notificar a los widgets (tarjetas) existentes
        for i in range(self.media_layout.count()):
            widget = self.media_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'filename'):
                if widget.filename in fresh_data:
                    widget.refresh_state_from_config(fresh_data[widget.filename])

    def _cleanup_worker(self, worker):
        """Limpia la memoria del hilo terminado."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()

    def preview_item(self, filename: str, ftype: str, config: dict):
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior para probar.", "status_warning").show_toast()
        self.service.preview_media(filename, ftype, config)
    
    def _on_sync_finished(self, changes_count):
        """
        Se llama cuando termina la sincronización con Kick.
        """
        if changes_count > 0:
            self.load_data()

            ToastNotification(
                self, 
                "Sincronizado", 
                f"Se actualizaron {changes_count} estados desde Kick.", 
                "info"
            ).show_toast()

    # =========================================================================
    # SECCIÓN 4: MANEJADORES DE EVENTOS UI
    # =========================================================================
    def _show_help_modal(self):
        content = load_help_content("overlay_page")
        InfoModal(self, "Guía de Overlays", content).exec()

    def _handle_toggle_global(self, checked: bool):
        self.service.set_overlay_active(checked)
        status = "Activado" if checked else "Desactivado"
        ToastNotification(self, "Overlay", status, "info").show_toast()
    
    def _handle_manual_sync(self):
        """
        Recarga los archivos locales Y fuerza la sincronización con Kick.
        """
        # 1. Feedback visual
        ToastNotification(self, "Sincronizando", "Verificando archivos y estado en Kick...", "info").show_toast()
        # 2. Carga inmediata de archivos locales (por si pusiste un video nuevo en la carpeta)
        self.load_data()      
        # 3. Inicia la sincronización con la nube (si no está corriendo ya)
        if not self.sync_worker.isRunning():
            self.sync_worker.start()

    def _handle_pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder:
            self.service.set_media_folder(folder)
            self.lbl_path.setText(folder)
            self.load_data()

    def _handle_copy_url(self):
        QApplication.clipboard().setText(self.txt_url.text())
        ToastNotification(self, "Copiado", "URL copiada al portapapeles", "status_success").show_toast()

    def _handle_toggle_eye(self):
        current_mode = self.txt_url.echoMode()
        new_mode = QLineEdit.EchoMode.Password if current_mode == QLineEdit.EchoMode.Normal else QLineEdit.EchoMode.Normal
        self.txt_url.setEchoMode(new_mode)

    def _handle_search_changed(self, text: str):
        self.search_text = text.lower().strip()
        self._render_grid()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self._render_grid()

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