# frontend/theme.py

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
    Sistema de Color 'Kick Midnight' (Deep Dark).
    """
    # --- 1. Paleta Base (Deep Dark) ---
    Black_N0       = "#000000" # Pure Black (Fondo de ventana base si se requiere)
    Black_N1       = "#050505" # Fondo Principal (Main Window)
    Black_N2       = "#191919" # Tarjetas / Paneles (Surface)
    Black_N3       = "#262626" # Inputs / Hover States
    Black_N4       = "#333333" # Bordes fuertes / Elementos activos
    
    # --- 2. Grises ---
    Gray_N1        = "#8B8B8B" # Texto Secundario / Iconos inactivos
    Gray_N2        = "#666666" # Texto Terciario / Placeholders
    Gray_Border    = "#333333" # Bordes sutiles (Igual a N4 para integración)
    
    # --- 3. Blancos ---
    White_N1       = "#FFFFFF"
    White_Alpha_08 = "rgba(255,255,255,0.08)"
    White_Alpha_05 = "rgba(255,255,255,0.05)"
    
    # --- 4. Acentos (Kick Green) ---
    NeonGreen_Main  = "#53fc18"
    NeonGreen_Light = "#6aff2e"
    NeonGreen_Dark  = "#3da812"
    
    # --- 5. Estados ---
    status_error      = "#FF453A"
    status_success    = "#32D74B"
    status_warning   = "#FFD60A"
    status_info     = "#0A84FF"

    # --- 6. Alias Funcionales ---    
    border        = Gray_Border
    info          = status_info

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
        "level_01": (10,10,10,10),
        "level_02": (16,16,16,16), 
        "level_03": (20,20,20,20), 
        "space_01": 12
    }

class Fonts:
    """Configuración tipográfica."""
    family = "Segoe UI"
    h1 = "18pt"    # ~24px
    h2 = "14pt"    # ~20px
    h3 = "12pt"    # ~16px
    body = "10pt"  # ~14px

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
    QLabel {{ background: transparent; border: none; padding: 0px; }}
    
    QLabel#h1 {{ 
        font-size: {f.h1}; font-weight: bold; 
        padding: 0px 5px 0px -5px;
    }}
    
    QLabel#h2 {{ 
        font-size: {f.h2}; font-weight: bold; 
        padding: 0px 5px 0px -5px;
    }}
    
    QLabel#h3 {{ 
        font-size: {f.h3}; font-weight: bold; 
        color: {c.White_N1}; 
        padding: 0px 5px 0px -5px;
    }}

    QLabel#h4 {{ 
        font-size: {f.h3}; font-weight: bold; 
        color: {c.White_N1};
        border-bottom: 1px solid #333;
        padding: 0px 5px 8px -3px;
    }}

    QLabel#h5 {{ 
        font-size: {f.body}; 
        font-weight: bold; 
        color: {c.Gray_N1}; 
        padding: 0px 5px 0px -3px;
    }}
    
    QLabel#normal {{ font-size: {f.body}; font-weight: 500; color: {c.Gray_N2}; }}
    QLabel#subtitle {{ font-size: {f.body}; color: {c.Gray_N2}; }}
    
    /* --- CONTENEDORES --- */
    QFrame {{ border: none; }}
    QFrame#Sidebar {{ background-color: {c.Black_N2}; border-right: 1px solid {c.border}; }}
    QScrollArea {{ background: transparent; border: none; }}

    /* --- INPUTS --- */
    QLineEdit, QPlainTextEdit {{ 
        background-color: {c.Black_N2}; color: {c.White_N1}; 
        border-radius: {r['input']}; padding: 4px;
        border: 1px solid {c.border};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{ 
        border: 1px solid {c.NeonGreen_Main}; background-color: {c.Black_N3}; 
    }}
    QLineEdit[readOnly="true"] {{ color: {c.NeonGreen_Main}; font-family: Consolas; }}
    
    /* Botón Sidebar */
    QPushButton#MenuBtnMini {{ 
        background: transparent; border: none; margin: 4px; padding: 8px; border-radius: 12px; 
    }}
    QPushButton#MenuBtnMini:hover {{ background-color: {c.White_Alpha_08}; }}
    QPushButton#MenuBtnMini:checked {{ 
        background-color: rgba(83, 252, 24, 0.1); 
        border: 1px solid {c.NeonGreen_Dark}; 
    }}

    /* --- Sliders --- */
    QSlider::groove:horizontal {{
        border: 1px solid {c.Black_N4}; height: 6px; border-radius: 3px; background-color: transparent;
    }}
    QSlider::handle:horizontal {{
        background-color: {c.NeonGreen_Main}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
    }}
    

    /* --- SCROLLBARS --- */
    
    /* VERTICAL */
    QScrollBar:vertical {{ background: {c.Black_N1}; width: 8px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: #444; border-radius: {r['scroll']}; min-height: 20px; }}
    QScrollBar::handle:vertical:hover {{ background: {c.NeonGreen_Main}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    /* HORIZONTAL */
    QScrollBar:horizontal {{ background: {c.Black_N1}; height: 8px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: #444; border-radius: {r['scroll']}; min-width: 20px; }}
    QScrollBar::handle:horizontal:hover {{ background: {c.NeonGreen_Main}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """

