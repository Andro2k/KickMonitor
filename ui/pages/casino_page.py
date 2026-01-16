# ui/pages/casino_page.py

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QCheckBox, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt

from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.factories import create_page_header
from ui.utils import get_icon, get_icon_colored
from ui.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from backend.services.gambling_service import GamblingService
from ui.components.flow_layout import FlowLayout 
from ui.components.casino_cards import GameConfigCard, LimitsCard

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
        self._setup_cards_section() # Aquí usamos los acordeones
        self._setup_history_section()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _setup_header(self):
        h_frame = QFrame()
        h_layout = QHBoxLayout(h_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        v_head = QVBoxLayout()
        v_head.addWidget(create_page_header("Casino & Apuestas", "Sistema de economía y juegos de azar."))
        h_layout.addLayout(v_head)
        
        h_layout.addStretch()
        
        # Interruptor Maestro
        container = QWidget()
        container.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 8px;")
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(15, 8, 15, 8)
        
        lbl = QLabel("Estado del Casino:", styleSheet="border:none; color:#aaa; font-weight:bold; font-size:12px;")
        
        self.chk_enabled = QCheckBox()
        self.chk_enabled.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_enabled.setStyleSheet(get_switch_style())
        self.chk_enabled.setChecked(self.service.get_status())
        self.chk_enabled.toggled.connect(self._handler_toggle_casino)
        
        c_layout.addWidget(lbl)
        c_layout.addWidget(self.chk_enabled)
        
        h_layout.addWidget(container)
        self.main_layout.addWidget(h_frame)

    def _setup_cards_section(self):
        """Contenedor FlowLayout para las tarjetas de configuración (Ahora Acordeones)."""
        self.main_layout.addWidget(QLabel("Configuración de Juegos", objectName="h3"))
        
        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent;")
        
        # FlowLayout para que las tarjetas se acomoden automáticamente
        self.flow_layout = FlowLayout(cards_container, margin=0, spacing=(LAYOUT["spacing"]))
        
        # 1. Tarjeta de Límites Globales (Acordeón)
        self.flow_layout.addWidget(LimitsCard(self.service))
        
        # 2. Tarjetas de Juegos (Acordeones)
        
        # Dados
        self.flow_layout.addWidget(GameConfigCard(
            self.service, "dices.svg", "Dados", 
            [
                ("Win Rate (%):", "gamble_win_rate", 45, True),
                ("Pago (x):", "gamble_multiplier", 2.0, False)
            ]
        ))
        
        # Carta Alta
        self.flow_layout.addWidget(GameConfigCard(
            self.service, "credit-card.svg", "Carta Alta", 
            [
                 ("Pago (x):", "highcard_multiplier", 2.0, False)
            ]
        ))
        
        # Slots
        self.flow_layout.addWidget(GameConfigCard(
            self.service, "columns.svg", "Slots", 
            [
                ("Jackpot (3x) Multi:", "slots_jackpot_x", 10, True)
            ]
        ))

        # Ruleta
        self.flow_layout.addWidget(GameConfigCard(
            self.service, "disc.svg", "Ruleta", 
            [
                ("Pago Número (x):", "roulette_multi_num", 35.0, False),
                ("Pago Color (x):", "roulette_multi_col", 2.0, False)
            ]
        ))

        self.main_layout.addWidget(cards_container)

    def _setup_history_section(self):
        """Tarjeta ancha para la tabla de historial."""
        self.main_layout.addSpacing(LAYOUT["spacing"])
        
        h_sec = QHBoxLayout()
        h_sec.addWidget(QLabel("Historial en Vivo", objectName="h3"))
        h_sec.addStretch()
        
        btn_clean = QPushButton("Limpiar Historial")
        btn_clean.setIcon(get_icon("trash.svg"))
        btn_clean.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clean.setStyleSheet(STYLES["btn_danger_outlined"])
        btn_clean.clicked.connect(self._handler_clear_history)
        h_sec.addWidget(btn_clean)
        
        self.main_layout.addLayout(h_sec)

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
        self.table.setMinimumHeight(350)
        self.table.setStyleSheet(STYLES["table_clean"] + "QTableWidget { border-radius: 16px; }")
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 80)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 120)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 100)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        l_card.addWidget(self.table)
        self.main_layout.addWidget(card)

    # ==========================================
    # LOGICA DE HISTORIAL Y HANDLERS
    # ==========================================
    def load_initial_history(self):
        self.table.setRowCount(0)
        history = self.service.get_history_log(50)
        for row in history:
            ts_str = str(row[0]).split(" ")[1][:5] if " " in str(row[0]) else str(row[0])
            self.add_history_entry(row[1], row[2], row[3], bool(row[4]), ts_str)

    def add_history_entry(self, user, game_type, result_text, is_win=False, time_str=None):
        if not time_str: time_str = datetime.now().strftime("%H:%M")
        row = 0
        self.table.insertRow(row)
        
        item_time = QTableWidgetItem(time_str)
        item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_time.setForeground(Qt.GlobalColor.gray)
        
        item_user = QTableWidgetItem(user)
        item_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        item_user.setFont(self._font_bold())
        
        name_map = {"dice": "Dados", "roulette": "Ruleta", "slots": "Slots", "highcard": "Cartas"}
        icon_map = {"dice": "dices.svg", "roulette": "disc.svg", "slots": "columns.svg", "highcard": "credit-card.svg"}
        
        g_name = name_map.get(game_type, game_type)
        g_icon = icon_map.get(game_type, "dices.svg")
        
        item_game = QTableWidgetItem(g_name)
        item_game.setIcon(get_icon(g_icon))
        
        clean_res = result_text.replace(f"@{user}", "").strip()
        item_res = QTableWidgetItem(clean_res)
        
        if is_win: item_res.setForeground(Qt.GlobalColor.green)
        else: item_res.setForeground(Qt.GlobalColor.red)
            
        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_user)
        self.table.setItem(row, 2, item_game)
        self.table.setItem(row, 3, item_res)
        
        if self.table.rowCount() > 50: self.table.removeRow(50)
    
    def _handler_clear_history(self):
        if ModalConfirm(self, "Borrar Historial", "¿Estás seguro? Se eliminarán todos los registros.").exec():
            if self.service.clear_all_history():
                self.table.setRowCount(0)
                ToastNotification(self, "Limpieza", "Historial eliminado", "status_success").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo borrar", "status_error").show_toast()

    def _handler_toggle_casino(self, checked):
        self.service.set_status(checked)
        status = "HABILITADO" if checked else "DESHABILITADO"
        color = "status_success" if checked else "status_warning"
        ToastNotification(self, "Casino", f"Sistema {status}", color).show_toast()

    def _font_bold(self):
        f = self.font(); f.setBold(True); return f