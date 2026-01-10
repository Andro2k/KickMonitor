# ui/theme.py
import sys
import os

# ==========================================
# 1. SISTEMA DE RUTAS (Para CSS/QSS)
# ==========================================
def asset_url(filename: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, "assets", "icons", filename).replace("\\", "/")

# ==========================================
# 2. DEFINICIONES DE DISEÑO (TOKENS)
# ==========================================
class Palette:
    """
    Sistema de Color 'Kick Dark'.
    """
    # --- 1. Paleta Base ---
    Black_N0       = "#0B0B0C"
    Black_N1       = "#1E1E1E"
    Black_N2       = "#252525"
    Black_N3       = "#2D2D2D"
    Black_N4       = "#3E3E3E"
    Black_Pure     = "#000000"
    
    Gray_N1        = "#A0A0A0"
    Gray_N2        = "#666666"
    Gray_Border    = "#454545"
    
    White_N1       = "#FFFFFF"
    White_Alpha_08 = "rgba(255,255,255,0.08)"
    
    NeonGreen_Main  = "#53fc18"
    NeonGreen_Light = "#6aff2e"
    NeonGreen_Dark  = "#3da812"
    
    Status_Red      = "#FF453A"
    Status_Green    = "#32D74B"
    Status_Yellow   = "#FFD60A"
    Status_Blue     = "#0A84FF"

    # --- 2. Alias Funcionales ---    
    border        = Gray_Border
    info          = Status_Blue

class Dims:
    """Dimensiones y Espaciados."""
    radius = {
        "card":   "12px",
        "modal":  "16px",
        "input":  "8px",
        "button": "8px",
        "chip":   "6px",
        "scroll": "4px"
    }
    layout = {
        "outer": (16,16,16,16), 
        "inner": (8,8,8,8), 
        "margins": (12,12,12,12), 
        "spacing": 8
    }

class Fonts:
    """Configuración tipográfica."""
    family = "Segoe UI"
    h1 = "18pt"    # ~24px
    h2 = "15pt"    # ~20px
    h3 = "12pt"    # ~16px
    body = "10pt"  # ~14px
    small = "9pt"  # ~12px

# ==========================================
# 3. HOJA DE ESTILOS GLOBAL (QSS MAESTRO)
# ==========================================
def get_sheet(is_dark: bool = True) -> str:
    c = Palette
    r = Dims.radius
    f = Fonts
    
    return f"""
    /* --- BASE --- */
    QMainWindow, QWidget {{ 
        background-color: {c.Black_N1}; color: {c.White_N1}; 
        font-family: "{f.family}"; font-size: {f.body};
    }}
    
    /* --- TEXTOS --- */
    QLabel {{ background: transparent; border: none; }}
    QLabel#h1 {{ font-size: {f.h1}; font-weight: bold; margin-bottom: 4px; }}
    QLabel#h2 {{ font-size: {f.h2}; font-weight: bold; margin-bottom: 2px; }}
    QLabel#h3 {{ font-size: {f.h3}; font-weight: 600; color: {c.White_N1}; }}
    QLabel#normal {{ font-size: {f.body}; font-weight: 500; color: {c.White_N1}; }}
    QLabel#subtitle {{ font-size: {f.small}; color: {c.Gray_N1}; }}
    
    /* --- CONTENEDORES --- */
    QFrame {{ border: none; }}
    QFrame#Sidebar {{ background-color: {c.Black_N2}; border-right: 1px solid {c.border}; }}
    QScrollArea {{ background: transparent; border: none; }}

    /* --- INPUTS --- */
    QLineEdit, QPlainTextEdit {{ 
        background-color: {c.Black_N2}; color: {c.White_N1}; 
        border-radius: {r['input']}; padding: 4px; 
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{ 
        border: 1px solid {c.NeonGreen_Main}; background-color: {c.Black_N3}; 
    }}
    QLineEdit[readOnly="true"] {{ color: {c.NeonGreen_Main}; font-family: Consolas; }}

    /* --- BOTONES --- */
    QPushButton {{ 
        background-color: {c.Black_N2}; color: {c.White_N1}; 
        border-radius: {r['button']}; padding: 6px;
    }}
    QPushButton:hover {{ background-color: {c.White_Alpha_08}; border-color: {c.Gray_N1}; }}
    QPushButton:pressed {{ background-color: {c.border}; }}
    
    /* Botón Sidebar */
    QPushButton#MenuBtnMini {{ 
        background: transparent; border: none; margin: 4px; padding: 8px; border-radius: 12px; 
    }}
    QPushButton#MenuBtnMini:hover {{ background-color: {c.White_Alpha_08}; }}
    QPushButton#MenuBtnMini:checked {{ 
        background-color: rgba(83, 252, 24, 0.1); 
        border: 1px solid {c.NeonGreen_Dark}; 
    }}

    /* --- SCROLLBARS --- */
    QScrollBar:vertical {{ background: {c.Black_N1}; width: 8px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: #444; border-radius: {r['scroll']}; min-height: 20px; }}
    QScrollBar::handle:vertical:hover {{ background: {c.NeonGreen_Main}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: {c.Black_N1}; height: 8px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: #444; border-radius: {r['scroll']}; min-width: 20px; }}
    QScrollBar::handle:horizontal:hover {{ background: {c.NeonGreen_Main}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """

# ==========================================
# 4. ESTILOS ESPECÍFICOS (REUTILIZABLES)
# ==========================================
c = Palette
r = Dims.radius

