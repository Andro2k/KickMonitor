from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation
from ui.theme import THEME_DARK, LAYOUT

class CustomModal(QDialog):
    CONFIGS = {
        "Status_Green":  {"icon": "✓", "color": THEME_DARK['Status_Green']},
        "Status_Red":    {"icon": "✕", "color": THEME_DARK['Status_Red']},
        "Status_Yellow": {"icon": "!", "color": THEME_DARK['Status_Yellow']},
        "info":          {"icon": "i", "color": THEME_DARK['info']}
    }

    def __init__(self, parent, titulo: str, mensaje: str, tipo: str = "info", mode: str = "alert"):
        super().__init__(parent)
        self.tipo_mode = mode
        self.config = self.CONFIGS.get(tipo, self.CONFIGS["info"])
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) 
        self.setFixedWidth(360)

        self._setup_ui(titulo, mensaje)
        self._animate_entry()

    def _setup_ui(self, titulo, mensaje):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 30, 10, 10)
        
        body = QFrame()
        body.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N3']}; 
                border-radius: 16px; 
                border: 1px solid {self.config['color']};
            }}
        """)
        
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 35, 20, 20)
        body_layout.setSpacing(LAYOUT["spacing"])

        lbl_tit = QLabel(titulo)
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_tit.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME_DARK['White_N1']}; border: none;")
        
        lbl_msg = QLabel(mensaje)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"font-size: 13px; color: {THEME_DARK['Gray_N1']}; border: none;")

        body_layout.addWidget(lbl_tit)
        body_layout.addWidget(lbl_msg)
        body_layout.addLayout(self._create_buttons())
        
        layout.addWidget(body)
        self._setup_icon()

    def _create_buttons(self):
        actions = QHBoxLayout()
        
        if self.tipo_mode == "confirm":
            btn_c = self._make_btn("Cancelar", primary=False)
            btn_c.clicked.connect(self._animate_close_reject)
            actions.addWidget(btn_c)
        
        text_ok = "Confirmar" if self.tipo_mode == "confirm" else "Entendido"
        btn_ok = self._make_btn(text_ok, primary=True)
        btn_ok.clicked.connect(self._animate_close_accept)
        actions.addWidget(btn_ok)
        
        return actions

    def _make_btn(self, text, primary):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        
        if primary:
            # Botón Primario: Fondo de color, Hover con borde blanco
            color = self.config['color']
            style = f"""
                QPushButton {{
                    background-color: {color};
                    color: #000000;
                    border: 1px solid {color};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }}
            """
        else:
            # Botón Secundario: Transparente, Hover gris oscuro
            style = f"""
                QPushButton {{
                    background-color: {THEME_DARK['Black_N2']};
                    color: {THEME_DARK['Gray_N1']};
                    border: 1px solid {THEME_DARK['border']};
                    border-radius: 8px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {THEME_DARK['Black_N1']};
                    color: {THEME_DARK['White_N1']};
                    border: 1px solid {THEME_DARK['Gray_N1']};
                }}
            """
        
        btn.setStyleSheet(style)
        return btn

    def _setup_icon(self):
        lbl = QLabel(self.config['icon'], self)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setGeometry((self.width() - 64) // 2, 0, 64, 64)
        lbl.setStyleSheet(f"""
            background-color: {self.config['color']}; 
            color: #000; 
            border-radius: 32px; 
            font-size: 26px; 
            font-weight: 900; 
            border: 4px solid {THEME_DARK['Black_N1']};
        """)

    def _animate_entry(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def _animate_close_accept(self): self._fade_out(self.accept)
    def _animate_close_reject(self): self._fade_out(self.reject)
    
    def _fade_out(self, call):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)
        self.anim_out.finished.connect(call)
        self.anim_out.start()

def ModalAlert(parent, titulo, mensaje, tipo="info"):
    return CustomModal(parent, titulo, mensaje, tipo, mode="alert")

def ModalConfirm(parent, titulo, mensaje):
    tipo = "Status_Red" if any(x in titulo.lower() for x in ["salir", "eliminar", "borrar", "duplicado"]) else "info"
    return CustomModal(parent, titulo, mensaje, tipo, mode="confirm")