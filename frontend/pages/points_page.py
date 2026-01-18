# frontend/pages/points_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QCheckBox, QAbstractItemView, 
    QLineEdit, QComboBox, QFrame, QFileDialog,
    QScrollArea, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer

# --- IMPORTS DE FACTORÍAS ---
from frontend.factories import (
    create_icon_btn, 
    create_nav_btn, 
    create_page_header, 
    create_styled_input, 
    create_switch_widget
)
from frontend.theme import LAYOUT, THEME_DARK, STYLES
from frontend.utils import get_icon, get_icon_colored
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from backend.services.points_service import PointsService

class PointsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = PointsService(db_handler)
        
        self.search_text = ""
        self.filter_mode = "Todos"
        
        # Auto-refresh cada 10s
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(10000) 
        
        self.init_ui()
        self.load_table_data()

    def init_ui(self):
        # 1. LAYOUT PRINCIPAL (Scroll Vertical)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        # 2. CONTENEDOR INTERNO
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(*LAYOUT["margins"])
        self.content_layout.setSpacing(LAYOUT["spacing"])

        # 3. CONSTRUCCIÓN DE LA UI
        # A. Header
        self.content_layout.addWidget(self._create_header()) 
        # B. Barra de Gestión Manual
        self.content_layout.addWidget(self._create_manual_strip())
        # C. Tabla de Usuarios
        self.content_layout.addWidget(self._create_table_card())
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_header(self):
        """Crea la cabecera usando factories."""
        h_frame = QFrame()
        h_header = QHBoxLayout(h_frame)
        h_header.setContentsMargins(0, 0, 0, 0)
        
        # Título desde factory
        h_header.addWidget(create_page_header("Tabla de Usuarios", "Gestión de puntos y estado."))
        h_header.addStretch()
        
        # Botones de navegación desde factory
        btn_import = create_nav_btn("Importar", "upload.svg", self._handle_import_csv)
        btn_export = create_nav_btn("Exportar", "download.svg", self._handle_export_csv)
        
        h_header.addWidget(btn_import)       
        h_header.addWidget(btn_export)
        
        return h_frame

    def _create_manual_strip(self):
        """Barra horizontal para agregar/quitar puntos manualmente."""
        card = QFrame()
        card.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QHBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        # Inputs
        l.addWidget(QLabel("Usuario:", styleSheet="color:#888; font-weight:bold; "))
        
        self.inp_manual_user = QLineEdit()
        self.inp_manual_user.setPlaceholderText("Ej: damir")
        self.inp_manual_user.setFixedWidth(150)
        self.inp_manual_user.setStyleSheet(STYLES["input_readonly"])
        l.addWidget(self.inp_manual_user)

        l.addWidget(QLabel("Puntos:", styleSheet="color:#888; font-weight:bold; "))
        
        self.spin_manual_pts = QSpinBox()
        self.spin_manual_pts.setRange(-100000, 100000)
        self.spin_manual_pts.setValue(100)
        self.spin_manual_pts.setFixedWidth(100)
        self.spin_manual_pts.setStyleSheet(STYLES["spinbox_modern"])
        l.addWidget(self.spin_manual_pts)

        l.addStretch()

        # Botón Aplicar (Estilo Sólido)
        btn_apply = QPushButton(" Aplicar")
        btn_apply.setIcon(get_icon_colored("save.svg", THEME_DARK['NeonGreen_Main']))
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setFixedHeight(34)
        btn_apply.setStyleSheet(STYLES["btn_primary"])
        btn_apply.clicked.connect(self._handle_manual_update)
        l.addWidget(btn_apply)
        
        return card

    def _create_table_card(self):
        """Contenedor de la tabla y sus filtros."""
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)

        # Toolbar Interna
        bar = QFrame()
        bar.setStyleSheet(f"border: 1px solid {THEME_DARK['Black_N4']};")
        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(*LAYOUT["margins"])
        h_bar.setSpacing(LAYOUT["spacing"])

        lbl_search = QLabel()
        lbl_search.setPixmap(get_icon("search.svg").pixmap(16,16))
        lbl_search.setStyleSheet("opacity: 0.5; border:none;")
        h_bar.addWidget(lbl_search)

        # Input estilizado desde factory
        self.inp_search = create_styled_input("Buscar usuario.", is_cmd=False, callback=self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"].replace(f"background-color: {THEME_DARK['Black_N2']}", "background-color: transparent"))
        self.combo_filter.addItems(["Todos", "Pausados", "Silenciados"])
        self.combo_filter.setFixedWidth(110)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)
        
        # Botón refresh desde factory
        btn_refresh = create_icon_btn("refresh-cw.svg", self.load_table_data, tooltip="Recargar")
        h_bar.addWidget(btn_refresh)

        l.addWidget(bar)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Usuario", "Puntos", "Visto", "Pausar", "Silenciar", "Acción"])
        self.table.setStyleSheet(STYLES["table_clean"] + "QTableWidget { border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }")
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(400) 
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 100)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 120)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(3, 80)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(4, 80)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(5, 60)

        l.addWidget(self.table)
        
        return card

    # ==========================================
    # LOGICA DE DATOS
    # ==========================================
    def load_table_data(self):
        scroll_val = self.table.verticalScrollBar().value()
        self.table.setRowCount(0)
        
        role_svgs = { "bot": "bot.svg", "user": "user.svg" }
        users = self.service.get_users_data() 

        for idx, (user, points, last_seen, is_paused, is_muted, role) in enumerate(users):
            if self.search_text and self.search_text not in user.lower(): continue
            if self.filter_mode == "Pausados" and not is_paused: continue
            if self.filter_mode == "Silenciados" and not is_muted: continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            clean_role = str(role).lower().strip() if role else "user"
            svg_name = role_svgs.get(clean_role, "user.svg")
            
            # 1. Usuario
            item_user = QTableWidgetItem(user)
            item_user.setIcon(get_icon(svg_name))
            item_user.setForeground(Qt.GlobalColor.white)
            if clean_role == "bot": item_user.setForeground(Qt.GlobalColor.green)
            item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            # 2. Puntos
            item_points = QTableWidgetItem(f"{points:,}")
            item_points.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_points.setForeground(Qt.GlobalColor.green)
            
            # 3. Visto
            t_str = str(last_seen).split(".")[0]
            item_time = QTableWidgetItem(t_str)
            item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_time.setForeground(Qt.GlobalColor.gray)
            
            # 4. Switch Pause (Usando Factory)
            w_pause = create_switch_widget(
                checked=is_paused, 
                func=lambda chk, u=user: self._handle_toggle_pause(u, chk), 
                tooltip="Pausar obtención de puntos"
            )
            
            # 5. Switch Mute (Usando Factory)
            w_mute = create_switch_widget(
                checked=is_muted, 
                func=lambda chk, u=user: self._handle_toggle_mute(u, chk), 
                tooltip="Silenciar en TTS"
            )
            
            # 6. Botón Eliminar (Usando Factory + Wrapper de Centrado)
            btn_del = create_icon_btn(
                "trash.svg", 
                lambda _, u=user: self._handle_delete_user(u), 
                color_hover="#ff453a"
            )
            # Wrapper para centrar el botón en la celda
            w_del = QWidget(); w_del.setStyleSheet("background: transparent;")
            l_del = QHBoxLayout(w_del); l_del.setContentsMargins(0,0,0,0); l_del.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l_del.addWidget(btn_del)
            
            self.table.setItem(row, 0, item_user)
            self.table.setItem(row, 1, item_points)
            self.table.setItem(row, 2, item_time)
            self.table.setCellWidget(row, 3, w_pause)
            self.table.setCellWidget(row, 4, w_mute)
            self.table.setCellWidget(row, 5, w_del)

        self.table.verticalScrollBar().setValue(scroll_val)

    def _auto_refresh(self):
        if not self.inp_search.hasFocus() and not self.inp_manual_user.hasFocus():
            self.load_table_data()

    def _handle_manual_update(self):
        user = self.inp_manual_user.text().strip()
        qty = self.spin_manual_pts.value()
        
        if not user:
            ToastNotification(self, "Error", "Ingresa un usuario", "status_warning").show_toast()
            return
            
        new_total = self.service.add_manual_points(user, qty)
        ToastNotification(self, "Puntos", f"{user}: {qty:+} pts (Total: {new_total})", "status_success").show_toast()
        self.inp_manual_user.clear()
        self.load_table_data()

    def _handle_search_changed(self, text):
        self.search_text = text.lower().strip()
        self.load_table_data()

    def _handle_filter_changed(self):
        self.filter_mode = self.combo_filter.currentText()
        self.load_table_data()

    def _handle_toggle_pause(self, user, checked):
        self.service.toggle_pause(user, checked)
        ToastNotification(self, "Estado", f"{user} {'pausado' if checked else 'anudado'}", "info").show_toast()

    def _handle_toggle_mute(self, user, checked):
        self.service.toggle_mute(user, checked)
        msg = "Silenciado 🔇" if checked else "Escuchando 🔊"
        ToastNotification(self, "Voz", f"{user} {msg}", "info").show_toast()

    def _handle_delete_user(self, user):
        if ModalConfirm(self, "Eliminar", f"¿Estás seguro de eliminar a {user}? Se perderán sus puntos.").exec():
            if self.service.delete_user(user):
                self.load_table_data()
                ToastNotification(self, "Eliminado", "Usuario eliminado correctamente.", "status_success").show_toast()

    def _handle_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Puntos", "data_users.csv", "CSV Files (*.csv)")
        if not path: return

        if self.service.export_points_csv(path):
            ToastNotification(self, "Exportado", f"Datos guardados en {path}", "status_success").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo escribir el archivo.", "status_error").show_toast()

    def _handle_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Puntos", "", "CSV Files (*.csv)")
        if not path: return

        if not ModalConfirm(self, "Importar Datos", "Esto sobrescribirá puntos y roles. ¿Continuar?").exec():
            return

        success, title, msg = self.service.import_points_csv(path)
        
        msg_type = "status_success" if success else "status_error"
        if success and "Errores" in msg and not msg.endswith("(Errores: 0)"):
             msg_type = "status_warning" 

        ToastNotification(self, title, msg, msg_type).show_toast()
        
        if success:
            self.load_table_data()