# ==========================================
# 4. ESTILOS ESPECÍFICOS (REUTILIZABLES)
# ==========================================
c = Palette
r = Dims.radius

STYLES = {
    # --- CONTENEDORES ---
    "card": f"""
        QFrame {{
            background-color: {c.Black_N2}; 
            border-radius: {r['card']}; 
        }}
    """,
    "card_large": f"""
        QFrame {{
            background-color: {c.Black_N2}; 
            border-radius: 16px; 
        }}
    """,
    # --- LABELS ---
    "label_readonly": f"""
        QLabel {{ 
            background: {c.Black_N3}; color: {c.Gray_N1}; 
            font-family: Consolas; border: 1px solid {c.border};
            border-radius: {r['input']}; padding: 4px;
        }}
    """,
    "label_text": f"""
        QLabel {{font-weight: bold; font-size: 13px; color: white; border: none; background: transparent;}}
    """,
    "label_title": f"""
        QLabel {{ 
            border:none; font-size: 14px; 
            font-weight: bold; color: white;
        }}
    """,
    # --- INPUTS ---
    "input": f"""
        QLineEdit {{ background: {c.Black_N3}; border-radius: {r['input']}; padding: 6px; color: white; }}
        QLineEdit:focus {{ border: 1px solid {c.Gray_N1}; }}
    """,
    "input_cmd": f"""
        QLineEdit {{ 
            background: {c.Black_N3}; color: {c.Gray_N1}; font-weight: bold; font-family: Consolas;
            border-radius: 4px; padding: 6px; border: 1px solid {c.border};
        }}
        QLineEdit:focus {{ border-color: {c.Gray_N1}; }}
    """,
    "input_readonly": f"""
        QLineEdit {{ 
            background: {c.Black_N3}; color: {c.Gray_N1}; 
            font-family: Consolas; border: 1px solid {c.border};
            border-radius: {r['input']}; padding: 4px;
        }}
    """,
    
    # --- LOGS Y CONSOLAS ---
    "text_edit_log": f"""
        QTextEdit {{
            background-color: {c.Black_N2};
            color: {c.White_N1};
            border: 1px solid {c.Black_N2};
            padding: 12px;
            font-family: 'Segoe UI', monospace;
            font-size: 13px;
        }}
    """,
    "text_edit_console": f"""
         QTextEdit {{
            background-color: {c.Black_N2}; color: {c.Gray_N1};
            font-family: Consolas, monospace; font-size: 12px; padding: 10px; border: none;
        }}
    """,
    "textarea": f"""
        QPlainTextEdit {{
            background-color: {c.Black_N3};
            color: {c.White_N1};
            border: 1px solid {c.border};
            border-radius: {r['input']};
            padding: 8px;
        }}
        QPlainTextEdit:focus {{
            border: 1px solid {c.Gray_N1}; 
        }}
    """,
    "text_browser": f"""
        QTextBrowser {{
            background-color: {c.Black_N4};
            color: #DDD;
            border: 1px solid {c.border};
            border-radius: {r['input']};
            padding: 6px;
            font-size: 12px;
        }}
    """,

    # --- BOTONES ---
    # Botón estándar para barra superior (Importar/Exportar)
    "btn_nav": f"""
        QPushButton {{
            background-color: {c.Black_N2}; color: {c.White_N1};
            padding: 6px 12px; border: 1px solid {c.Black_N2}; border-radius: 6px; 
            font-size: 12px; font-weight: bold;
            
        }}
        QPushButton:hover {{ 
            background-color: {c.Black_N4}; border-color: {c.NeonGreen_Main}; 
        }}
    """,
    # Botón sólido primario (Aplicar, Guardar)
    "btn_primary": f"""
        QPushButton {{ 
            background-color: rgba(83, 252, 24, 0.15); border: 1px solid {c.NeonGreen_Main};
            color: {c.NeonGreen_Main};
            padding: 6px 12px; margin: 2px; border-radius: 6px;
            font-size: 12px; font-weight: bold; 
        }}
        QPushButton:hover {{ background-color: {c.Black_N3}; }}
    """,
    
    "btn_primary_disabled": f"""
        QPushButton {{ 
            background-color: {c.Black_N4}; border: 1px solid {c.Black_N4};
            color: {c.Gray_N2};
            padding: 6px 12px; margin: 2px; border-radius: 6px;
            font-size: 12px; font-weight: bold; 
        }}
    """,
    # Botón delineado (Configurar, Gestionar)
    "btn_outlined": f"""
        QPushButton {{ 
            background-color: {c.Black_N3}; color: {c.White_N1}; 
            padding: 6px 12px; margin: 2px; border: 1px solid {c.Gray_Border}; border-radius: 6px;
            font-size: 12px; font-weight: bold; 
        }} 
        QPushButton:hover {{ border-color: {c.NeonGreen_Main}; color: {c.White_N1}; }}
    """,
    # Botón "Peligroso" delineado (Desvincular, Borrar todo)
    "btn_danger_outlined": f"""
        QPushButton {{
            background-color: rgba(239, 83, 80, 0.2); color: {c.White_N1};
            padding: 6px 12px; border: 1px solid {c.status_error}; border-radius: 6px;
            font-weight: 500;
        }}
        QPushButton:hover {{ background-color: {c.status_error}; color: white; }}
    """,
    # Botón pequeño de acción (Editar, Borrar en tablas)
    "btn_icon_ghost": f"""
        QPushButton {{ background: transparent; border: none; border-radius: 6px; }} 
        QPushButton:hover {{ background-color: {c.White_Alpha_08}; }}
    """,
    # Botón grande del Dashboard (Accesos directos)
    "btn_shortcut": f"""
        QPushButton {{ 
            background-color: {c.Black_N4}; 
            border-radius: 10px; 
            border: 1px solid {c.Black_N2};
        }} 
        QPushButton:hover {{ 
            background-color: {c.Black_N2}; 
            border-color: {c.NeonGreen_Main}; 
        }}
    """,
    # Botón verde translucido
    "btn_toggle": f"""
        QPushButton {{
            background-color: {c.Black_N3};
            border: 1px solid {c.border};
            border-radius: 6px;
            color: {c.White_N1};
            padding: 6px 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c.Black_N4};
            border-color: {c.Gray_N1};
        }}
        /* ESTADO ACTIVO (CHECKED) - Reemplaza tu lógica manual */
        QPushButton:checked {{
            background-color: rgba(83, 252, 24, 0.15); 
            border: 1px solid {c.NeonGreen_Main};
            color: {c.NeonGreen_Main};
        }}
    """,

    # --- LISTAS Y TABLAS ---
    "list_clean": f"""
        QListWidget {{ background-color: {c.Black_N2}; outline: none; border-radius: {r['card']}; }}
        QListWidget::item {{ border-bottom: 1px solid {c.Black_N4}; padding: 6px; }}
        QListWidget::item:hover {{ background: {c.White_Alpha_08}; }}
        QListWidget::item:selected {{ background: {c.Black_N4}; }}
    """,
    "table_clean": f"""
        QTableWidget {{
            background-color: {c.Black_N2}; gridline-color: {c.Black_N4}; outline: none; border: none;
        }}
        QHeaderView::section {{
            background-color: {c.Black_N3}; color: {c.Gray_N1}; border: none; border-bottom: 1px solid {c.border};
            padding: 8px; font-weight: bold; text-transform: uppercase; font-size: 11px;
        }}
        QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {c.Black_N4}; }}
        QTableWidget::item:selected {{ background-color: {c.White_Alpha_08}; color: {c.NeonGreen_Main}; }}
    """,
    
    # --- COMPLEX WIDGETS ---
    "combobox": f"""
        QComboBox {{
            background-color: {c.Black_N3}; border: 1px solid {c.Black_N4};
            color: {c.White_N1}; border-radius: 6px; padding: 6px 12px; min-height: 16px;
        }}
        QComboBox:hover, QComboBox:focus {{
            border: 1px solid {c.Gray_N1}; background-color: {c.Black_N2};
        }}
        
        QComboBox::drop-down{{border: none;}}
        QComboBox::down-arrow {{image: url({asset_url("chevron-down.svg")});}}
        QComboBox::down-arrow::on {{image: url({asset_url("chevron-up.svg")});}}

        QComboBox QAbstractItemView {{
            background-color: {c.NeonGreen_Dark}; color: {c.Black_N3};
            selection-background-color: {c.NeonGreen_Main}; selection-color: {c.Black_N0}; padding: 4px;
        }}
    """,
    "spinbox_modern": f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.Black_N3}; color: {c.White_N1}; border-radius: {r['input']};
            padding: 6px 10px; padding-right: 25px; selection-color: {c.Black_N0};
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{  background-color: {c.Black_N3}; }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border; subcontrol-position: top right; width: 16px; border: none;
            border-left: 1px solid {c.Black_N1}; border-top-right-radius: {r['input']}; background-color: {c.Black_N3};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; border: none;
            border-left: 1px solid {c.Black_N1}; border-bottom-right-radius: {r['input']}; background-color: {c.Black_N3};
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: {c.Black_N4}; }}
    """,
    
    # --- SIDEBAR (Existente) ---
    "sidebar_btn": f"""
        QPushButton {{
            background-color: transparent; color: {c.Gray_N1}; 
            padding: 6px; border: none; border-radius: 8px; text-align: left; font-weight: 500; margin: 2px;
        }}
        QPushButton:hover {{ background-color: {c.White_Alpha_08}; color: {c.White_N1}; }}
        QPushButton:checked {{ background-color: rgba(83, 252, 24, 0.15); color: {c.NeonGreen_Main}; font-weight: bold; }}
    """,
    "sidebar_container": f"""
        QFrame {{
            background-color: {c.Black_N1}; 
            border-right: 1px solid {c.Black_N2};
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