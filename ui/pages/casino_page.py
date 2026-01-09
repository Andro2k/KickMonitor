# ui/pages/gambling_page.py

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QTabWidget, QPushButton
)
from PyQt6.QtCore import Qt, QSize
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.utils import get_icon 
from ui.theme import LAYOUT, THEME_DARK, STYLES, RADIUS, get_switch_style
from services.gambling_service import GamblingService

class GamblingPage(QWidget):
    def __init__(self, db_handler, controller=None, parent=None):
        super().__init__(parent)
        self.service = GamblingService(db_handler)
        self.init_ui()
        self.load_initial_history()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(layout)
        self._setup_tabs(layout)

    def _setup_header(self, layout):
        header = QHBoxLayout()
        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        
        v_head.addWidget(QLabel("Casino & Apuestas", objectName="h2"))
        v_head.addWidget(QLabel("Sistema de economía y juegos de azar.", objectName="subtitle"))
        
        header.addLayout(v_head)
        header.addStretch()
        layout.addLayout(header)

    def _setup_tabs(self, layout):
        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(18, 18))
        
        # --- CAMBIO AQUÍ: Usamos el estilo centralizado ---
        self.tabs.setStyleSheet(STYLES["tabs_base"])
        # --------------------------------------------------

        # Pestaña 1: Configuración
        self.tab_settings = QWidget()
        self._build_settings_tab(self.tab_settings)
        self.tabs.addTab(self.tab_settings, get_icon("settings.svg"), "Configuración")

        # Pestaña 2: Historial
        self.tab_history = QWidget()
        self._build_history_tab(self.tab_history)
        self.tabs.addTab(self.tab_history, get_icon("activity.svg"), "Historial en Vivo") 

        layout.addWidget(self.tabs)

    # ==========================================
    # 2. CONTENIDO PESTAÑA: CONFIGURACIÓN
    # ==========================================
    def _build_settings_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        # A. Interruptor Maestro
        switch_frame = self._create_clean_frame()
        sw_layout = QHBoxLayout(switch_frame)
        sw_layout.setContentsMargins(*LAYOUT["margins"])
        
        lbl_sw = QLabel("Estado del Casino", objectName="normal")
        lbl_sw.setStyleSheet(f"border: none;")
        
        self.chk_enabled = QCheckBox("Habilitado")
        self.chk_enabled.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_enabled.setStyleSheet(get_switch_style())
        self.chk_enabled.setChecked(self.service.get_status())
        self.chk_enabled.toggled.connect(self._handler_toggle_casino)
        
        sw_layout.addWidget(lbl_sw)
        sw_layout.addStretch()
        sw_layout.addWidget(self.chk_enabled)
        layout.addWidget(switch_frame)

        # B. Límites Globales
        layout.addWidget(QLabel("Límites de Apuesta", objectName="h3"))
        
        limits_frame = self._create_clean_frame()
        l_limits = QHBoxLayout(limits_frame)
        l_limits.setContentsMargins(*LAYOUT["margins"])
        l_limits.setSpacing(LAYOUT["spacing"])
        
        # Mínimo
        v_min = QVBoxLayout()
        # Creamos el label y le quitamos el borde
        lbl_min = QLabel("Apuesta Mínima:")
        lbl_min.setObjectName("subtitle")
        lbl_min.setStyleSheet("border: none; color: #aaa;")
        v_min.addWidget(lbl_min)

        self.spin_min = QSpinBox()
        self.spin_min.setRange(1, 100000)
        self.spin_min.setValue(self.service.get_min_bet())
        self.spin_min.setStyleSheet(STYLES["spinbox_modern"])
        self.spin_min.valueChanged.connect(self.service.set_min_bet)
        v_min.addWidget(self.spin_min)

        # Máximo
        v_max = QVBoxLayout()
        # Lo mismo para el máximo
        lbl_max = QLabel("Apuesta Máxima:")
        lbl_max.setObjectName("subtitle")
        lbl_max.setStyleSheet("border: none; color: #aaa;") # <--- AQUÍ EL CAMBIO
        v_max.addWidget(lbl_max)

        self.spin_max = QSpinBox()
        self.spin_max.setRange(100, 1000000)
        self.spin_max.setValue(self.service.get_max_bet())
        self.spin_max.setStyleSheet(STYLES["spinbox_modern"])
        self.spin_max.valueChanged.connect(self.service.set_max_bet)
        v_max.addWidget(self.spin_max)
        
        l_limits.addLayout(v_min)
        l_limits.addLayout(v_max)
        layout.addWidget(limits_frame)

        # C. Juegos (Grilla)
        layout.addWidget(QLabel("Reglas por Juego", objectName="h3"))
        
        # Fila 1
        row1 = QHBoxLayout()
        row1.setSpacing(15)
        row1.addWidget(self._create_game_panel("dices.svg", "Dados", [
            ("Win Rate (%):", "gamble_win_rate", 45, True),
            ("Pago (x):", "gamble_multiplier", 2.0, False)
        ]))
        row1.addWidget(self._create_game_panel("credit-card.svg", "Carta Alta", [
             ("Pago (x):", "highcard_multiplier", 2.0, False)
        ]))
        layout.addLayout(row1)

        # Fila 2
        row2 = QHBoxLayout()
        row2.setSpacing(15)
        row2.addWidget(self._create_game_panel("columns.svg", "Slots", [
            ("Jackpot (3 iguales) x:", "slots_jackpot_x", 10, True)
        ]))
        row2.addWidget(self._create_game_panel("disc.svg", "Ruleta", [
            ("Pago Número (x):", "roulette_multi_num", 35.0, False),
            ("Pago Color (x):", "roulette_multi_col", 2.0, False)
        ]))
        layout.addLayout(row2)

        layout.addStretch()

    # ==========================================
    # 3. CONTENIDO PESTAÑA: HISTORIAL
    # ==========================================
    def _build_history_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(*LAYOUT["margins"])
        
        # Barra Superior
        h_top = QHBoxLayout()
        h_top.addWidget(QLabel("Monitor de Jugadas", objectName="h3"))
        h_top.addStretch()
        
        # Botón Recargar (Link)
        btn_load = QLabel(" <a href='#'>Recargar</a> ")
        btn_load.linkActivated.connect(self.load_initial_history)
        btn_load.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main']}; font-weight:bold;")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        h_top.addWidget(btn_load)

        # --- NUEVO: Botón Borrar (Papelera) ---
        btn_clean = QPushButton()
        btn_clean.setIcon(get_icon("trash.svg"))
        btn_clean.setFixedSize(28, 28)
        btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clean.setToolTip("Borrar todo el historial")
        btn_clean.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N4']};
                
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 69, 58, 0.2); 
                border: 1px solid #FF453A;
            }}
        """)
        btn_clean.clicked.connect(self._handler_clear_history)
        h_top.addWidget(btn_clean)
        # --------------------------------------

        layout.addLayout(h_top)

        # Tabla (Igual que antes)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Hora", "Usuario", "Juego", "Resultado"])
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(STYLES["table_clean"])
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 70)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 120)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 100)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)

    # ==========================================
    # 4. HELPERS VISUALES
    # ==========================================
    def _create_clean_frame(self):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']}; 
                border-radius: {RADIUS['input']}; 
                
            }}
        """)
        return f

    def _create_game_panel(self, icon_name, title_text, settings):
        """Genera un panel de configuración para un juego específico."""
        container = QWidget()
        l_cont = QVBoxLayout(container)
        l_cont.setContentsMargins(0,0,0,0)
        l_cont.setSpacing(5)
        
        # Header (Icono + Título)
        h_head = QHBoxLayout()
        h_head.setSpacing(8)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(icon_name).pixmap(QSize(18, 18)))
        icon_lbl.setStyleSheet("border: none; opacity: 0.8;")
        
        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet(f"font-weight: bold; color: {THEME_DARK['White_N1']}; border: none;")
        
        h_head.addWidget(icon_lbl)
        h_head.addWidget(lbl_title)
        h_head.addStretch()
        l_cont.addLayout(h_head)
        
        # Cuerpo con inputs
        frame = self._create_clean_frame()
        l_frame = QVBoxLayout(frame)
        l_frame.setSpacing(LAYOUT["spacing"])
        l_frame.setContentsMargins(*LAYOUT["margins"])
        
        for lbl_text, key, default, is_int in settings:
            l_frame.addWidget(QLabel(lbl_text, styleSheet="border:none; color:#aaa; font-size:12px;"))
            
            if is_int:
                val = self.service.get_int_setting(key, default)
                spin = QSpinBox()
                spin.setRange(1, 1000)
                spin.setValue(val)
                spin.setStyleSheet(STYLES["spinbox_modern"])
                spin.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))
                
                if "%" in lbl_text: spin.setSuffix("%")
                elif "x" in lbl_text: spin.setSuffix(" x")
                
                l_frame.addWidget(spin)
            else:
                val = self.service.get_float_setting(key, default)
                dspin = QDoubleSpinBox()
                dspin.setRange(1.1, 100.0)
                dspin.setValue(val)
                dspin.setSingleStep(0.1)
                dspin.setStyleSheet(STYLES["spinbox_modern"])
                dspin.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))
                
                l_frame.addWidget(dspin)
                
        l_frame.addStretch()
        l_cont.addWidget(frame)
        return container

    # ==========================================
    # 5. HANDLERS
    # ==========================================
    def _handler_toggle_casino(self, checked):
        self.service.set_status(checked)
        status = "HABILITADO" if checked else "DESHABILITADO"
        color = "Status_Green" if checked else "Status_Yellow"
        ToastNotification(self, "Casino", f"Sistema {status}", color).show_toast()

    def load_initial_history(self):
        """Carga datos de la base de datos."""
        self.table.setRowCount(0)
        history = self.service.get_history_log(50) # Obtener últimos 50
        
        # Iterar en orden inverso para que el más nuevo quede arriba (o abajo según prefieras)
        # La query viene ORDER BY id DESC (el primero es el más nuevo)
        for row in history:
            # row: timestamp, username, game_type, result_text, is_win
            ts_str = str(row[0]).split(" ")[1][:5] if " " in str(row[0]) else str(row[0])
            self.add_history_entry(row[1], row[2], row[3], bool(row[4]), ts_str)

    def add_history_entry(self, user, game_type, result_text, is_win=False, time_str=None):
        """
        Agrega una fila al historial.
        Soporta is_win para colores y time_str para historial guardado.
        """
        # Si no nos pasan hora (es un evento en vivo), usamos la actual
        if not time_str:
            time_str = datetime.now().strftime("%H:%M")
            
        row = 0
        self.table.insertRow(row)
        
        # 1. Columna Hora
        item_time = QTableWidgetItem(time_str)
        item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_time.setForeground(Qt.GlobalColor.gray)
        
        # 2. Columna Usuario
        item_user = QTableWidgetItem(user)
        item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        # 3. Columna Juego (Icono + Nombre)
        name_map = {"dice": "Dados", "roulette": "Ruleta", "slots": "Slots", "highcard": "Cartas"}
        icon_map = {"dice": "dices.svg", "roulette": "disc.svg", "slots": "columns.svg", "highcard": "credit-card.svg"}
        
        g_name = name_map.get(game_type, game_type)
        g_icon = icon_map.get(game_type, "dices.svg")
        
        item_game = QTableWidgetItem(g_name)
        item_game.setIcon(get_icon(g_icon))
        
        # 4. Columna Resultado (Con Color basado en is_win)
        clean_res = result_text.replace(f"@{user}", "").strip()
        item_res = QTableWidgetItem(clean_res)
        
        # Usamos el booleano real 'is_win' que viene de la base de datos/controlador
        if is_win:
            item_res.setForeground(Qt.GlobalColor.green) # Ganó
        else:
            item_res.setForeground(Qt.GlobalColor.red)   # Perdió
            
        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_user)
        self.table.setItem(row, 2, item_game)
        self.table.setItem(row, 3, item_res)
        
        # Mantener la tabla limpia (máximo 50 filas)
        if self.table.rowCount() > 50:
            self.table.removeRow(50)
    
    def _handler_clear_history(self):
        # Advertencia de seguridad usando tu componente ModalConfirm
        if ModalConfirm(self, "Borrar Historial", "¿Estás seguro? Se eliminarán todos los registros de juego permanentemente.").exec():
            # 1. Borrar de DB
            if self.service.clear_all_history():
                # 2. Limpiar UI
                self.table.setRowCount(0)
                ToastNotification(self, "Limpieza", "Historial eliminado correctamente", "Status_Green").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo borrar la base de datos", "Status_Red").show_toast()