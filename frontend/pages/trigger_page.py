# frontend/pages/overlay_page.py

from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QApplication, QFileDialog, 
    QCheckBox, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer

from frontend.alerts.info_modal import InfoModal
from frontend.components.cards import Card
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.components.flow_layout import FlowLayout 
from frontend.components.trigger_card import MediaCard
from frontend.factories import create_help_btn, create_nav_btn, create_page_header, create_styled_input, create_icon_btn
from frontend.help_content import load_help_content
from frontend.utils import get_icon
from frontend.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from backend.services.triggers_service import TriggerService

class TriggerPage(QWidget):
    def __init__(self, server_worker, db_handler, parent=None):
        super().__init__(parent)
        
        # --- Dependencias y Estado ---
        self.service = TriggerService(db_handler, server_worker)
        self.full_media_list: List[Dict] = [] 
        self.search_text: str = ""
        self.filter_mode: str = "Todos"

        # --- Inicialización ---
        self.init_ui()
        # Carga diferida para no bloquear el inicio de la app
        QTimer.singleShot(100, self.load_data)

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
        self.content_layout.setContentsMargins(*LAYOUT["margins"])
        self.content_layout.setSpacing(LAYOUT["spacing"])

        # Construcción de secciones
        self._setup_header()
        self._setup_config_section()
        self._setup_toolbar()
        self._setup_media_grid()

        self.scroll.setWidget(content_widget)
        main_layout.addWidget(self.scroll)

    def _setup_header(self):
        """Encabezado con título y botones de importación/exportación."""
        h_layout = QHBoxLayout()
        h_layout.addWidget(create_page_header("Control de Triggers", "Configura tus alertas visuales y sonoras."))
        h_layout.addSpacing(10)
        h_layout.addWidget(create_help_btn(self._show_help_modal))
        h_layout.addStretch()
        h_layout.addWidget(create_nav_btn("Importar", "upload.svg", self._handle_import))
        h_layout.addWidget(create_nav_btn("Exportar", "download.svg", self._handle_export))
        self.content_layout.addLayout(h_layout)

    def _show_help_modal(self):
        # Llamamos al modal pasando el texto desde el diccionario
        content = load_help_content("overlay_page")
        InfoModal(self, "Guía de Overlays", content).exec()

    def _setup_config_section(self):
        """
        Sección superior con tarjetas de URL, Carpeta y Ajustes Globales.
        """
        container = QHBoxLayout()
        container.setSpacing(LAYOUT["spacing"])
        
        layout_left = QVBoxLayout()
        layout_left.setSpacing(LAYOUT["spacing"])

        # 1. Tarjeta URL del Servidor
        layout_left.addWidget(self._create_url_card())
        
        # 2. Tarjeta Ruta de Archivos
        layout_left.addWidget(self._create_path_card())

        # 3. Tarjeta de Opciones (Derecha)
        card_options = self._create_options_card()

        container.addLayout(layout_left, stretch=1)
        container.addWidget(card_options)
        self.content_layout.addLayout(container)

    def _create_url_card(self) -> Card:
        card = Card(self)
        card.setFixedHeight(48)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.txt_url = QLineEdit(self.service.get_local_ip_url())
        self.txt_url.setReadOnly(True)
        self.txt_url.setStyleSheet(STYLES["input_readonly"])
        self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addWidget(self.txt_url, stretch=1)
        layout.addWidget(create_icon_btn("eye.svg", self._handle_toggle_eye))
        layout.addWidget(create_icon_btn("copy.svg", self._handle_copy_url))
        
        card.layout.addLayout(layout)
        return card

    def _create_path_card(self) -> Card:
        card = Card(self)
        card.setFixedHeight(48)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        current_path = self.service.get_media_folder() or "Sin carpeta seleccionada"
        self.lbl_path = QLabel(current_path)
        # Reutilizamos estilo de input pero adaptado a Label
        lbl_style = STYLES["input_readonly"].replace("QLineEdit", "QLabel") + "border:none; padding:0;"
        self.lbl_path.setStyleSheet(lbl_style)
        self.lbl_path.setWordWrap(False)

        layout.addWidget(self.lbl_path, stretch=1)
        layout.addWidget(create_icon_btn("folder.svg", self._handle_pick_folder))
        layout.addWidget(create_icon_btn("refresh-cw.svg", self.load_data))
        layout.addWidget(create_icon_btn("trash.svg", self._handle_clean_all, color_hover=THEME_DARK['status_error']))
        
        card.layout.addLayout(layout)
        return card

    def _create_options_card(self) -> Card:
        card = Card(self)
        card.setFixedWidth(180)
        card.setFixedHeight((48 * 2) + LAYOUT["spacing"]) # Altura basada en las dos cards de la izquierda
        
        title = QLabel("Ajustes Globales")
        title.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-weight: bold; font-size: 12px;")
        
        self.chk_rand = QCheckBox("Posición Aleatoria")
        self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_rand.setStyleSheet(get_switch_style())
        self.chk_rand.setChecked(self.service.db.get_bool("random_pos"))
        self.chk_rand.toggled.connect(self.service.set_random_pos)

        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)

        card.layout.addWidget(title)
        card.layout.addWidget(self.chk_rand)
        card.layout.addSpacing(5)
        card.layout.addWidget(self.chk_on)
        card.layout.addStretch()
        
        return card

    def _setup_toolbar(self):
        """Barra de búsqueda y filtros."""
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 10px; border: 1px solid {THEME_DARK['Black_N1']};")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(10)

        # Icono búsqueda
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("search.svg").pixmap(16, 16))
        icon_lbl.setStyleSheet("border:none; opacity:0.5;")
        
        # Input búsqueda
        self.inp_search = create_styled_input("Buscar archivo.", is_cmd=False, callback=self._handle_search_changed)

        # Filtro ComboBox
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
        """Contenedor para las MediaCards usando FlowLayout."""
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
            # Extracción de datos
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            # Lógica de Filtrado
            if search_term and (search_term not in fname) and (search_term not in cmd):
                continue
            
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            # Creación de Card
            card = MediaCard(item["filename"], item["type"], item["config"], self)
            self.media_layout.addWidget(card)
            count += 1

        # Estado vacío
        if count == 0:
            self._show_empty_state()

    def _show_empty_state(self):
        lbl = QLabel("No se encontraron archivos multimedia.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #666; margin-top: 20px;")
        self.media_layout.addWidget(lbl)

    def check_filter_refresh(self):
        """
        Si hay un filtro activo (que no sea 'Todos' ni tipos de archivo)
        """
        # Si estamos filtrando por estado (Activos/Desactivados), recargamos la grilla
        if self.filter_mode in ["Activos", "Desactivados"]:
            self._render_grid()

    # =========================================================================
    # SECCIÓN 3: MANEJADORES DE EVENTOS (HANDLERS)
    # =========================================================================
    def _handle_toggle_global(self, checked: bool):
        self.service.set_overlay_active(checked)
        status = "Activado" if checked else "Desactivado"
        ToastNotification(self, "Overlay", status, "info").show_toast()
    
    def _handle_clean_all(self):
        if ModalConfirm(self, "Borrar Todo", "Se eliminarán todas las configuraciones.").exec():
            self.service.clear_all_data()
            self.load_data()

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

    def handle_command_update(self, filename: str, new_cmd: str):
        """
        Maneja la lógica de negocio para comandos:
        1. Si está vacío -> Desactiva la carta actual.
        2. Si el comando ya existe en otra carta -> Desactiva la OTRA carta (para evitar duplicados).
        """
        new_cmd = new_cmd.strip()
        
        # Referencia al item actual en la lista local
        current_item = next((x for x in self.full_media_list if x["filename"] == filename), None)
        if not current_item: return

        # Regla 1: Si no hay comando, desactivar y guardar
        if not new_cmd:
            current_item["config"]["cmd"] = ""
            current_item["config"]["active"] = 0
            self.save_item(filename, current_item["type"], current_item["config"], silent=True)
            self._refresh_all_cards_ui() # Refrescar visualmente
            return

        # Regla 2: Buscar duplicados y desactivar el anterior
        found_duplicate = False
        for item in self.full_media_list:
            # Si es otro archivo Y tiene el mismo comando
            if item["filename"] != filename and item["config"].get("cmd") == new_cmd:
                item["config"]["active"] = 0 # Desactivamos el "viejo" dueño del comando
                # Guardamos el cambio en la base de datos para el item desactivado
                self.service.save_trigger(item["filename"], item["type"], item["config"])
                found_duplicate = True

        # Actualizar el item actual
        current_item["config"]["cmd"] = new_cmd
        self.save_item(filename, current_item["type"], current_item["config"], silent=True)

        # Si hubo cambios en otros items (duplicados) o el propio, refrescamos la UI
        if found_duplicate or not current_item["config"].get("active"):
            self._refresh_all_cards_ui()
            
            if found_duplicate:
                ToastNotification(self, "Comando Reasignado", f"El comando '{new_cmd}' fue quitado de otra carta.", "info").show_toast()

    def _refresh_all_cards_ui(self):
        """
        Itera sobre los widgets existentes y actualiza su estado visual
        """
        for i in range(self.media_layout.count()):
            widget = self.media_layout.itemAt(i).widget()
            if hasattr(widget, 'refresh_state_from_config'):
                # Buscamos la config actualizada en la lista
                item_data = next((x for x in self.full_media_list if x["filename"] == widget.filename), None)
                if item_data:
                    widget.refresh_state_from_config(item_data["config"])
    # =========================================================================
    # SECCIÓN 4: API PÚBLICA (USADA POR HIJOS/EXTERNOS)
    # =========================================================================
    def save_item(self, filename: str, ftype: str, data: dict, silent: bool = False):
        """Callback llamado por MediaCard para guardar configuraciones individuales."""
        success, msg = self.service.save_trigger(filename, ftype, data)
        
        if not silent:
            type_msg = "status_success" if success else "status_error"
            title = "Guardado" if success else "Error"
            ToastNotification(self, title, msg, type_msg).show_toast()
        
        # Actualizar memoria local para evitar recarga completa de DB
        for item in self.full_media_list:
            if item["filename"] == filename:
                item["config"] = data 
                break

    def preview_item(self, filename: str, ftype: str, config: dict):
        """Callback llamado por MediaCard para previsualizar alertas."""
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior para probar.", "status_warning").show_toast()
        
        self.service.preview_media(filename, ftype, config)