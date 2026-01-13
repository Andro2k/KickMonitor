# ui/pages/points_page.py

import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QCheckBox, QAbstractItemView, 
    QLineEdit, QComboBox, QFrame, QFileDialog,
    QScrollArea, QSizePolicy, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from ui.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from ui.utils import get_icon, get_colored_icon
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from backend.services.points_service import PointsService

class PointsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = PointsService(db_handler)
        
        self.search_text = ""
        self.filter_mode = "Todos"
        
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
        
        # --- CAMBIO: Usamos QVBoxLayout simple en lugar de FlowLayout ---
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(*LAYOUT["margins"])
        self.content_layout.setSpacing(LAYOUT["spacing"])

        # 3. CONSTRUCCIÓN DE LA UI
        # A. Header (Título + Botones Exportar)
        self.content_layout.addWidget(self._create_header()) 
        # B. Barra de Gestión Manual (Compacta)
        self.content_layout.addWidget(self._create_manual_strip())
        # C. Tabla de Usuarios (Expansible)
        self.content_layout.addWidget(self._create_table_card())
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_header(self):
        h_frame = QFrame()
        h_header = QHBoxLayout(h_frame)
        h_header.setContentsMargins(0, 0, 0, 0)
        
        v_titles = QVBoxLayout()
        v_titles.setSpacing(LAYOUT["spacing"])
        v_titles.addWidget(QLabel("Tabla de Usuarios", objectName="h2"))
        v_titles.addWidget(QLabel("Gestión de puntos y estado de usuarios.", objectName="subtitle"))
        h_header.addLayout(v_titles)
        h_header.addStretch()
        
        btn_import = self._create_top_btn("upload.svg", "Importar", self._handle_import_csv)
        btn_export = self._create_top_btn("download.svg", "Exportar", self._handle_export_csv)
        
        h_header.addWidget(btn_import)       
        h_header.addWidget(btn_export)
        
        return h_frame

    # ==========================================
    # TARJETA 1: GESTIÓN MANUAL (MODO BARRA)
    # ==========================================
    def _create_manual_strip(self):
        """
        Crea una barra horizontal compacta para agregar/quitar puntos.
        """
        card = QFrame()
        card.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        # Usamos QHBoxLayout (Horizontal) para que quede en una línea
        l = QHBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        # Inputs en línea
        l.addWidget(QLabel("Usuario:", styleSheet="color:#888; font-weight:bold; "))
        
        self.inp_manual_user = QLineEdit()
        self.inp_manual_user.setPlaceholderText("Ej: damir")
        self.inp_manual_user.setFixedWidth(150)
        self.inp_manual_user.setStyleSheet(STYLES["input"])
        l.addWidget(self.inp_manual_user)

        l.addWidget(QLabel("Puntos:", styleSheet="color:#888; font-weight:bold; "))
        
        self.spin_manual_pts = QSpinBox()
        self.spin_manual_pts.setRange(-100000, 100000)
        self.spin_manual_pts.setValue(100)
        self.spin_manual_pts.setFixedWidth(100)
        self.spin_manual_pts.setStyleSheet(STYLES["spinbox_modern"])
        l.addWidget(self.spin_manual_pts)

        l.addStretch()

        # Botón Aplicar
        btn_apply = QPushButton(" Aplicar")
        btn_apply.setIcon(get_colored_icon("save.svg", THEME_DARK['Black_N1']))
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setFixedHeight(34)
        btn_apply.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['NeonGreen_Main']};
                color: {THEME_DARK['Black_N1']};
                font-weight: bold; border-radius: 6px; border: none; padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Light']}; }}
        """)
        btn_apply.clicked.connect(self._handle_manual_update)
        l.addWidget(btn_apply)
        
        return card

    # ==========================================
    # TARJETA 2: TABLA (OCUPA EL RESTO)
    # ==========================================
    def _create_table_card(self):
        card = QFrame()
        # Expanding vertical para que llene la pantalla
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card.setStyleSheet(f"background: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)

        # Toolbar Interna (Buscador y Filtros)
        bar = QFrame()
        bar.setStyleSheet(f"border-bottom: 1px solid {THEME_DARK['Black_N4']}; background: transparent;")
        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(*LAYOUT["margins"])
        h_bar.setSpacing(LAYOUT["spacing"])

        lbl_search = QLabel()
        lbl_search.setPixmap(get_icon("search.svg").pixmap(16,16))
        lbl_search.setStyleSheet("opacity: 0.5; border:none;")
        h_bar.addWidget(lbl_search)

        self.inp_search = QLineEdit()
        self.inp_search.setStyleSheet(STYLES["input"])
        self.inp_search.setPlaceholderText("Buscar usuario...")
        self.inp_search.setStyleSheet("background:transparent; color:white;")
        self.inp_search.textChanged.connect(self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"].replace(f"background-color: {THEME_DARK['Black_N2']}", "background-color: transparent"))
        self.combo_filter.addItems(["Todos", "Pausados", "Silenciados"])
        self.combo_filter.setFixedWidth(110)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)
        
        btn_refresh = QPushButton()
        btn_refresh.setIcon(get_icon("refresh-cw.svg"))
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("background:transparent; border:none;")
        btn_refresh.clicked.connect(self.load_table_data)
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
        # Altura mínima para que no desaparezca
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
    # LOGICA DE DATOS (Sin Cambios)
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
            
            item_user = QTableWidgetItem(user)
            item_user.setIcon(get_icon(svg_name))
            item_user.setForeground(Qt.GlobalColor.white)
            if clean_role == "bot": item_user.setForeground(Qt.GlobalColor.green)
            item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            item_points = QTableWidgetItem(f"{points:,}")
            item_points.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_points.setForeground(Qt.GlobalColor.green)
            
            t_str = str(last_seen).split(".")[0]
            item_time = QTableWidgetItem(t_str)
            item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_time.setForeground(Qt.GlobalColor.gray)
            
            w_pause = self._create_switch_widget(is_paused, "Pausar", lambda chk, u=user: self._handle_toggle_pause(u, chk))
            w_mute = self._create_switch_widget(is_muted, "Silenciar", lambda chk, u=user: self._handle_toggle_mute(u, chk))
            btn_del = self._create_action_btn("trash.svg", "#ff453a", lambda _, u=user: self._handle_delete_user(u))
            
            self.table.setItem(row, 0, item_user)
            self.table.setItem(row, 1, item_points)
            self.table.setItem(row, 2, item_time)
            self.table.setCellWidget(row, 3, w_pause)
            self.table.setCellWidget(row, 4, w_mute)
            self.table.setCellWidget(row, 5, btn_del)

        self.table.verticalScrollBar().setValue(scroll_val)

    def _auto_refresh(self):
        if not self.inp_search.hasFocus() and not self.inp_manual_user.hasFocus():
            self.load_table_data()

    def _handle_manual_update(self):
        user = self.inp_manual_user.text().strip()
        qty = self.spin_manual_pts.value()
        
        if not user:
            ToastNotification(self, "Error", "Ingresa un usuario", "Status_Yellow").show_toast()
            return
            
        new_total = self.service.add_manual_points(user, qty)
        ToastNotification(self, "Puntos", f"{user}: {qty:+} pts (Total: {new_total})", "Status_Green").show_toast()
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
                ToastNotification(self, "Eliminado", "Usuario eliminado correctamente.", "Status_Green").show_toast()

    def _handle_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Puntos", "data_users.csv", "CSV Files (*.csv)")
        if not path: return

        # La UI solo llama al servicio y muestra el resultado
        if self.service.export_points_csv(path):
            ToastNotification(self, "Exportado", f"Datos guardados en {path}", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo escribir el archivo.", "Status_Red").show_toast()

    def _handle_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Puntos", "", "CSV Files (*.csv)")
        if not path: return

        if not ModalConfirm(self, "Importar Datos", "Esto sobrescribirá puntos y roles. ¿Continuar?").exec():
            return

        success, title, msg = self.service.import_points_csv(path)
        
        msg_type = "Status_Green" if success else "Status_Red"
        if success and "Errores" in msg and not msg.endswith("(Errores: 0)"):
             msg_type = "Status_Yellow" # Advertencia si hubo algunos fallos parciales

        ToastNotification(self, title, msg, msg_type).show_toast()
        
        if success:
            self.load_table_data()

    # ==========================================
    # HELPERS
    # ==========================================
    def _create_top_btn(self, icon, text, func):
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N2']}; color: {THEME_DARK['White_N1']};
                padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['Black_N4']}; 
                border-color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def _create_switch_widget(self, checked, tooltip, callback):
        w = QWidget(); w.setStyleSheet("background: transparent;")
        l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk = QCheckBox(); chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setToolTip(tooltip)
        chk.setStyleSheet(get_switch_style("switch-on.svg"))
        chk.setChecked(bool(checked))
        chk.clicked.connect(callback)
        l.addWidget(chk)
        return w

    def _create_action_btn(self, icon, color, func):
        w = QWidget(); w.setStyleSheet("background: transparent;")
        l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton(); btn.setIcon(get_icon(icon)); btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; }} 
            QPushButton:hover {{ 
                background-color: {color}; border: 1px solid {color}; border-radius: 4px; 
            }}
        """)
        btn.clicked.connect(func)
        l.addWidget(btn)
        return w