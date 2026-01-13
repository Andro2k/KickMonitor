# ui/factories.py
from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QCheckBox, QFrame, QVBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import Qt, QSize
from ui.theme import STYLES, THEME_DARK, get_switch_style
from ui.utils import get_icon

def create_nav_btn(text: str, icon_name: str, func=None) -> QPushButton:
    """
    Crea el botón estándar de la cabecera (Ej: Importar, Exportar, Nuevo).
    """
    btn = QPushButton("  " + text)
    if icon_name:
        btn.setIcon(get_icon(icon_name))
    
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(STYLES.get("btn_nav", "")) 
    
    if func:
        btn.clicked.connect(func)
    return btn

def create_icon_btn(icon_name: str, func=None, color_hover: str = None, tooltip: str = "") -> QPushButton:
    """
    Crea botones pequeños de acción (Ej: Editar/Eliminar en tablas).
    """
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
    
    # Conectar señal
    if func:
        chk.clicked.connect(func)
        
    layout.addWidget(chk)
    return container

def create_page_header(title: str, subtitle: str) -> QWidget:
    """
    Crea el bloque de título estándar para el inicio de cada página.
    Ej: "Monitor de Chat" (H2) + "Estado del servicio..." (Subtitle)
    """
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

def create_card_header(title: str, icon_name: str = None) -> QWidget:
    """
    Crea una cabecera para las tarjetas (Cards) con icono opcional y título H3.
    Retorna un Widget contenedor listo para añadir al layout de la tarjeta.
    """
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

def create_styled_input(placeholder: str = "", is_cmd: bool = False, callback=None) -> QLineEdit:
    """
    Crea un QLineEdit pre-estilizado.
    is_cmd=True : Estilo verde monospaced (para comandos o rutas).
    is_cmd=False: Estilo normal (para buscadores).
    """
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