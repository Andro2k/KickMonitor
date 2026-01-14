from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QLineEdit, QPushButton, QApplication, QFileDialog, 
    QCheckBox, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer

from ui.components.cards import Card
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.factories import create_nav_btn, create_page_header, create_styled_input, create_icon_btn
from ui.utils import get_icon
from ui.theme import LAYOUT, STYLES, THEME_DARK, get_switch_style
from backend.services.overlay_service import OverlayService
from ui.components.flow_layout import FlowLayout 
from ui.components.media_card import MediaCard

class OverlayPage(QWidget):
    def __init__(self, server_worker, db_handler, parent=None):
        super().__init__(parent)
        self.service = OverlayService(db_handler, server_worker)
        self.full_media_list = [] 
        self.search_text = ""
        self.filter_mode = "Todos"
        self.init_ui()
        QTimer.singleShot(100, self.load_data)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(*LAYOUT["margins"])
        self.content_layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(self.content_layout)
        self._setup_config_section(self.content_layout)
        self._setup_toolbar(self.content_layout)
        self._setup_media_grid(self.content_layout)

        self.scroll.setWidget(content)
        layout.addWidget(self.scroll)
    
    def _setup_media_grid(self, layout):
        self.media_container = QWidget()
        self.media_container.setStyleSheet("background: transparent;")
        self.media_layout = FlowLayout(self.media_container, margin=0, spacing=10)
        layout.addWidget(self.media_container)
        
    def load_data(self):
        self.full_media_list = self.service.get_media_files_with_config()
        self.render_grid()

    def render_grid(self):
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        count = 0
        for item in self.full_media_list:
            fname = item["filename"].lower()
            cmd = item["config"].get("cmd", "").lower()
            ftype = item["type"]
            is_active = bool(item["config"].get("active", 0))

            if self.search_text and (self.search_text not in fname) and (self.search_text not in cmd): continue
            if self.filter_mode == "Activos" and not is_active: continue
            if self.filter_mode == "Desactivados" and is_active: continue
            if self.filter_mode == "Video" and ftype != "video": continue
            if self.filter_mode == "Audio" and ftype != "audio": continue

            card = MediaCard(item["filename"], item["type"], item["config"], self)
            self.media_layout.addWidget(card)
            count += 1

        if count == 0:
            lbl = QLabel("No se encontraron archivos multimedia.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #666; margin-top: 20px;")
            self.media_layout.addWidget(lbl)

    # --- Public Methods (For MediaCard) ---
    def save_item(self, filename, ftype, data, silent=False):
        success, msg = self.service.save_trigger(filename, ftype, data)
        if not silent:
            type_msg = "Status_Green" if success else "Status_Red"
            ToastNotification(self, "Guardado" if success else "Error", msg, type_msg).show_toast()
        
        for item in self.full_media_list:
            if item["filename"] == filename:
                item["config"] = data 
                break

    def preview_item(self, filename, ftype, config):
        if not self.chk_on.isChecked():
            return ToastNotification(self, "Overlay Apagado", "Activa el switch superior.", "Status_Yellow").show_toast()
        self.service.preview_media(filename, ftype, config)

    # --- Handlers ---
    def _handle_toggle_global(self, checked):
        self.service.set_overlay_active(checked)
        ToastNotification(self, "Overlay", "Activado" if checked else "Desactivado", "info").show_toast()
    
    def _handle_clean_all(self):
        if ModalConfirm(self, "Borrar Todo", "Se eliminarán todas las configuraciones.").exec():
            self.service.clear_all_data(); self.load_data()

    def _handle_pick_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if f: self.service.set_media_folder(f); self.lbl_path.setText(f); self.load_data()

    def _handle_copy_url(self):
        QApplication.clipboard().setText(self.txt_url.text())
        ToastNotification(self, "Copiado", "URL copiada", "Status_Green").show_toast()

    def _handle_toggle_eye(self):
        mode = QLineEdit.EchoMode.Password if self.txt_url.echoMode() == QLineEdit.EchoMode.Normal else QLineEdit.EchoMode.Normal
        self.txt_url.setEchoMode(mode)

    def _handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", "alertas.csv", "CSV Files (*.csv)")
        if path and self.service.export_csv(path): 
            ToastNotification(self, "Éxito", "Exportado correctamente", "Status_Green").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar", "", "CSV Files (*.csv)")
        if not path or not ModalConfirm(self, "Importar", "¿Sobrescribir configuración?").exec(): return
        ok, fail, missing = self.service.import_csv(path); self.load_data()
        if missing: ModalConfirm(self, "Faltantes", "\n".join(missing[:5])).exec()
        ToastNotification(self, "Importación", f"OK: {ok} | Fail: {fail}", "Status_Green").show_toast()

    def _handle_search_changed(self, text):
        self.search_text = text.lower().strip(); self.render_grid()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText(); self.render_grid()

    # --- UI Setup Helpers ---
    def _setup_header(self, layout):
        h = QHBoxLayout()
        h.addWidget(create_page_header("Control de Triggers", "Configura tus alertas visuales y sonoras."))
        h.addStretch()
        h.addWidget(create_nav_btn("Importar", "upload.svg", self._handle_import))
        h.addWidget(create_nav_btn("Exportar", "download.svg", self._handle_export))
        layout.addLayout(h)

    def _setup_config_section(self, layout):
        card_h = 48
        h_cont = QHBoxLayout(); h_cont.setSpacing(LAYOUT["spacing"])
        v_left = QVBoxLayout(); v_left.setSpacing(LAYOUT["spacing"])

        # Card URL
        c_url = Card(self); c_url.setFixedHeight(card_h)
        l_url = QHBoxLayout(); l_url.setContentsMargins(0,0,0,0)
        self.txt_url = QLineEdit(self.service.get_local_ip_url()); self.txt_url.setReadOnly(True); self.txt_url.setStyleSheet(STYLES["input_readonly"]); self.txt_url.setEchoMode(QLineEdit.EchoMode.Password)
        l_url.addWidget(self.txt_url, stretch=1); l_url.addWidget(create_icon_btn("eye.svg", self._handle_toggle_eye)); l_url.addWidget(create_icon_btn("copy.svg", self._handle_copy_url))
        c_url.layout.addLayout(l_url)
        
        # Card Path
        c_dir = Card(self); c_dir.setFixedHeight(card_h)
        l_dir = QHBoxLayout(); l_dir.setContentsMargins(0,0,0,0)
        self.lbl_path = QLabel(self.service.get_media_folder() or "Sin carpeta"); self.lbl_path.setStyleSheet(STYLES["input_readonly"].replace("QLineEdit", "QLabel") + "border:none; padding:0;"); self.lbl_path.setWordWrap(False)
        l_dir.addWidget(self.lbl_path, stretch=1); l_dir.addWidget(create_icon_btn("folder.svg", self._handle_pick_folder)); l_dir.addWidget(create_icon_btn("refresh-cw.svg", self.load_data)); l_dir.addWidget(create_icon_btn("trash.svg", self._handle_clean_all, color_hover=THEME_DARK['Status_Red']))
        c_dir.layout.addLayout(l_dir)

        v_left.addWidget(c_url); v_left.addWidget(c_dir)

        # Card Options
        c_opts = Card(self); c_opts.setFixedWidth(180); c_opts.setFixedHeight((card_h * 2) + LAYOUT["spacing"])
        c_opts.layout.addWidget(QLabel("Ajustes Globales", styleSheet=f"color: {THEME_DARK['Gray_N2']}; font-weight: bold; font-size: 12px;"))
        self.chk_rand = QCheckBox("Posición Aleatoria"); self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor); self.chk_rand.setStyleSheet(get_switch_style()); self.chk_rand.setChecked(self.service.db.get_bool("random_pos")); self.chk_rand.toggled.connect(self.service.set_random_pos)
        c_opts.layout.addWidget(self.chk_rand)
        c_opts.layout.addSpacing(5)
        self.chk_on = QCheckBox("Overlay Activo"); self.chk_on.setCursor(Qt.CursorShape.PointingHandCursor); self.chk_on.setStyleSheet(get_switch_style()); self.chk_on.setChecked(self.service.is_overlay_active()); self.chk_on.toggled.connect(self._handle_toggle_global)
        c_opts.layout.addWidget(self.chk_on); c_opts.layout.addStretch()

        h_cont.addLayout(v_left, stretch=1); h_cont.addWidget(c_opts)
        layout.addLayout(h_cont)

    def _setup_toolbar(self, layout):
        bar = QFrame(); bar.setFixedHeight(60)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 10px; border: 1px solid {THEME_DARK['Black_N1']};")

        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(*LAYOUT["margins"]); h_bar.setSpacing(10)
        h_bar.addWidget(QLabel(pixmap=get_icon("search.svg").pixmap(16,16), styleSheet="border:none; opacity:0.5;"))
        self.inp_search = create_styled_input("Buscar archivo...", is_cmd=False, callback=self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        h_bar.addWidget(QLabel("Filtrar:", styleSheet="border:none; color:#888;"))
        self.combo_filter = QComboBox(); self.combo_filter.setStyleSheet(STYLES["combobox"])
        self.combo_filter.addItems(["Todos", "Activos", "Desactivados", "Video", "Audio"])
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)
        layout.addWidget(bar)