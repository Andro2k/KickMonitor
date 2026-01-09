# ui/pages/points_page.py

import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QCheckBox, QAbstractItemView, 
    QLineEdit, QComboBox, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from ui.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from ui.utils import get_icon
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from services.points_service import PointsService

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

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(layout)
        self._setup_toolbar(layout)
        self._setup_table(layout)
        
        # Carga inicial
        self.load_table_data()

    def _setup_header(self, layout):
        """Título y botones de gestión de datos (Import/Export)."""
        h_header = QHBoxLayout()
        
        # Títulos
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)
        v_titles.addWidget(QLabel("Tabla de Usuarios", objectName="h2"))
        v_titles.addWidget(QLabel("Gestión de puntos y estado de usuarios.", objectName="subtitle"))
        h_header.addLayout(v_titles)
        h_header.addStretch()
        
        # Botones de Acción Global
        btn_export = self._create_top_btn("download.svg", "Exportar CSV", self._handle_export_csv)
        btn_import = self._create_top_btn("upload.svg", "Importar CSV", self._handle_import_csv)
        btn_refresh = self._create_top_btn("refresh-cw.svg", "Refrescar", self.load_table_data)
        
        h_header.addWidget(btn_export)
        h_header.addWidget(btn_import)
        h_header.addWidget(btn_refresh)
        
        layout.addLayout(h_header)

    def _setup_toolbar(self, layout):
        """Barra de búsqueda y filtros."""
        bar = QFrame()
        bar.setStyleSheet(f"background-color: {THEME_DARK['Black_N3']}; border-radius: 10px; ")
        h_bar = QHBoxLayout(bar)
        h_bar.setContentsMargins(*LAYOUT["margins"])
        h_bar.setSpacing(LAYOUT["spacing"])

        # Icono Lupa
        lbl_search = QLabel()
        lbl_search.setPixmap(get_icon("search.svg").pixmap(16,16))
        lbl_search.setStyleSheet("opacity: 0.5; border:none;")
        h_bar.addWidget(lbl_search)

        # Input Buscador
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Buscar por nombre...")
        self.inp_search.setStyleSheet(STYLES["input"])
        self.inp_search.textChanged.connect(self._handle_search_changed)
        h_bar.addWidget(self.inp_search, stretch=1)
        
        # Separador Vertical
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("border-left: 1px solid #444;")
        h_bar.addWidget(line)
        
        # Combo Filtro
        h_bar.addWidget(QLabel("Ver:", styleSheet="border:none;", objectName="normal"))
        self.combo_filter = QComboBox()
        self.combo_filter.setStyleSheet(STYLES["combobox"])
        self.combo_filter.addItems(["Todos", "Pausados", "Silenciados"])
        self.combo_filter.setFixedWidth(120)
        self.combo_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_filter.currentIndexChanged.connect(self._handle_filter_changed)
        h_bar.addWidget(self.combo_filter)

        layout.addWidget(bar)

    def _setup_table(self, layout):
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Usuario", "Puntos", "Visto", "Pausar", "Silenciar", "Acción"])
        self.table.setStyleSheet(STYLES["table_clean"])
        
        # Configuración Visual
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Anchos de Columna
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Usuario llena espacio
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 100)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 120)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(3, 80)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(4, 80)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(5, 60)

        layout.addWidget(self.table)

    # ==========================================
    # 2. LOGICA DE DATOS
    # ==========================================
    def load_table_data(self):
        scroll_val = self.table.verticalScrollBar().value()
        self.table.setRowCount(0)
        
        # IMPORTANTE: Asegúrate de tener estos archivos en tu carpeta de iconos
        role_svgs = {
            "bot":         "bot.svg",
            "user":        "user.svg"
        }

        users = self.service.get_users_data() 

        for idx, (user, points, last_seen, is_paused, is_muted, role) in enumerate(users):
            
            # Filtros...
            if self.search_text and self.search_text not in user.lower(): continue
            if self.filter_mode == "Pausados" and not is_paused: continue
            if self.filter_mode == "Silenciados" and not is_muted: continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            clean_role = str(role).lower().strip() if role else "user"
            
            # Lógica: Si es "bot", usa bot.svg. Si es CUALQUIER otra cosa, usa user.svg
            svg_name = role_svgs.get(clean_role, "user.svg")
            
            item_user = QTableWidgetItem(user)
            item_user.setIcon(get_icon(svg_name))
            item_user.setForeground(Qt.GlobalColor.white)
            
            # Solo coloreamos diferente si es Bot, el resto blanco normal
            if clean_role == "bot": 
                item_user.setForeground(Qt.GlobalColor.green)

            item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            # ... (El resto del bucle for sigue exactamente igual: puntos, tiempo, botones) ...
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
        # Solo refrescar si el usuario no está buscando activamente
        if not self.inp_search.hasFocus():
            self.load_table_data()

    # ==========================================
    # 3. HANDLERS (EVENTOS)
    # ==========================================
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

    # --- NUEVO: EXPORTAR CSV ---
    def _handle_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Puntos", "data_users.csv", "CSV Files (*.csv)")
        if not path: return

        try:
            users = self.service.get_users_data()
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Agregamos "role" al encabezado
                writer.writerow(["username", "points", "last_seen", "is_paused", "is_muted", "role"])
                
                for u in users:
                    # u tiene: [0]name, [1]pts, [2]seen, [3]pause, [4]mute, [5]role
                    # Nos aseguramos de guardar el role (u[5]) al final
                    role_val = u[5] if u[5] else "user"
                    writer.writerow([u[0], u[1], str(u[2]), int(u[3]), int(u[4]), role_val])
            
            ToastNotification(self, "Exportado", f"Datos guardados en {path}", "Status_Green").show_toast()
        except Exception as e:
            ToastNotification(self, "Error Exportar", str(e), "Status_Red").show_toast()

    # --- NUEVO: IMPORTAR CSV CORREGIDO ---
    def _handle_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Puntos", "", "CSV Files (*.csv)")
        if not path: return

        if not ModalConfirm(self, "Importar Datos", "Esto sobrescribirá puntos y roles. ¿Continuar?").exec():
            return

        count = 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # Saltar cabecera
                
                for row in reader:
                    # Formato esperado: [0]User, [1]Points, [2]Date, [3]Paused, [4]Muted, [5]Role
                    if len(row) >= 2:
                        user = row[0].strip()
                        try:
                            # 1. Actualizar Puntos
                            target_points = int(row[1])
                            current = self.service.db.get_points(user)
                            diff = target_points - current
                            
                            # Esto crea al usuario si no existe gracias a la lógica interna de add_points
                            self.service.db.add_points(user, diff)
                            
                            # 2. Actualizar Pausa/Mute (Si existen en el CSV)
                            if len(row) >= 5:
                                is_paused = int(row[3]) == 1
                                is_muted = int(row[4]) == 1
                                self.service.toggle_pause(user, is_paused)
                                self.service.toggle_mute(user, is_muted)

                            # 3. NUEVO: Actualizar ROL (Si existe en el CSV)
                            if len(row) >= 6:
                                role_csv = row[5].strip()
                                # Usamos la función que ya tienes en DBHandler
                                self.service.db.update_user_role(user, role_csv)
                            
                            count += 1
                        except ValueError:
                            continue 

            self.load_table_data()
            ToastNotification(self, "Importación", f"{count} usuarios actualizados.", "Status_Green").show_toast()
            
        except Exception as e:
            ToastNotification(self, "Error Importar", str(e), "Status_Red").show_toast()

    # ==========================================
    # 4. HELPERS VISUALES
    # ==========================================
    def _create_top_btn(self, icon, text, func):
        btn = QPushButton(text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N3']};
                color: {THEME_DARK['White_N1']};
                
                padding: 6px 12px; border-radius: 6px; font-size: 12px;
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
        
        chk = QCheckBox()
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setToolTip(tooltip)
        chk.setStyleSheet(get_switch_style("switch-on.svg"))
        chk.setChecked(bool(checked))
        chk.clicked.connect(callback)
        
        l.addWidget(chk)
        return w

    def _create_action_btn(self, icon, color, func):
        w = QWidget(); w.setStyleSheet("background: transparent;")
        l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; }} 
            QPushButton:hover {{ 
                background-color: {color}; 
                border: 1px solid {color}; 
                border-radius: 4px; 
            }}
        """)
        btn.clicked.connect(func)
        
        l.addWidget(btn)
        return w