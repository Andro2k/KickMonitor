# ui/pages/overlay_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QApplication, QFileDialog, QCheckBox, QFrame, 
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer

from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.components.media_item_widget import MediaItemWidget
from ui.utils import get_icon
from ui.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from services.overlay_service import OverlayService
from ui.components.flow_layout import FlowLayout # <--- IMPORTANTE

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
        # 1. SCROLL AREA PRINCIPAL
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # 2. FLOW LAYOUT
        self.flow_layout = FlowLayout(content, margin=LAYOUT["margins"][0], spacing=LAYOUT["spacing"])

        # 3. HEADER FIJO
        outer_layout.addWidget(self._create_header())

        # 4. CONSTRUIR TARJETAS
        self._setup_cards()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_header(self):
        h_frame = QFrame()
        h_head = QHBoxLayout(h_frame)
        h_head.setContentsMargins(*LAYOUT["margins"])
        
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
        h_head.addSpacing(15)

        self.chk_on = QCheckBox("Overlay Activo")
        self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_on.setStyleSheet(get_switch_style())
        self.chk_on.setChecked(self.service.is_overlay_active())
        self.chk_on.toggled.connect(self._handle_toggle_global)
        h_head.addWidget(self.chk_on)
        h_head.addSpacing(15)

        # Botones Export/Import
        btn_export = self._create_top_btn("download.svg", "Exportar", self._handle_export)
        btn_import = self._create_top_btn("upload.svg", "Importar", self._handle_import)
        h_head.addWidget(btn_export)
        h_head.addWidget(btn_import)
        
        return h_frame

    def _setup_cards(self):
        # TARJETA 1: OBS URL
        card_url = self._create_url_card()
        card_url.setMinimumWidth(350)
        card_url.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.flow_layout.addWidget(card_url)

        # TARJETA 2: DIRECTORIO
        card_dir = self._create_dir_card()
        card_dir.setMinimumWidth(350)
        card_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.flow_layout.addWidget(card_dir)

        # TARJETA 3: LISTA DE MEDIA (Grande)
        card_list = self._create_list_card()
        card_list.setMinimumWidth(600) # Ancho mínimo mayor para la lista
        card_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(card_list)

    # ==========================================
    # CREADORES DE TARJETAS
    # ==========================================
    def _create_url_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card"])
        l = QVBoxLayout(card)
        l.setContentsMargins(15, 15, 15, 15)
        
        l.addWidget(QLabel("Conexión OBS (Browser Source)", styleSheet="color:#aaa; font-weight:bold; font-size:11px;"))
        
        row = QHBoxLayout()
        self.txt_url = QLineEdit(self.service.get_local_ip_url())
        self.txt_url.setReadOnly(True)
        self.txt_url.setStyleSheet(STYLES["url_readonly"])
        self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
        
        btn_eye = QPushButton()
        btn_eye.setIcon(get_icon("eye.svg"))
        btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eye.setStyleSheet("background:transparent; border:none;")
        btn_eye.clicked.connect(self._handle_toggle_eye)
        
        btn_copy = QPushButton("Copiar")
        btn_copy.setIcon(get_icon("copy.svg"))
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"background-color:{THEME_DARK['Black_N4']}; border-radius:6px; padding:4px 8px;")
        btn_copy.clicked.connect(self._handle_copy_url)
        
        row.addWidget(self.txt_url)
        row.addWidget(btn_eye)
        row.addWidget(btn_copy)
        l.addLayout(row)
        return card

    def _create_dir_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card"])
        l = QVBoxLayout(card)
        l.setContentsMargins(15, 15, 15, 15)

        l.addWidget(QLabel("Carpeta Multimedia", styleSheet="color:#aaa; font-weight:bold; font-size:11px;"))
        
        row = QHBoxLayout()
        current_path = self.service.get_media_folder() or "Sin carpeta seleccionada"
        self.lbl_path = QLabel(current_path)
        self.lbl_path.setStyleSheet(f"color:{THEME_DARK['NeonGreen_Main']}; font-family:Consolas;")
        self.lbl_path.setWordWrap(False) # Cortar si es muy largo
        
        btn_f = self._create_tool_btn("folder.svg", self._handle_pick_folder, "Elegir Carpeta")
        btn_r = self._create_tool_btn("refresh-cw.svg", self.load_data, "Recargar Lista")
        btn_x = self._create_tool_btn("trash.svg", self._handle_clean_all, "Limpiar Configuración")
        btn_x.setStyleSheet("QPushButton:hover { background-color: #FF453A; border: 1px solid #FF453A; }")

        row.addWidget(self.lbl_path, stretch=1)
        row.addWidget(btn_f)
        row.addWidget(btn_r)
        row.addWidget(btn_x)
        l.addLayout(row)
        return card

    def _create_list_card(self):
        card = QFrame()
        card.setStyleSheet(STYLES["card"])
        l = QVBoxLayout(card)
        l.setContentsMargins(0, 0, 0, 0) # Sin margen para que la barra de herramientas toque los bordes
        l.setSpacing(0)

        # 1. TOOLBAR INTERNA
        toolbar = QFrame()
        toolbar.setStyleSheet(f"border-bottom: 1px solid {THEME_DARK['Black_N4']}; background: transparent;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(15, 10, 15, 10)
        tb_layout.setSpacing(10)

        lbl_search = QLabel(); lbl_search.setPixmap(get_icon("search.svg").pixmap(16,16)); lbl_search.setStyleSheet("opacity:0.5; border:none;")
        tb_layout.addWidget(lbl_search)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Buscar archivo o comando...")
        self.inp_search.setStyleSheet("background:transparent; border:none; color:white;")
        self.inp_search.textChanged.connect(self._handle_search_changed)
        tb_layout.addWidget(self.inp_search, stretch=1)
        
        tb_layout.addWidget(QLabel("|", styleSheet="color:#444;"))
        
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["Todos", "Activos", "Desactivados", "Video", "Audio"])
        self.combo_filter.setFixedWidth(120)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.setStyleSheet(STYLES["combobox"].replace(f"background-color: {THEME_DARK['Black_N2']}", "background-color: transparent"))
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        tb_layout.addWidget(self.combo_filter)
        
        l.addWidget(toolbar)

        # 2. LISTA
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(STYLES["list_clean"] + "QListWidget { border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; }")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setMinimumHeight(400) # Altura mínima
        l.addWidget(self.list_widget)

        return card

    # ==========================================
    # 2. LÓGICA DE NEGOCIO (IGUAL)
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

            if self.search_text:
                if (self.search_text not in fname) and (self.search_text not in cmd): continue
            
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            w_item = QListWidgetItem(self.list_widget)
            w_item.setSizeHint(QSize(0, 70))
            
            widget = MediaItemWidget(item["filename"], item["type"], item["config"], self)
            self.list_widget.setItemWidget(w_item, widget)
    
    def save_item(self, filename, ftype, data, silent=False):
        raw_cmd = data.get("cmd", "").strip()
        if raw_cmd:
            raw_cmd = raw_cmd.replace(" ", "_")
            if not raw_cmd.startswith("!"): raw_cmd = "!" + raw_cmd
            data["cmd"] = raw_cmd.lower()

        new_cmd = data["cmd"]

        if new_cmd:
            for item in self.full_media_list:
                existing_file = item["filename"]
                existing_config = item["config"]
                existing_cmd = existing_config.get("cmd", "").lower()
                
                if existing_file != filename and existing_cmd == new_cmd:
                    msg = (f"El comando '{new_cmd}' ya se usa en: {existing_file}.\n\n"
                           "¿Deseas sobrescribirlo?")
                    if not ModalConfirm(self, "⚠️ Comando Duplicado", msg).exec():
                        self.load_data()
                        return False 
                    existing_config["cmd"] = ""; existing_config["active"] = 0
                    break 

        success, msg = self.service.save_trigger(filename, ftype, data)
        if not silent:
            type_msg = "Status_Green" if success else "Status_Red"
            ToastNotification(self, "Guardado" if success else "Error", msg, type_msg).show_toast()
        
        for item in self.full_media_list:
            if item["filename"] == filename: item["config"] = data; break
        
        self.render_list()
        return success

    def preview_item(self, filename, ftype, config):
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior.", "Status_Yellow").show_toast()
        self.service.preview_media(filename, ftype, config)

    # ==========================================
    # HANDLERS
    # ==========================================
    def _handle_toggle_global(self, checked):
        self.service.set_overlay_active(checked)
        ToastNotification(self, "Overlay", "Activado" if checked else "Desactivado", "info").show_toast()

    def _handle_clean_all(self):
        if ModalConfirm(self, "Borrar Todo", "Se eliminarán todas las configuraciones.").exec():
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
            ToastNotification(self, "Exportado", "Configuración guardada.", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo guardar.", "Status_Red").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Alertas", "", "CSV Files (*.csv)")
        if not path: return
        if not ModalConfirm(self, "Importar", "¿Sobrescribir configuración actual?").exec(): return

        ok, fail, missing = self.service.import_csv(path)
        self.load_data()
        
        if fail == 0 and not missing:
            ToastNotification(self, "Éxito", f"Importados: {ok}", "Status_Green").show_toast()
        else:
            if missing:
                files_str = "\n- ".join(missing[:5])
                if len(missing) > 5: files_str += f"\n... y {len(missing)-5} más."
                ModalConfirm(self, "Archivos Faltantes", f"No encontrados en carpeta:\n\n- {files_str}").exec()
            ToastNotification(self, "Avisos", f"OK: {ok} | Error: {fail}", "Status_Yellow").show_toast()

    def _handle_search_changed(self, text):
        self.search_text = text.lower().strip()
        self.render_list()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self.render_list()

    def _create_tool_btn(self, icon, func, tooltip):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("background:transparent; border:none;") # Estilo base limpio
        btn.clicked.connect(func)
        return btn

    def _create_top_btn(self, icon, text, func):
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N3']}; color: {THEME_DARK['White_N1']};
                padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;
                border: 1px solid {THEME_DARK['Black_N4']};
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['Black_N4']}; border-color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(func)
        return btn