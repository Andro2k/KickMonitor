# frontend/factories.py

from PyQt6.QtWidgets import (
    QComboBox, QFrame, QPushButton, QWidget, QHBoxLayout, 
    QCheckBox, QSizePolicy, QVBoxLayout, QLabel, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt
from frontend.theme import STYLES, THEME_DARK, get_switch_style
from frontend.utils import get_icon

# ==========================================
# BOTONES Y NAVEGACIÓN
# ==========================================

def create_nav_btn(text: str, icon_name: str, func=None) -> QPushButton:
    """Crea el botón estándar de la cabecera (Ej: Importar, Exportar, Nuevo)."""
    btn = QPushButton("  " + text)
    if icon_name:
        btn.setIcon(get_icon(icon_name))
    
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(STYLES.get("btn_nav", "")) 
    
    if func:
        btn.clicked.connect(func)
    return btn

def create_icon_btn(icon_name: str, func=None, color_hover: str = None, tooltip: str = "") -> QPushButton:
    """Crea botones pequeños de acción (Ej: Editar/Eliminar en tablas)."""
    btn = QPushButton()
    btn.setIcon(get_icon(icon_name))
    btn.setFixedSize(28, 28)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        btn.setToolTip(tooltip)
    
    # Estilo base transparente
    base_style = STYLES.get("btn_icon_ghost", "")
    if color_hover:
        custom_style = f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; }} 
            QPushButton:hover {{ background-color: {color_hover}; border: 1px solid {color_hover}; }}
        """
        btn.setStyleSheet(custom_style)
    else:
        btn.setStyleSheet(base_style)

    if func:
        btn.clicked.connect(func)
    return btn

def create_table_actions_widget(buttons: list) -> QWidget:
    """
    NUEVO: Crea un contenedor centrado para alojar botones de acción en una celda de tabla.
    Evita repetir la creación de QWidget + Layout + Margins en cada página.
    """
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    for btn in buttons:
        layout.addWidget(btn)
        
    return container

def create_switch_widget(checked: bool, func, tooltip: str = "") -> QWidget:
    """
    Crea un QCheckBox estilizado como Switch dentro de un contenedor centrado.
    Ideal para celdas de tablas.
    """
    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    chk = QCheckBox()
    chk.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        chk.setToolTip(tooltip)
    
    chk.setStyleSheet(get_switch_style("switch-on.svg"))
    chk.setChecked(bool(checked))
    
    if func:
        chk.clicked.connect(func)
        
    layout.addWidget(chk)
    return container

# ==========================================
# HEADERS Y TÍTULOS
# ==========================================
def create_page_header(title: str, subtitle: str) -> QWidget:
    """Crea el bloque de título estándar para el inicio de cada página."""
    container = QWidget()
    l = QVBoxLayout(container)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)

    lbl_title = QLabel(title)
    lbl_title.setObjectName("h2")
    
    lbl_sub = QLabel(subtitle)
    lbl_sub.setObjectName("subtitle")
    
    l.addWidget(lbl_title)
    l.addWidget(lbl_sub)
    
    return container

# -- Dashboard Page --
def create_card_header(title: str, icon_name: str = None) -> QWidget:
    """Crea una cabecera para las tarjetas (Cards) con icono opcional."""
    w = QWidget()
    l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(10)

    if icon_name:
        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon(icon_name).pixmap(20, 20))
        lbl_icon.setStyleSheet("border: none; opacity: 0.8;")
        l.addWidget(lbl_icon)

    lbl_text = QLabel(title)
    lbl_text.setObjectName("h3")
    lbl_text.setStyleSheet("border: none;")
    
    l.addWidget(lbl_text)
    l.addStretch()
    
    return w

# -- Settings Page --
def create_header_page(title: str, description: str) -> QFrame:
    """Crea el encabezado usado en Settings."""
    frame = QFrame()
    frame.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']};")
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15,10,15,10)
    
    lbl_head = QLabel(title)
    lbl_head.setObjectName("h1")
    
    lbl_desc = QLabel(description)
    lbl_desc.setObjectName("subtitle")
    
    layout.addWidget(lbl_head)
    layout.addWidget(lbl_desc)
    
    return frame
def create_section_header(text: str) -> QLabel:
    """Crea el encabezado de sección con línea divisoria visual implícita"""
    lbl = QLabel(text)
    lbl.setObjectName("h4")
    return lbl

# ==========================================
# INPUTS Y FORMULARIOS
# ==========================================

def create_styled_input(placeholder: str = "", is_cmd: bool = False, callback=None) -> QLineEdit:
    """Crea un QLineEdit pre-estilizado."""
    inp = QLineEdit()
    if placeholder:
        inp.setPlaceholderText(placeholder)
    
    style_key = "input_cmd" if is_cmd else "input"
    inp.setStyleSheet(STYLES.get(style_key, ""))
    
    if callback:
        if is_cmd:
            inp.editingFinished.connect(callback)
        else:
            inp.textChanged.connect(callback)
            
    return inp

# -- Settings Page --
def create_setting_row(title: str, description: str, widget: QWidget) -> QWidget:
    """Crea una fila de configuración: Texto izquierda | Widget derecha."""
    container = QWidget()
    layout = QGridLayout(container)
    layout.setContentsMargins(0, 10, 0, 10)
    layout.setColumnStretch(0, 1)
    
    lbl_title = QLabel(title)
    lbl_title.setObjectName("h5")
    
    lbl_desc = QLabel(description)
    lbl_desc.setWordWrap(True)
    lbl_desc.setObjectName("normal")
    
    layout.addWidget(lbl_title, 0, 0)
    layout.addWidget(lbl_desc, 1, 0)
    layout.addWidget(widget, 0, 1, 2, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)
    
    return container
def create_styled_button(text: str, style_key: str, func=None) -> QPushButton:
    """Crea un botón genérico aplicando una clave del diccionario STYLES."""
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(STYLES.get(style_key, "sidebar_btn"))
    
    if func:
        btn.clicked.connect(func)
        
    return btn
def create_styled_combobox(items: list[str], width: int = 0) -> QComboBox:
    """Crea un ComboBox pre-estilizado."""
    combo = QComboBox()
    combo.addItems(items)
    combo.setStyleSheet(STYLES.get("combobox", ""))
    
    if width > 0:
        combo.setFixedWidth(width)
        
    return combo

# ==========================================
# BOTONES DASHBOARD (GRANDES) DASHBOARD PAGE
# ==========================================

def create_dashboard_action_btn(text: str, icon_name: str, func=None) -> QPushButton:
    """Crea el botón ancho de acción principal (Ej: Conectar Kick, Spotify)."""
    btn = QPushButton(text)
    btn.setIcon(get_icon(icon_name))
    btn.setCheckable(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(28)
    btn.setMinimumWidth(160)
    
    btn.setStyleSheet(f"""
        QPushButton {{ 
            background-color: {THEME_DARK['Black_N3']}; 
            color: {THEME_DARK['White_N1']}; 
            border-radius: 8px; 
            font-weight: bold; font-size: 13px; text-align: left; padding-left: 15px; 
            border: 1px solid {THEME_DARK['border']};
        }}
    """)
    
    if func:
        btn.clicked.connect(func)
    return btn

def create_shortcut_btn(text: str, icon_name: str, func=None) -> QPushButton:
    """Crea el botón cuadrado vertical para el grid de accesos directos."""
    btn = QPushButton()
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(64)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    l = QVBoxLayout(btn)
    l.setSpacing(4)
    l.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    ico = QLabel()
    ico.setPixmap(get_icon(icon_name).pixmap(24,24))
    ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
    ico.setStyleSheet("border:none; background:transparent;")
    
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("border:none; font-weight:500; font-size:11px; background:transparent;")
    
    l.addWidget(ico)
    l.addWidget(lbl)
    
    btn.setStyleSheet(STYLES.get("btn_shortcut", ""))
    
    if func:
        btn.clicked.connect(func)
        
    return btn