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
from ui.utils import get_icon
from ui.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from backend.services.overlay_service import OverlayService

class OverlayPage(QWidget):
    def __init__(self, server_worker, db_handler, parent=None):
        super().__init__(parent)
        self.service = OverlayService(db_handler, server_worker)
        self.full_media_list = [] # Guardamos la lista completa aquí
        self.search_text = ""
        self.filter_mode = "Todos"
        self.init_ui()

        # Cargar lista con un ligero retraso para no bloquear el inicio de la app
        QTimer.singleShot(100, self.load_data)

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(layout)
        self._setup_info_cards(layout)
        self._setup_toolbar(layout)
        self._setup_media_list(layout)

    def _setup_header(self, layout):
        h_head = QHBoxLayout()
        
        # Títulos
        v_tit = QVBoxLayout()
        v_tit.setSpacing(2)
        v_tit.addWidget(QLabel("Control de Triggers", objectName="h2"))
        v_tit.addWidget(QLabel("Configura tus alertas visuales y sonoras.", objectName="subtitle"))
        h_head.addLayout(v_tit)
        
        h_head.addStretch()

        # Switches Globales
        self.chk_rand = QCheckBox("Posición Aleatoria")
        self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_rand.setStyleSheet(get_switch_style())
        self.chk_rand.setChecked(self.service.db.get_bool("random_pos"))
        self.chk_rand.toggled.connect(self.service.set_random_pos)
        h_head.addWidget(self.chk_rand)
        h_head.addSpacing(10)

        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)
        h_head.addWidget(self.chk_on)
        h_head.addSpacing(10)

        btn_export = self._create_top_btn("download.svg", "Exportar", self._handle_export)
        btn_import = self._create_top_btn("upload.svg", "Importar", self._handle_import)
        h_head.addWidget(btn_export)
        h_head.addWidget(btn_import)
        
        layout.addLayout(h_head)

    def _setup_info_cards(self, layout):
        h_cards = QHBoxLayout()

        # --- Card 1: URL para OBS ---
        c_url = Card(self)
        l_url = QHBoxLayout()
        l_url.setContentsMargins(0,0,0,0)
        
        self.txt_url = QLineEdit(self.service.get_local_ip_url())
        self.txt_url.setReadOnly(True)
        self.txt_url.setStyleSheet(STYLES["url_readonly"])
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
        h_cards.addWidget(c_url)

        # --- Card 2: Carpeta Multimedia ---
        c_dir = Card(self)
        l_dir = QHBoxLayout()
        l_dir.setContentsMargins(0,0,0,0)
        
        current_path = self.service.get_media_folder() or "Sin carpeta seleccionada"
        self.lbl_path = QLabel(current_path)
        self.lbl_path.setWordWrap(False)
        
        btn_f = self._create_tool_btn("folder.svg", self._handle_pick_folder, "Elegir Carpeta")
        btn_r = self._create_tool_btn("refresh-cw.svg", self.load_data, "Recargar Lista")
        btn_x = self._create_tool_btn("trash.svg", self._handle_clean_all, "Limpiar Configuración")
        btn_x.setStyleSheet("QPushButton:hover { background-color: #FF453A; border: 1px solid #FF453A; }")

        l_dir.addWidget(self.lbl_path, stretch=1)
        l_dir.addWidget(btn_f)
        l_dir.addWidget(btn_r)
        l_dir.addWidget(btn_x)
        c_dir.layout.addLayout(l_dir)
        h_cards.addWidget(c_dir)
        
        layout.addLayout(h_cards)

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
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Buscar archivo o comando...")
        self.inp_search.setStyleSheet(STYLES["input"])
        self.inp_search.textChanged.connect(self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        # Label Filtro
        lbl_filter = QLabel("Filtrar:", objectName="normal")
        lbl_filter.setStyleSheet("border: none; background: transparent;") # Aseguramos sin borde y fondo transparente
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
    # 2. LÓGICA DE NEGOCIO
    # ==========================================
    def load_data(self):
        """1. Carga datos del disco/DB a memoria."""
        self.full_media_list = self.service.get_media_files_with_config()
        self.render_list() # 2. Llama al renderizado

    def render_list(self):
        """2. Filtra los datos en memoria y dibuja la lista."""
        self.list_widget.clear()
        
        for item in self.full_media_list:
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            # --- FILTRO BÚSQUEDA ---
            if self.search_text:
                # Busca en nombre de archivo O en el comando
                if (self.search_text not in fname) and (self.search_text not in cmd):
                    continue
            
            # --- FILTRO COMBO ---
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            # --- DIBUJAR ---
            w_item = QListWidgetItem(self.list_widget)
            w_item.setSizeHint(QSize(0, 70))
            
            widget = MediaItemWidget(item["filename"], item["type"], item["config"], self)
            self.list_widget.setItemWidget(w_item, widget)
    
    def save_item(self, filename, ftype, data, silent=False):
        # ========================================================
        # 1. SANITIZACIÓN (Limpieza de entrada)
        # ========================================================
        raw_cmd = data.get("cmd", "").strip()
        
        if raw_cmd:
            # A. Reemplazar espacios por guiones bajos
            raw_cmd = raw_cmd.replace(" ", "_")
            
            # B. Agregar prefijo "!" si falta
            if not raw_cmd.startswith("!"):
                raw_cmd = "!" + raw_cmd
            
            # C. Guardamos la versión corregida en el diccionario 'data'
            data["cmd"] = raw_cmd.lower()

        # Usamos esta variable limpia para las comparaciones
        new_cmd = data["cmd"]

        # ========================================================
        # 2. VALIDACIÓN DE DUPLICADOS (Con comando ya limpio)
        # ========================================================
        if new_cmd:
            for item in self.full_media_list:
                existing_file = item["filename"]
                existing_config = item["config"]
                existing_cmd = existing_config.get("cmd", "").lower()
                
                # Chequeamos contra el comando ya limpio (!oh_my_god)
                if existing_file != filename and existing_cmd == new_cmd:
                    msg = (f"El comando '{new_cmd}' ya se usa en: {existing_file}.\n\n"
                           "Si continúas, el otro archivo perderá este comando.\n"
                           "¿Deseas sobrescribirlo?")
                    
                    if not ModalConfirm(self, "⚠️ Comando Duplicado", msg).exec():
                        # Si cancela, recargamos DB para borrar cambios visuales falsos
                        self.load_data()
                        return False 
                    
                    # Si acepta, borramos el comando del archivo "rival"
                    existing_config["cmd"] = ""
                    existing_config["active"] = 0
                    break 

        # ========================================================
        # 3. GUARDADO EN BASE DE DATOS
        # ========================================================
        success, msg = self.service.save_trigger(filename, ftype, data)
        
        if not silent:
            type_msg = "Status_Green" if success else "Status_Red"
            ToastNotification(self, "Guardado" if success else "Error", msg, type_msg).show_toast()
        
        # 4. Actualizar memoria (Lista local)
        for item in self.full_media_list:
            if item["filename"] == filename:
                item["config"] = data 
                break
        
        # 5. Refrescar la vista
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
        
        if self.service.export_csv(path):
            ToastNotification(self, "Exportado", "Configuración guardada exitosamente.", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo guardar el archivo.", "Status_Red").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Alertas", "", "CSV Files (*.csv)")
        if not path: return
        
        if not ModalConfirm(self, "Importar", "Esto sobrescribirá comandos existentes. ¿Continuar?").exec():
            return

        # Llamamos al servicio
        ok, fail, missing = self.service.import_csv(path)
        
        self.load_data()
        
        # --- AVISO INTELIGENTE DE ARCHIVOS FALTANTES ---
        if fail == 0 and not missing:
            ToastNotification(self, "Éxito", f"Se importaron {ok} alertas correctamente.", "Status_Green").show_toast()
        else:
            # Construimos un mensaje de advertencia
            if missing:
                limit_show = 5
                files_str = "\n- ".join(missing[:limit_show])
                if len(missing) > limit_show: files_str += f"\n... y {len(missing)-limit_show} más."
                
                # Mostramos un modal porque el toast es muy pequeño para la lista
                ModalConfirm(self, "Archivos Faltantes", 
                             f"La configuración se cargó, pero NO encuentro estos archivos en tu carpeta:\n\n- {files_str}").exec()
            
            ToastNotification(self, "Importación con Avisos", f"OK: {ok} | Errores: {fail}", "Status_Yellow").show_toast()

    def _handle_search_changed(self, text):
        self.search_text = text.lower().strip()
        self.render_list()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self.render_list()

    # Helpers de botones
    def _create_tool_btn(self, icon, func, tooltip):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        return btn

    def _create_top_btn(self, icon, text, func):
        """Botón con texto e icono para la cabecera."""
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N2']};
                color: {THEME_DARK['White_N1']};
                
                padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['Black_N4']}; 
                border-color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(func)
        return btn