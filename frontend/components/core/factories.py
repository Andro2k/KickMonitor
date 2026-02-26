# frontend/factories.py

from PyQt6.QtWidgets import (
    QComboBox, QFrame, QPushButton, QWidget, QHBoxLayout, 
    QCheckBox, QSizePolicy, QVBoxLayout, QLabel, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from frontend.components.core.layouts import FlowLayout
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
    combo.setStyleSheet(STYLES.get("combobox_modern", ""))
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
            border-radius: 16px;
        }}
        QPushButton:hover {{
            background-color: {THEME_DARK['Black_N2']};
            border-color: {THEME_DARK['White_N1']};
        }}
    """)
    if func: btn.clicked.connect(func)
    return btn

# =============================================================================
# INPUTS DINÁMICOS (TAGS Y ALIAS)
# =============================================================================
class ModernPill(QFrame):
    """Componente visual reutilizable para Etiquetas (Tags) o Alias."""
    def __init__(self, text: str, remove_callback, theme="green", parent=None):
        super().__init__(parent)
        self.text = text
        self.setObjectName("pill")
        
        # Sistema de Temas
        if theme == "green":
            bg_color = "rgba(83, 252, 24, 0.15)"
            border_color = "rgba(83, 252, 24, 0.3)"
            text_color = "#53fc18"
            hover_bg = "rgba(255, 76, 76, 0.2)" # Rojo suave al pasar el mouse
        else: 
            bg_color = "#191919"
            border_color = "#4a4a5a"
            text_color = "#d1d1e0"
            hover_bg = "#3d3d4a"

        self.setStyleSheet(f"""
            #pill {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; }}
            QLabel {{ color: {text_color}; font-size: 12px; font-weight: bold; border: none; padding-left: 4px; background: transparent;}}
            QPushButton {{
                border: none; border-radius: 10px; background: transparent;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)
        
        lbl = QLabel(text)
        
        # --- AQUÍ ESTÁ TU NUEVO BOTÓN CON SVG ---
        btn = QPushButton()
        btn.setIcon(get_icon("x.svg")) 
        from PyQt6.QtCore import QSize
        btn.setIconSize(QSize(14, 14))
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: remove_callback(self))
        
        layout.addWidget(lbl)
        layout.addWidget(btn)


class DynamicTagInput(QWidget):
    """Contenedor universal para gestionar inputs de etiquetas, alias o usuarios."""
    tags_changed = pyqtSignal()
    
    def __init__(self, placeholder="Escribe y presiona Enter...", theme="green", max_tags=10, max_length=30, prefix="", parent=None):
        super().__init__(parent)
        self.tags = []
        self.theme = theme
        self.max_tags = max_tags
        self.max_length = max_length
        self.prefix = prefix 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setMaxLength(100) 
        self.input.returnPressed.connect(self._add_from_input)
        
        self.flow_container = QWidget()
        self.flow_container.setStyleSheet("background-color: transparent;")
        self.flow_layout = FlowLayout(self.flow_container, margin=0, spacing=5, expand_items=False)
        
        layout.addWidget(self.input)
        layout.addWidget(self.flow_container)

    def _add_from_input(self):
        text = self.input.text().strip().lower()
        if text:
            for t in text.split(","):
                if len(self.tags) >= self.max_tags:
                    break 
                    
                clean_t = t.strip()
                if clean_t:
                    clean_t = clean_t.replace(" ", "-")
                    if self.prefix and not clean_t.startswith(self.prefix):
                        clean_t = self.prefix + clean_t
                    
                    if len(clean_t) > self.max_length:
                        clean_t = clean_t[:self.max_length]
                        
                    if clean_t not in self.tags:
                        self.tags.append(clean_t)
                        pill = ModernPill(clean_t, self._remove_tag, theme=self.theme)
                        self.flow_layout.addWidget(pill)
            self.input.clear()
            self.tags_changed.emit()

    def _remove_tag(self, pill):
        if pill.text in self.tags:
            self.tags.remove(pill.text)
        self.flow_layout.removeWidget(pill)
        pill.deleteLater()
        self.tags_changed.emit()

    def get_tags_string(self):
        return ",".join(self.tags)

    def set_tags_from_string(self, text):
        self.tags.clear()
        for i in reversed(range(self.flow_layout.count())):
            w = self.flow_layout.itemAt(i).widget()
            if w:
                self.flow_layout.removeWidget(w)
                w.deleteLater()
                
        if not text: return
        for t in text.split(","):
            if len(self.tags) >= self.max_tags: break
            
            clean_t = t.strip()
            if clean_t:
                clean_t = clean_t.replace(" ", "-")
                
                if self.prefix and not clean_t.startswith(self.prefix):
                    clean_t = self.prefix + clean_t
                if len(clean_t) > self.max_length:
                    clean_t = clean_t[:self.max_length]
                self.tags.append(clean_t)
                pill = ModernPill(clean_t, self._remove_tag, theme=self.theme)
                self.flow_layout.addWidget(pill)