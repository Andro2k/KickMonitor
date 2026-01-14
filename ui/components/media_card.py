
import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSizePolicy, QDialog
)
from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtGui import QIcon
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.utils import ThumbnailWorker, get_colored_icon, get_icon
from ui.factories import create_icon_btn
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from ui.dialogs.edit_media_modal import ModalEditMedia

class MediaCard(QFrame):
    def __init__(self, filename, ftype, config, parent_page):
        super().__init__()
        self.filename = filename
        self.ftype = ftype
        self.config = config.copy()
        self.page = parent_page 
        self.thread_pool = QThreadPool.globalInstance()
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        self.setMinimumWidth(180) 
        self.setFixedHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 16px;
                border: 1px solid {THEME_DARK['Black_N1']};
            }}
            QFrame:hover {{
                border: 1px solid {THEME_DARK['Black_N4']};
                background-color: {THEME_DARK['Black_N3']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        # --- ZONA DE IMAGEN/ICONO ---
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_icon.setScaledContents(False)

        # 1. Contenedor para la imagen (con borde redondeado y fondo negro)
        bg_icon = QFrame()
        bg_icon.setFixedHeight(100) # Hacemos la zona de imagen un poco más alta
        bg_icon.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N1']}; 
                border-radius: 8px; 
                border: 1px solid {THEME_DARK['Black_N3']};
            }}
        """)
        
        # === CAMBIO CLAVE: CARGA INMEDIATA ===
        # 1. Ponemos SIEMPRE el icono por defecto primero (es instantáneo)
        icon_name = "video.svg" if self.ftype == "video" else "music.svg"
        default_pix = get_icon(icon_name).pixmap(48, 48)
        self.lbl_icon.setPixmap(default_pix)

        # 2. Si es video, lanzamos la tarea en segundo plano
        if self.ftype == "video":
            self._load_thumbnail_async()

        l_bg = QVBoxLayout(bg_icon)
        l_bg.setContentsMargins(0,0,0,0)
        l_bg.addWidget(self.lbl_icon)
        layout.addWidget(bg_icon)

        # Nombre
        self.lbl_name = QLabel(self.filename)
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 13px; color: white; border: none; background: transparent;")
        self.lbl_name.setWordWrap(True) 
        layout.addWidget(self.lbl_name)

        # Input Comando
        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("!comando")
        self.txt_cmd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_cmd.setStyleSheet(STYLES["input_cmd"] + f"background: {THEME_DARK['Black_N1']};")
        self.txt_cmd.editingFinished.connect(self._save_quick_cmd) 
        layout.addWidget(self.txt_cmd)

        # Botones
        row_btns = QHBoxLayout()
        row_btns.setSpacing(5)

        self.btn_play = QPushButton("Preview")
        self.btn_play.setIcon(get_icon("play-circle.svg"))
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setFixedHeight(32)
        self.btn_play.clicked.connect(self._preview)
        
        self.btn_conf = create_icon_btn("sliders.svg", self._open_advanced_settings, tooltip="Ajustes Avanzados")
        self.btn_toggle = create_icon_btn("eye.svg", self._toggle_active, tooltip="Activar/Desactivar")
        self.btn_del = create_icon_btn("trash.svg", self._delete_config, color_hover=THEME_DARK['Status_Red'])

        row_btns.addWidget(self.btn_play, stretch=1)
        row_btns.addWidget(self.btn_conf)
        row_btns.addWidget(self.btn_toggle)
        row_btns.addWidget(self.btn_del)

        layout.addLayout(row_btns)

    def _load_values(self):
        self.txt_cmd.setText(self.config.get("cmd", ""))
        self._update_active_style(bool(self.config.get("active", 0)))

    # --- Actions ---
    def _open_advanced_settings(self):
        dlg = ModalEditMedia(self, self.filename, self.ftype, self.config)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.config.update({
                "cmd": dlg.cmd, "cost": dlg.cost, "dur": dlg.dur,
                "volume": dlg.vol, "scale": dlg.scale
            })
            self.txt_cmd.setText(dlg.cmd)
            self.page.save_item(self.filename, self.ftype, self.config, silent=True)
            ToastNotification(self.page, "Ajustes", "Configuración actualizada", "info").show_toast()

    def _save_quick_cmd(self):
        text = self.txt_cmd.text().strip()

        if text and not text.startswith("!"):
            text = f"!{text}"
            self.txt_cmd.setText(text)

        if hasattr(self.page, 'handle_command_update'):
            self.page.handle_command_update(self.filename, text)
        else:
            self.config["cmd"] = text
            self.page.save_item(self.filename, self.ftype, self.config, silent=True)

    def refresh_state_from_config(self, new_config):
        """
        NUEVO MÉTODO: Permite que la página actualice esta tarjeta externamente.
        """
        self.config = new_config.copy()
        
        if self.txt_cmd.text() != self.config.get("cmd", ""):
            self.txt_cmd.setText(self.config.get("cmd", ""))
            
        is_active = bool(self.config.get("active", 0))
        self._update_active_style(is_active)

    # En media_card.py

    def _toggle_active(self):
        curr = bool(self.config.get("active", 0))
        self.config["active"] = 0 if curr else 1
        self._update_active_style(not curr)
        self.page.save_item(self.filename, self.ftype, self.config, silent=True)

    def _delete_config(self):
        if ModalConfirm(self, "Eliminar", "¿Borrar configuración?").exec():
            self.config = {"cmd": "", "active": 0, "volume": 100, "scale": 1.0}
            self.page.save_item(self.filename, self.ftype, self.config)
            self._load_values()

    def _preview(self):
        self.page.preview_item(self.filename, self.ftype, self.config)

    def _update_active_style(self, is_active):
        icon_preview = QIcon()
        
        if is_active:
            pix_black = get_colored_icon("play-circle.svg", THEME_DARK['Black_N1']).pixmap(24, 24)
            icon_preview.addPixmap(pix_black, QIcon.Mode.Normal)
            icon_preview.addPixmap(pix_black, QIcon.Mode.Active)

            # Estilo CSS del botón
            self.btn_play.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME_DARK['NeonGreen_Main']}; 
                    color: {THEME_DARK['Black_N1']};
                    font-weight: bold; border-radius: 8px; border: none;
                    text-align: left; padding-left: 10px;
                }}
                QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Light']}; }}
            """)
            
            # Restaurar opacidad de la tarjeta completa
            self.setStyleSheet(self.styleSheet().replace("QFrame { opacity: 0.6; }", ""))

        else:
            pix_gray = get_colored_icon("play-circle.svg", THEME_DARK['Gray_N2']).pixmap(24, 24)
            pix_white = get_colored_icon("play-circle.svg", THEME_DARK['White_N1']).pixmap(24, 24)
            
            # Añadimos ambos estados al icono
            icon_preview.addPixmap(pix_gray, QIcon.Mode.Normal)
            icon_preview.addPixmap(pix_white, QIcon.Mode.Active)   # Active suele activarse en Hover
            icon_preview.addPixmap(pix_white, QIcon.Mode.Selected) # Por seguridad

            # Estilo CSS del botón
            self.btn_play.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME_DARK['Black_N1']}; 
                    color: {THEME_DARK['Gray_N2']};
                    font-weight: bold; border-radius: 8px; 
                    border: 1px solid {THEME_DARK['Black_N3']};
                    text-align: left; padding-left: 10px;
                }}
                QPushButton:hover {{ 
                    border: 1px solid {THEME_DARK['Gray_N1']}; 
                    color: {THEME_DARK['White_N1']}; 
                }}
            """)

            # Aplicar opacidad a la tarjeta si no está activa
            if "opacity" not in self.styleSheet():
                self.setStyleSheet(self.styleSheet() + "QFrame { opacity: 0.6; }")

        # 2. Asignar los iconos finales
        self.btn_play.setIcon(icon_preview)
        self.btn_toggle.setIcon(get_icon("eye.svg" if is_active else "eye-off.svg"))