STYLES = {
    "card": f"""
        QFrame {{
            background-color: {c.Black_N3}; 
            border-radius: {r['card']}; 
        }}
    """,
    "input": f"""
        QLineEdit {{ background: {c.Black_N2}; border-radius: {r['input']}; padding: 8px; color: white; }}
        QLineEdit:focus {{ border: 1px solid {c.NeonGreen_Main}; }}
    """,
    "input_cmd": f"""
        QLineEdit {{ 
            background: {c.Black_N2}; color: {c.NeonGreen_Main}; font-weight: bold; font-family: Consolas;
            border-radius: 4px; padding: 4px; 
        }}
        QLineEdit:focus {{ border-color: {c.NeonGreen_Main}; }}
    """,
    "url_readonly": f"""
        QLineEdit {{ background: {c.Black_N2}; color: {c.NeonGreen_Main}; font-family: Consolas; }}
    """,
    "spinbox_modern": f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.Black_N2};
            color: {c.White_N1};
            border-radius: {r['input']};
            padding: 6px 10px;
            padding-right: 25px;
            selection-background-color: {c.NeonGreen_Main};
            selection-color: {c.Black_Pure};
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {c.NeonGreen_Main};
            background-color: {c.Black_N1};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border; subcontrol-position: top right; width: 16px;
            border-left: 0.5px solid {c.border}; border-bottom: 0.5px solid {c.border}; 
            border-top-right-radius: {r['input']}; background-color: {c.Black_N2};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right; width: 16px;
            border-left: 0.5px solid {c.border}; border-top: 0.5px solid {c.border};
            border-bottom-right-radius: {r['input']}; background-color: {c.Black_N2};
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {c.Black_N1}; border: 0.5px solid {c.NeonGreen_Main}; 
        }}
    """,
    "combobox": f"""
        /* --- ESTADO BASE --- */
        QComboBox {{
            background-color: {c.Black_N2};
            color: {c.White_N1};
            border-radius: {r['input']};
            padding: 6px;
            min-height: 20px;
        }}
        
        /* --- HOVER Y FOCUS --- */
        QComboBox:hover, QComboBox:focus {{
            border: 1px solid {c.NeonGreen_Main};
            background-color: {c.Black_N3};
        }}

        /* --- FLECHA (DROP-DOWN) --- */
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
        }}

        /* --- LISTA DESPLEGABLE (POPUP) --- */
        QComboBox QAbstractItemView {{
            background-color: {c.Black_N3};
            color: {c.White_N1};
            selection-background-color: {c.NeonGreen_Main};
            selection-color: {c.Black_Pure};
            padding: 4px;
        }}
    """,
    "list_clean": f"""
        QListWidget {{ background-color: {c.Black_N3}; outline: none; }}
        QListWidget::item {{ border-bottom: 1px solid {c.Black_N4}; padding: 6px; }}
        QListWidget::item:hover {{ background: {c.White_Alpha_08}; }}
        QListWidget::item:selected {{ background: {c.Black_N4}; }}
    """,
    "table_clean": f"""
        QTableWidget {{
            background-color: {c.Black_N3}; gridline-color: {c.Black_N4}; outline: none;
        }}
        QHeaderView::section {{
            background-color: {c.Black_N2}; color: {c.Gray_N1}; border: none; border-bottom: 1px solid {c.border};
            padding: 8px; font-weight: bold; text-transform: uppercase; font-size: 11px;
        }}
        QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {c.Black_N4}; }}
        QTableWidget::item:selected {{ background-color: {c.White_Alpha_08}; color: {c.NeonGreen_Main}; }}
    """,
    "tabs_base": f"""
        QTabWidget::pane {{ border: 1px solid {c.border}; }}
        QTabBar::tab {{
            background: {c.Black_N2}; color: {c.Gray_N1}; padding: 10px 15px;
            border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
        }}
        QTabBar::tab:selected {{ background: {c.Black_N3}; color: {c.NeonGreen_Main}; border-bottom: 2px solid {c.NeonGreen_Main}; }}
        QTabBar::tab:hover {{ color: {c.White_N1}; background: {c.White_Alpha_08}; }}
    """,
    "sidebar_btn": f"""
        QPushButton {{
            background-color: transparent;
            color: {c.Gray_N1};
            border: none;
            border-radius: 8px;
            text-align: left;
            padding: 6px;
            font-weight: 500;
            margin: 2px;
        }}
        QPushButton:hover {{
            background-color: {c.White_Alpha_08};
            color: {c.White_N1};
        }}
        QPushButton:checked {{
            background-color: rgba(83, 252, 24, 0.15);
            color: {c.NeonGreen_Main};
            font-weight: bold;
        }}
    """,
    "sidebar_container": f"""
        QFrame {{
            background-color: {c.Black_N1}; 
            border-right: 0.5px solid {c.border};
        }}
    """
}

# ==========================================
# 5. HELPERS VISUALES
# ==========================================
def get_switch_style(on_icon_name: str = "switch-on.svg") -> str:
    # Usamos asset_url porque CSS necesita rutas con '/'
    off = asset_url("switch-off.svg")
    on = asset_url(on_icon_name)
    return f"""
        QCheckBox {{ background: transparent; spacing: 5px; color: {Palette.Gray_N1}; }}
        QCheckBox::indicator {{ width: 28px; height: 24px; border: none; }}
        QCheckBox::indicator:unchecked {{ image: url({off}); }}
        QCheckBox::indicator:checked {{ image: url({on}); }}
    """

# ==========================================
# 6. EXPORTACIONES
# ==========================================
COLORS = {k: v for k, v in Palette.__dict__.items() if not k.startswith("__")}
LAYOUT = Dims.layout
RADIUS = Dims.radius
THEME_DARK = COLORS 

TOAST_THEME = {
    "bg": "#232324",
    "states": { 
        "Status_Green": Palette.Status_Green, 
        "Status_Red":  Palette.Status_Red, 
        "Status_Yellow": Palette.Status_Yellow, 
        "info":    Palette.info 
    }
}