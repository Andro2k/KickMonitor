# ui/pages/casino_page.py

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QPushButton, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt

from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.utils import get_icon, get_colored_icon
from ui.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from services.gambling_service import GamblingService
from ui.components.flow_layout import FlowLayout # <--- IMPORTAMOS

class GamblingPage(QWidget):
    def __init__(self, db_handler, controller=None, parent=None):
        super().__init__(parent)
        self.service = GamblingService(db_handler)
        self.init_ui()
        self.load_initial_history()
    
    def init_ui(self):
        # 1. SCROLL AREA
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # 2. LAYOUT PRINCIPAL DEL CONTENIDO
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(*LAYOUT["margins"])
        self.main_layout.setSpacing(LAYOUT["spacing"])

        # 3. CONSTRUCCIÓN
        self._setup_header()
        self._setup_cards_section()
        self._setup_history_section()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _setup_header(self):
        h_frame = QFrame()
        h_layout = QHBoxLayout(h_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        v_head.addWidget(QLabel("Casino & Apuestas", objectName="h2"))
        v_head.addWidget(QLabel("Sistema de economía y juegos de azar.", objectName="subtitle"))
        h_layout.addLayout(v_head)
        
        h_layout.addStretch()
        
        # Interruptor Maestro en la cabecera
        container = QWidget()
        container.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 8px; border: 1px solid {THEME_DARK['Black_N4']};")
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(*LAYOUT["margins"])
        
        lbl = QLabel("Estado del Casino:", styleSheet="border:none; color:#aaa; font-weight:bold; font-size:12px;")
        
        self.chk_enabled = QCheckBox()
        self.chk_enabled.setStyleSheet(get_switch_style())
        self.chk_enabled.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_enabled.setStyleSheet(get_switch_style())
        self.chk_enabled.setChecked(self.service.get_status())
        self.chk_enabled.toggled.connect(self._handler_toggle_casino)
        
        c_layout.addWidget(lbl)
        c_layout.addWidget(self.chk_enabled)
        
        h_layout.addWidget(container)
        
        self.main_layout.addWidget(h_frame)

    def _setup_cards_section(self):
        """Contenedor FlowLayout para las tarjetas de configuración."""
        self.main_layout.addWidget(QLabel("Configuración de Juegos", objectName="h3"))
        
        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent;")
        
        # FlowLayout para que las tarjetas se acomoden automáticamente
        self.flow_layout = FlowLayout(cards_container, margin=0, spacing=(LAYOUT["spacing"]))
        
        # 1. Tarjeta de Límites (Globales)
        self.flow_layout.addWidget(self._create_limits_card())
        
        # 2. Tarjetas de Juegos (Individuales)
        # Dados
        self.flow_layout.addWidget(self._create_game_card("dices.svg", "Dados", [
            ("Win Rate (%):", "gamble_win_rate", 45, True),
            ("Pago (x):", "gamble_multiplier", 2.0, False)
        ]))
        
        # Carta Alta
        self.flow_layout.addWidget(self._create_game_card("credit-card.svg", "Carta Alta", [
             ("Pago (x):", "highcard_multiplier", 2.0, False)
        ]))
        
        # Slots
        self.flow_layout.addWidget(self._create_game_card("columns.svg", "Slots", [
            ("Jackpot (3x) Multi:", "slots_jackpot_x", 10, True)
        ]))

        # Ruleta
        self.flow_layout.addWidget(self._create_game_card("disc.svg", "Ruleta", [
            ("Pago Número (x):", "roulette_multi_num", 35.0, False),
            ("Pago Color (x):", "roulette_multi_col", 2.0, False)
        ]))

        self.main_layout.addWidget(cards_container)

    def _setup_history_section(self):
        """Tarjeta ancha para la tabla de historial."""
        self.main_layout.addSpacing(LAYOUT["spacing"])
        
        # Header de sección
        h_sec = QHBoxLayout()
        h_sec.addWidget(QLabel("Historial en Vivo", objectName="h3"))
        h_sec.addStretch()
        
        # Botón Borrar
        btn_clean = QPushButton("Limpiar Historial")
        btn_clean.setIcon(get_colored_icon("trash.svg", "#FF453A"))
        btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clean.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N2']}; color: {THEME_DARK['White_N1']};
                padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background-color: rgba(255, 69, 58, 0.2); color: #FF453A; }}
        """)
        btn_clean.clicked.connect(self._handler_clear_history)
        h_sec.addWidget(btn_clean)
        
        self.main_layout.addLayout(h_sec)

        # Tarjeta Tabla
        card = QFrame()
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 16px;")
        l_card = QVBoxLayout(card)
        l_card.setContentsMargins(0,0,0,0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Hora", "Usuario", "Juego", "Resultado"])
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMinimumHeight(350) # Altura fija para la tabla
        self.table.setStyleSheet(STYLES["table_clean"] + "QTableWidget { border-radius: 16px; }")
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 80)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 120)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 100)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        l_card.addWidget(self.table)
        self.main_layout.addWidget(card)

    # ==========================================
    # CREADORES DE TARJETAS
    # ==========================================
    def _create_limits_card(self):
        """Tarjeta especial para límites min/max."""
        card = QFrame()
        card.setMinimumWidth(300)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        # Header
        h = QHBoxLayout()
        ico = QLabel(); ico.setPixmap(get_icon("sliders.svg").pixmap(18,18)); ico.setStyleSheet("border:none; opacity:0.7;")
        tit = QLabel("Límites Globales"); tit.setStyleSheet(f"font-weight:bold; color:{THEME_DARK['NeonGreen_Main']}; border:none;")
        h.addWidget(ico); h.addWidget(tit); h.addStretch()
        l.addLayout(h)

        # Inputs
        # Min
        l.addWidget(QLabel("Apuesta Mínima:", styleSheet="color:#aaa; font-size:11px; border:none;"))
        spin_min = QSpinBox()
        spin_min.setRange(1, 100000); spin_min.setValue(self.service.get_min_bet())
        spin_min.setStyleSheet(STYLES["spinbox_modern"])
        spin_min.valueChanged.connect(self.service.set_min_bet)
        l.addWidget(spin_min)

        # Max
        l.addWidget(QLabel("Apuesta Máxima:", styleSheet="color:#aaa; font-size:11px; border:none;"))
        spin_max = QSpinBox()
        spin_max.setRange(100, 1000000); spin_max.setValue(self.service.get_max_bet())
        spin_max.setStyleSheet(STYLES["spinbox_modern"])
        spin_max.valueChanged.connect(self.service.set_max_bet)
        l.addWidget(spin_max)

        l.addStretch()
        return card

    def _create_game_card(self, icon_name, title, settings):
        """Tarjeta genérica para configurar un juego."""
        card = QFrame()
        card.setMinimumWidth(280)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 12px;")
        
        l = QVBoxLayout(card)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(8)

        # Header
        h = QHBoxLayout()
        ico = QLabel(); ico.setPixmap(get_icon(icon_name).pixmap(18,18)); ico.setStyleSheet("border:none; opacity:0.8;")
        tit = QLabel(title); tit.setStyleSheet(f"font-weight:bold; color:{THEME_DARK['NeonGreen_Main']}; border:none;")
        h.addWidget(ico); h.addWidget(tit); h.addStretch()
        l.addLayout(h)
        
        # Separador
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background: {THEME_DARK['Black_N4']};")
        l.addWidget(sep)

        # Settings Dinámicos
        for lbl_text, key, default, is_int in settings:
            l.addWidget(QLabel(lbl_text, styleSheet="border:none; color:#aaa; font-size:11px; margin-top:4px;"))
            
            if is_int:
                val = self.service.get_int_setting(key, default)
                spin = QSpinBox()
                spin.setRange(1, 1000); spin.setValue(val)
                spin.setStyleSheet(STYLES["spinbox_modern"])
                if "%" in lbl_text: spin.setSuffix("%")
                elif "x" in lbl_text: spin.setSuffix(" x")
                spin.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))
                l.addWidget(spin)
            else:
                val = self.service.get_float_setting(key, default)
                dspin = QDoubleSpinBox()
                dspin.setRange(1.1, 100.0); dspin.setValue(val); dspin.setSingleStep(0.1)
                dspin.setStyleSheet(STYLES["spinbox_modern"])
                dspin.valueChanged.connect(lambda v, k=key: self.service.set_setting(k, v))
                l.addWidget(dspin)

        l.addStretch()
        return card

    # ==========================================
    # LOGICA DE HISTORIAL
    # ==========================================
    def load_initial_history(self):
        self.table.setRowCount(0)
        history = self.service.get_history_log(50)
        # history viene ordenado por ID DESC (el más reciente primero)
        for row in history:
            # row: timestamp, username, game_type, result_text, is_win
            ts_str = str(row[0]).split(" ")[1][:5] if " " in str(row[0]) else str(row[0])
            self.add_history_entry(row[1], row[2], row[3], bool(row[4]), ts_str)

    def add_history_entry(self, user, game_type, result_text, is_win=False, time_str=None):
        if not time_str:
            time_str = datetime.now().strftime("%H:%M")
            
        # Insertar siempre arriba (fila 0) para ver lo último primero
        row = 0
        self.table.insertRow(row)
        
        # Hora
        item_time = QTableWidgetItem(time_str)
        item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_time.setForeground(Qt.GlobalColor.gray)
        
        # Usuario
        item_user = QTableWidgetItem(user)
        item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        item_user.setFont(self._font_bold())
        
        # Juego
        name_map = {"dice": "Dados", "roulette": "Ruleta", "slots": "Slots", "highcard": "Cartas"}
        icon_map = {"dice": "dices.svg", "roulette": "disc.svg", "slots": "columns.svg", "highcard": "credit-card.svg"}
        
        g_name = name_map.get(game_type, game_type)
        g_icon = icon_map.get(game_type, "dices.svg")
        
        item_game = QTableWidgetItem(g_name)
        item_game.setIcon(get_icon(g_icon))
        
        # Resultado
        clean_res = result_text.replace(f"@{user}", "").strip()
        item_res = QTableWidgetItem(clean_res)
        
        if is_win:
            item_res.setForeground(Qt.GlobalColor.green)
        else:
            item_res.setForeground(Qt.GlobalColor.red)
            
        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_user)
        self.table.setItem(row, 2, item_game)
        self.table.setItem(row, 3, item_res)
        
        if self.table.rowCount() > 50:
            self.table.removeRow(50)
    
    def _handler_clear_history(self):
        if ModalConfirm(self, "Borrar Historial", "¿Estás seguro? Se eliminarán todos los registros.").exec():
            if self.service.clear_all_history():
                self.table.setRowCount(0)
                ToastNotification(self, "Limpieza", "Historial eliminado", "Status_Green").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo borrar", "Status_Red").show_toast()

    def _handler_toggle_casino(self, checked):
        self.service.set_status(checked)
        status = "HABILITADO" if checked else "DESHABILITADO"
        color = "Status_Green" if checked else "Status_Yellow"
        ToastNotification(self, "Casino", f"Sistema {status}", color).show_toast()

    def _font_bold(self):
        f = self.font(); f.setBold(True); return f