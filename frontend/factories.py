# frontend/factories.py

from PyQt6.QtWidgets import (
    QComboBox, QPushButton, QWidget, QHBoxLayout, 
    QCheckBox, QSizePolicy, QVBoxLayout, QLabel, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt
from frontend.theme import STYLES, THEME_DARK, get_switch_style
from frontend.utils import get_icon

# ==========================================
# BOTONES Y NAVEGACIÓN
# ==========================================
def create_nav_btn(text: str, icon_name: str, func=None) -> QPushButton:
    btn = QPushButton("  " + text)
    if icon_name: btn.setIcon(get_icon(icon_name))
    
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(STYLES.get("btn_nav", "")) 
    if func: btn.clicked.connect(func)
    
    return btn

def create_icon_btn(icon_name: str, func=None, **kwargs) -> QPushButton:
    btn = QPushButton()
    btn.setIcon(get_icon(icon_name))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
    # 1. Tamaño dinámico (Por defecto 28x28)
    size = kwargs.get("size", 28)
    btn.setFixedSize(size, size)
    
    # 2. Tooltip opcional
    if "tooltip" in kwargs:
        btn.setToolTip(kwargs["tooltip"])
    
    # 3. Estilo base vs Hover personalizado
    color_hover = kwargs.get("color_hover")
    if color_hover:
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; }} 
            QPushButton:hover {{ background-color: {color_hover}; border: 1px solid {color_hover}; }}
        """)
    else:
        btn.setStyleSheet(STYLES.get("btn_icon_ghost", ""))

    if func: btn.clicked.connect(func)
    return btn

def create_table_actions_widget(buttons: list) -> QWidget:
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    for btn in buttons: layout.addWidget(btn)
    return container

def create_switch_widget(checked: bool, func=None, tooltip: str = "") -> QWidget:
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    chk = QCheckBox()
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip: chk.setToolTip(tooltip)
    
    chk.setStyleSheet(get_switch_style("switch-on.svg"))
    chk.setChecked(bool(checked))
    if func: chk.clicked.connect(func)
        
    layout.addWidget(chk)
    return container

# ==========================================
# HEADERS Y TÍTULOS
# ==========================================
def create_page_header(title: str, subtitle: str) -> QWidget:
    container = QWidget()
    l = QVBoxLayout(container)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)

    lbl_title = QLabel(title); lbl_title.setObjectName("h2")
    lbl_sub = QLabel(subtitle); lbl_sub.setObjectName("subtitle")
    
    l.addWidget(lbl_title); l.addWidget(lbl_sub)
    return container

def create_card_header(title: str, icon_name: str = None) -> QWidget:
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(10)

    if icon_name:
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon(icon_name).pixmap(20, 20))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        l.addWidget(lbl_icon)

    lbl_text = QLabel(title); lbl_text.setObjectName("h3"); lbl_text.setStyleSheet("border: none;")
    l.addWidget(lbl_text); l.addStretch()
    return w

def create_section_header(text: str) -> QLabel:
    lbl = QLabel(text); lbl.setObjectName("h4")
    return lbl

# ==========================================
# INPUTS Y FORMULARIOS
# ==========================================
def create_styled_input(placeholder: str = "", is_cmd: bool = False, callback=None) -> QLineEdit:
    inp = QLineEdit()
    if placeholder: inp.setPlaceholderText(placeholder)
    
    inp.setStyleSheet(STYLES.get("input_cmd" if is_cmd else "input", ""))
    
    if callback:
        inp.editingFinished.connect(callback) if is_cmd else inp.textChanged.connect(callback)
    return inp

def create_setting_row(title: str, description: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QGridLayout(container)
    layout.setContentsMargins(0, 10, 0, 10)
    layout.setColumnStretch(0, 1)
    
    lbl_title = QLabel(title); lbl_title.setObjectName("h5")
    lbl_desc = QLabel(description); lbl_desc.setWordWrap(True); lbl_desc.setObjectName("normal")
    
    layout.addWidget(lbl_title, 0, 0); layout.addWidget(lbl_desc, 1, 0)
    layout.addWidget(widget, 0, 1, 2, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)
    return container

def create_styled_button(text: str, style_key: str, func=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(STYLES.get(style_key, "sidebar_btn"))
    if func: btn.clicked.connect(func)
    return btn

def create_styled_combobox(items: list[str], width: int = 0) -> QComboBox:
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLES.get("combobox", ""))
    if width > 0: combo.setFixedWidth(width)
    return combo

# ==========================================
# BOTONES DASHBOARD (GRANDES)
# ==========================================
def create_dashboard_action_btn(text: str, icon_name: str, func=None) -> QPushButton:
    btn = QPushButton(text)
    btn.setIcon(get_icon(icon_name))
    btn.setCheckable(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(28)
    btn.setMinimumWidth(160)
    
    # TRUCO 2: Uso estricto de THEME_DARK para no quemar colores
    btn.setStyleSheet(f"""
        QPushButton {{ 
            background-color: {THEME_DARK['Black_N3']}; 
            color: {THEME_DARK['White_N1']}; 
            border-radius: 8px; font-weight: bold; font-size: 13px; text-align: left; padding-left: 15px; 
            border: 1px solid {THEME_DARK['border']};
        }}
    """)
    if func: btn.clicked.connect(func)
    return btn

def create_shortcut_btn(text: str, icon_name: str, func=None) -> QPushButton:
    btn = QPushButton()
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(64)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    l = QVBoxLayout(btn); l.setSpacing(4); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    ico = QLabel(); ico.setPixmap(get_icon(icon_name).pixmap(24,24))
    ico.setAlignment(Qt.AlignmentFlag.AlignCenter); ico.setStyleSheet("border:none; background:transparent;")
    
    lbl = QLabel(text); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("border:none; font-weight:500; font-size:11px; background:transparent;")
    
    l.addWidget(ico); l.addWidget(lbl)
    btn.setStyleSheet(STYLES.get("btn_shortcut", ""))
    if func: btn.clicked.connect(func)
    return btn

def create_help_btn(func=None) -> QPushButton:
    btn = QPushButton()
    btn.setIcon(get_icon("help-circle.svg")) 
    btn.setFixedSize(32, 32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip("Ver guía de uso")
    
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid {THEME_DARK['border']}; 
            border-radius: 16px;
        }}
        QPushButton:hover {{
            background-color: {THEME_DARK['Black_N2']};
            border-color: {THEME_DARK['White_N1']};
        }}
    """)
    if func: btn.clicked.connect(func)
    return btn