# ui/pages/overlay_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QApplication, QFileDialog, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer

from ui.components.cards import Card
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.components.media_item_widget import MediaItemWidget
from ui.factories import create_nav_btn, create_page_header, create_styled_input
from ui.utils import get_icon
from ui.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from backend.services.overlay_service import OverlayService

class OverlayPage(QWidget):
    def __init__(self, server_worker, db_handler, parent=None):
        super().__init__(parent)
        self.service = OverlayService(db_handler, server_worker)
        self.full_media_list = [] 
        self.search_text = ""
        self.filter_mode = "Todos"
        self.init_ui()

        # Cargar lista con un ligero retraso
        QTimer.singleShot(100, self.load_data)

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(layout)
        self._setup_config_section(layout)
        self._setup_toolbar(layout)
        self._setup_media_list(layout)

    def _setup_header(self, layout):
        h_head = QHBoxLayout()
        
        # Títulos
        v_titles = QVBoxLayout()
        v_titles.addWidget(create_page_header("Control de Triggers", "Configura tus alertas visuales y sonoras."))
        h_head.addLayout(v_titles)
        h_head.addStretch()

        # Botones Exportar/Importar (Los switches se movieron abajo)
        btn_import = create_nav_btn("Importar", "upload.svg", self._handle_import)
        btn_export = create_nav_btn("Exportar", "download.svg", self._handle_export)
        
        h_head.addWidget(btn_import)
        h_head.addWidget(btn_export)

        layout.addLayout(h_head)

    def _setup_config_section(self, layout):
        """
        Organiza las tarjetas en dos columnas, alineadas arriba y con la misma altura total.
        """
        # --- 1. DEFINIR ALTURAS ---
        card_height = 48 
        right_height = (card_height * 2) + LAYOUT["spacing"]

        h_container = QHBoxLayout()
        h_container.setSpacing(LAYOUT["spacing"])
        
        # --- COLUMNA IZQUIERDA ---
        v_left = QVBoxLayout()
        v_left.setSpacing(LAYOUT["spacing"])

        # Card URL OBS
        c_url = Card(self)
        c_url.setFixedHeight(card_height)
        
        l_url = QHBoxLayout()
        l_url.setContentsMargins(0,0,0,0)
        self.txt_url = QLineEdit(self.service.get_local_ip_url())
        self.txt_url.setReadOnly(True)
        self.txt_url.setStyleSheet(STYLES["input_readonly"])
        self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
        
        btn_eye = QPushButton()
        btn_eye.setIcon(get_icon("eye.svg"))
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.clicked.connect(self._handle_toggle_eye)
        
        btn_copy = QPushButton("Copiar")
        btn_copy.setIcon(get_icon("copy.svg"))
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._handle_copy_url)
        
        l_url.addWidget(self.txt_url, stretch=1)
        l_url.addWidget(btn_eye)
        l_url.addWidget(btn_copy)
        c_url.layout.addLayout(l_url)
        
        # Card Carpeta Multimedia
        c_dir = Card(self)
        c_dir.setFixedHeight(card_height)

        l_dir = QHBoxLayout()
        l_dir.setContentsMargins(0,0,0,0)
        
        current_path = self.service.get_media_folder() or "Sin carpeta seleccionada"
        self.lbl_path = QLabel(current_path)
        self.lbl_path.setWordWrap(False)
        self.lbl_path.setStyleSheet("color: #aaa; font-style: italic;")
        
        btn_f = self._create_tool_btn("folder.svg", self._handle_pick_folder, "Elegir Carpeta")
        btn_r = self._create_tool_btn("refresh-cw.svg", self.load_data, "Recargar Lista")
        btn_x = self._create_tool_btn("trash.svg", self._handle_clean_all, "Limpiar Configuración")
        btn_x.setStyleSheet("QPushButton:hover { background-color: #FF453A; border: 1px solid #FF453A; }")

        l_dir.addWidget(self.lbl_path, stretch=1)
        l_dir.addWidget(btn_f)
        l_dir.addWidget(btn_r)
        l_dir.addWidget(btn_x)
        c_dir.layout.addLayout(l_dir)

        v_left.addWidget(c_url)
        v_left.addWidget(c_dir)

        # --- COLUMNA DERECHA ---
        c_opts = Card(self)
        c_opts.setFixedWidth(180)
        c_opts.setFixedHeight(right_height)
        
        lbl_opts = QLabel("Ajustes Globales")
        lbl_opts.setStyleSheet(f"color: {THEME_DARK['Gray_N2']}; font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        c_opts.layout.addWidget(lbl_opts)

        # Switch Random
        self.chk_rand = QCheckBox("Posición Aleatoria")
        self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_rand.setStyleSheet(get_switch_style())
        self.chk_rand.setChecked(self.service.db.get_bool("random_pos"))
        self.chk_rand.toggled.connect(self.service.set_random_pos)
        c_opts.layout.addWidget(self.chk_rand)

        c_opts.layout.addSpacing(LAYOUT["spacing"])

        # Switch Active
        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)
        c_opts.layout.addWidget(self.chk_on)
        
        c_opts.layout.addStretch() 

        h_container.addLayout(v_left, stretch=1) 
        h_container.addWidget(c_opts, stretch=0, alignment=Qt.AlignmentFlag.AlignTop) 
        
        layout.addLayout(h_container)

    def _setup_toolbar(self, layout):
        """Barra con buscador y filtros."""
        bar = QFrame()
        bar.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 10px; ")
        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(*LAYOUT["margins"])
        h_bar.setSpacing(LAYOUT["spacing"])

        # Icono Lupa
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon("search.svg").pixmap(16,16))
        lbl_icon.setStyleSheet("opacity: 0.5; border:none;")
        h_bar.addWidget(lbl_icon)

        # Input Buscador
        self.inp_search = create_styled_input("Buscar archivo...", is_cmd=False, callback=self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        # Label Filtro
        lbl_filter = QLabel("Filtrar:", objectName="normal")
        lbl_filter.setStyleSheet("border: none; background: transparent;")
        h_bar.addWidget(lbl_filter)
        
        # Combo Box
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"])
        self.combo_filter.addItems(["Todos", "Activos", "Desactivados", "Video", "Audio"])
        self.combo_filter.setFixedWidth(130)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)

        layout.addWidget(bar)

    def _setup_media_list(self, layout):
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(STYLES["list_clean"])
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.list_widget)

    # ==========================================
    # 2. LÓGICA DE NEGOCIO (Igual que antes)
    # ==========================================
    def load_data(self):
        self.full_media_list = self.service.get_media_files_with_config()
        self.render_list()

    def render_list(self):
        self.list_widget.clear()
        
        for item in self.full_media_list:
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            # Filtros
            if self.search_text:
                if (self.search_text not in fname) and (self.search_text not in cmd):
                    continue
            
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            # Dibujar
            w_item = QListWidgetItem(self.list_widget)
            w_item.setSizeHint(QSize(0, 70))
            
            widget = MediaItemWidget(item["filename"], item["type"], item["config"], self)
            self.list_widget.setItemWidget(w_item, widget)
    
    def save_item(self, filename, ftype, data, silent=False):
        # Sanitización y guardado
        raw_cmd = data.get("cmd", "").strip()
        if raw_cmd:
            raw_cmd = raw_cmd.replace(" ", "_")
            if not raw_cmd.startswith("!"): raw_cmd = "!" + raw_cmd
            data["cmd"] = raw_cmd.lower()

        new_cmd = data["cmd"]
        # Validación duplicados
        if new_cmd:
            for item in self.full_media_list:
                existing_file = item["filename"]
                existing_config = item["config"]
                existing_cmd = existing_config.get("cmd", "").lower()
                
                if existing_file != filename and existing_cmd == new_cmd:
                    msg = (f"El comando '{new_cmd}' ya se usa en: {existing_file}.\n\n"
                           "Si continúas, el otro archivo perderá este comando.\n"
                           "¿Deseas sobrescribirlo?")
                    if not ModalConfirm(self, "⚠️ Comando Duplicado", msg).exec():
                        self.load_data()
                        return False 
                    existing_config["cmd"] = ""
                    existing_config["active"] = 0
                    break 

        success, msg = self.service.save_trigger(filename, ftype, data)
        if not silent:
            type_msg = "Status_Green" if success else "Status_Red"
            ToastNotification(self, "Guardado" if success else "Error", msg, type_msg).show_toast()
        
        for item in self.full_media_list:
            if item["filename"] == filename:
                item["config"] = data 
                break
        self.render_list()
        return success

    def preview_item(self, filename, ftype, config):
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior derecho.", "Status_Yellow").show_toast()
        self.service.preview_media(filename, ftype, config)

    # ==========================================
    # 3. HANDLERS (EVENTOS)
    # ==========================================
    def _handle_toggle_global(self, checked):
        self.service.set_overlay_active(checked)
        ToastNotification(self, "Overlay", "Activado" if checked else "Desactivado", "info").show_toast()

    def _handle_clean_all(self):
        if ModalConfirm(self, "Borrar Todo", "Se eliminarán todas las configuraciones de alertas.").exec():
            self.service.clear_all_data()
            self.load_data()
            ToastNotification(self, "Limpieza", "Configuración reseteada", "Status_Green").show_toast()

    def _handle_pick_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta Media")
        if f:
            self.service.set_media_folder(f)
            self.lbl_path.setText(f)
            self.load_data()

    def _handle_copy_url(self):
        QApplication.clipboard().setText(self.txt_url.text())
        ToastNotification(self, "Copiado", "URL lista para pegar en OBS", "Status_Green").show_toast()

    def _handle_toggle_eye(self):
        if self.txt_url.echoMode() == QLineEdit.EchoMode.Normal:
            self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
            self.sender().setIcon(get_icon("eye.svg"))
        else:
            self.txt_url.setEchoMode(QLineEdit.EchoMode.Normal)
            self.sender().setIcon(get_icon("eye-off.svg"))

    def _handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Alertas", "alertas_backup.csv", "CSV Files (*.csv)")
        if not path: return
        
        # El servicio ahora usa DataManager para escribir limpiamente
        if self.service.export_csv(path):
            ToastNotification(self, "Exportado", "Configuración guardada exitosamente.", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo guardar el archivo.", "Status_Red").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Alertas", "", "CSV Files (*.csv)")
        if not path: return
        
        if not ModalConfirm(self, "Importar", "Esto sobrescribirá comandos existentes. ¿Continuar?").exec():
            return
            
        # El servicio retorna: (ok, fail, lista_errores_o_faltantes)
        ok, fail, missing_list = self.service.import_csv(path) 
        self.load_data()
        
        # CASO 1: Archivo Inválido (DataManager devolvió error en la lista y 0 importados)
        # Esto ocurre si subes el CSV de puntos en lugar del de overlay
        if ok == 0 and fail == 0 and missing_list:
             error_msg = missing_list[0] # El mensaje del DataManager
             ToastNotification(self, "Archivo Incorrecto", error_msg, "Status_Red").show_toast()
             return

        # CASO 2: Archivos Multimedia Faltantes (La importación funcionó, pero faltan archivos)
        if missing_list:
             limit_show = 5
             files_str = "\n- ".join(missing_list[:limit_show])
             if len(missing_list) > limit_show: 
                 files_str += f"\n... y {len(missing_list)-limit_show} más."
             
             ModalConfirm(self, "Archivos Faltantes", f"Se cargó la config, pero NO encuentro estos archivos en la carpeta:\n\n- {files_str}").exec()
             
        # Notificación Final
        if ok > 0:
            type_msg = "Status_Green" if fail == 0 else "Status_Yellow"
            ToastNotification(self, "Éxito", f"Se importaron {ok} alertas. (Ignorados: {fail})", type_msg).show_toast()
        elif fail > 0 and ok == 0:
            ToastNotification(self, "Error", "No se pudo importar ninguna alerta válida.", "Status_Red").show_toast()

    def _handle_search_changed(self, text):
        self.search_text = text.lower().strip()
        self.render_list()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self.render_list()

    # Helpers
    def _create_tool_btn(self, icon, func, tooltip):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        return btn

    def _create_top_btn(self, icon, text, func):
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(STYLES["btn_nav"])
        btn.clicked.connect(func)
        return btn