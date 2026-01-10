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
from services.points_service import PointsService
from ui.components.flow_layout import FlowLayout # <--- IMPORTANTE

class PointsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = PointsService(db_handler)
        
        # Estado interno
        self.search_text = ""
        self.filter_mode = "Todos"
        
        # Timer: Actualización automática (10s)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(10000) 
        
        self.init_ui()
        self.load_table_data()

    # ==========================================
    # 1. UI SETUP (RESPONSIVE)
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
        
        # 4. TARJETAS
        self._setup_cards()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_header(self):
        h_frame = QFrame()
        h_header = QHBoxLayout(h_frame)
        h_header.setContentsMargins(*LAYOUT["margins"])
        
        # Títulos
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)
        v_titles.addWidget(QLabel("Tabla de Usuarios", objectName="h2"))
        v_titles.addWidget(QLabel("Gestión de puntos y estado de usuarios.", objectName="subtitle"))
        h_header.addLayout(v_titles)
        h_header.addStretch()
        
        # Botones de Acción Global
        btn_export = self._create_top_btn("download.svg", "Exportar", self._handle_export_csv)
        btn_import = self._create_top_btn("upload.svg", "Importar", self._handle_import_csv)
        
        h_header.addWidget(btn_export)
        h_header.addWidget(btn_import)
        
        return h_frame

    def _setup_cards(self):
        # TARJETA 1: GESTIÓN MANUAL (Nueva funcionalidad útil)
        self.card_manual = self._create_manual_card()
        self.card_manual.setMinimumWidth(320)
        self.card_manual.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.flow_layout.addWidget(self.card_manual)

        # TARJETA 2: TABLA DE USUARIOS (Con Filtros Integrados)
        self.card_table = self._create_table_card()
        self.card_table.setMinimumWidth(500)
        self.card_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.flow_layout.addWidget(self.card_table)

    # ==========================================
    # CREADORES DE TARJETAS
    # ==========================================
    def _create_manual_card(self):
        """Tarjeta para sumar/restar puntos rápidamente."""
        card = QFrame()
        card.setStyleSheet(f"background: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 20, 20, 20)
        l.setSpacing(15)

        l.addWidget(QLabel("Gestión Rápida", objectName="h3"))

        # Input Usuario
        l.addWidget(QLabel("Usuario:", styleSheet="color:#888; font-size:12px; border:none;"))
        self.inp_manual_user = QLineEdit()
        self.inp_manual_user.setPlaceholderText("Ej: damir")
        self.inp_manual_user.setStyleSheet(STYLES["input"])
        l.addWidget(self.inp_manual_user)

        # Input Puntos
        l.addWidget(QLabel("Puntos (+/-):", styleSheet="color:#888; font-size:12px; border:none;"))
        self.spin_manual_pts = QSpinBox()
        self.spin_manual_pts.setRange(-100000, 100000)
        self.spin_manual_pts.setValue(100)
        self.spin_manual_pts.setStyleSheet(STYLES["spinbox_modern"])
        l.addWidget(self.spin_manual_pts)

        l.addStretch()

        # Botón Aplicar
        btn_apply = QPushButton(" Aplicar")
        btn_apply.setIcon(get_colored_icon("save.svg", THEME_DARK['Black_N1']))
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setFixedHeight(38)
        btn_apply.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['NeonGreen_Main']};
                color: {THEME_DARK['Black_N1']};
                font-weight: bold; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Light']}; }}
        """)
        btn_apply.clicked.connect(self._handle_manual_update)
        l.addWidget(btn_apply)
        
        return card

    def _create_table_card(self):
        """Tarjeta que contiene la Toolbar y la Tabla."""
        card = QFrame()
        card.setStyleSheet(f"background: {THEME_DARK['Black_N3']}; border-radius: 16px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)

        # 1. TOOLBAR INTERNA
        bar = QFrame()
        bar.setStyleSheet(f"border-bottom: 1px solid {THEME_DARK['Black_N4']}; background: transparent;")
        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(15, 10, 15, 10)
        h_bar.setSpacing(10)

        lbl_search = QLabel()
        lbl_search.setPixmap(get_icon("search.svg").pixmap(16,16))
        lbl_search.setStyleSheet("opacity: 0.5; border:none;")
        h_bar.addWidget(lbl_search)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Buscar usuario...")
        self.inp_search.setStyleSheet("background:transparent; border:none; color:white;")
        self.inp_search.textChanged.connect(self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        h_bar.addWidget(QLabel("|", styleSheet="color:#444; border:none;"))
        
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"].replace(f"background-color: {THEME_DARK['Black_N2']}", "background-color: transparent"))
        self.combo_filter.addItems(["Todos", "Pausados", "Silenciados"])
        self.combo_filter.setFixedWidth(110)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)
        
        # Botón Refrescar Pequeño
        btn_refresh = QPushButton()
        btn_refresh.setIcon(get_icon("refresh-cw.svg"))
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet("background:transparent; border:none;")
        btn_refresh.clicked.connect(self.load_table_data)
        h_bar.addWidget(btn_refresh)

        l.addWidget(bar)

        # 2. TABLA
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Usuario", "Puntos", "Visto", "Pausar", "Silenciar", "Acción"])
        self.table.setStyleSheet(STYLES["table_clean"] + "QTableWidget { border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; }")
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(400) # Altura mínima
        
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
    # 2. LOGICA DE DATOS
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

    # ==========================================
    # HANDLERS
    # ==========================================
    def _handle_manual_update(self):
        user = self.inp_manual_user.text().strip()
        qty = self.spin_manual_pts.value()
        
        if not user:
            ToastNotification(self, "Error", "Ingresa un usuario", "Status_Yellow").show_toast()
            return
            
        # Asumiendo que DB tiene add_points, sino usamos la lógica de import
        new_total = self.service.db.add_points(user, qty) 
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

        try:
            users = self.service.get_users_data()
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["username", "points", "last_seen", "is_paused", "is_muted", "role"])
                for u in users:
                    role_val = u[5] if u[5] else "user"
                    writer.writerow([u[0], u[1], str(u[2]), int(u[3]), int(u[4]), role_val])
            ToastNotification(self, "Exportado", f"Datos guardados en {path}", "Status_Green").show_toast()
        except Exception as e:
            ToastNotification(self, "Error Exportar", str(e), "Status_Red").show_toast()

    def _handle_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Puntos", "", "CSV Files (*.csv)")
        if not path: return

        if not ModalConfirm(self, "Importar Datos", "Esto sobrescribirá puntos y roles. ¿Continuar?").exec():
            return

        count = 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        user = row[0].strip()
                        try:
                            target_points = int(row[1])
                            current = self.service.db.get_points(user)
                            diff = target_points - current
                            self.service.db.add_points(user, diff)
                            if len(row) >= 5:
                                self.service.toggle_pause(user, int(row[3]) == 1)
                                self.service.toggle_mute(user, int(row[4]) == 1)
                            if len(row) >= 6:
                                self.service.db.update_user_role(user, row[5].strip())
                            count += 1
                        except ValueError: continue 

            self.load_table_data()
            ToastNotification(self, "Importación", f"{count} usuarios actualizados.", "Status_Green").show_toast()
        except Exception as e:
            ToastNotification(self, "Error Importar", str(e), "Status_Red").show_toast()

    # ==========================================
    # HELPERS
    # ==========================================
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