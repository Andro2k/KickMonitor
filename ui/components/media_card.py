from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSizePolicy, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.utils import get_icon_colored, get_icon
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

        # Icono
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        icon_name = "video.svg" if self.ftype == "video" else "music.svg"
        self.lbl_icon.setPixmap(get_icon(icon_name).pixmap(48, 48))
        self.lbl_icon.setFixedHeight(80)
        
        bg_icon = QFrame()
        bg_icon.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border-radius: 8px; border: none;")
        l_bg = QVBoxLayout(bg_icon); l_bg.setContentsMargins(0,0,0,0); l_bg.addWidget(self.lbl_icon)
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
        self.config = new_config.copy()
        
        if self.txt_cmd.text() != self.config.get("cmd", ""):
            self.txt_cmd.setText(self.config.get("cmd", ""))
            
        is_active = bool(self.config.get("active", 0))
        self._update_active_style(is_active)

    # En media_card.py

    def _toggle_active(self):
        # 1. Cambiar estado lógico
        curr = bool(self.config.get("active", 0))
        new_state = 0 if curr else 1
        self.config["active"] = new_state
        
        # 2. Guardar en base de datos (silencioso)
        self.page.save_item(self.filename, self.ftype, self.config, silent=True)

        # 3. LÓGICA NUEVA:
        # Si la página tiene el método de chequeo, lo llamamos.
        if hasattr(self.page, 'check_filter_refresh'):
            # Verificamos si hay que refrescar la grilla completa (para ocultar esta carta)
            self.page.check_filter_refresh()
            
            # Si NO se refrescó la grilla (porque estamos en "Todos"), actualizamos el estilo visual
            self._update_active_style(bool(new_state))
        else:
            # Fallback por si no has actualizado OverlayPage
            self._update_active_style(bool(new_state))

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
            pix_black = get_icon_colored("play-circle.svg", THEME_DARK['Black_N1']).pixmap(24, 24)
            icon_preview.addPixmap(pix_black, QIcon.Mode.Normal)
            icon_preview.addPixmap(pix_black, QIcon.Mode.Active)

            # Estilo CSS del botón
            self.btn_play.setStyleSheet(STYLES["btn_solid_primary"])
            
            # Restaurar opacidad de la tarjeta completa
            self.setStyleSheet(self.styleSheet().replace("QFrame { opacity: 0.6; }", ""))

        else:
            pix_gray = get_icon_colored("play-circle.svg", THEME_DARK['White_N1']).pixmap(24, 24)
            
            # Añadimos ambos estados al icono
            icon_preview.addPixmap(pix_gray, QIcon.Mode.Normal)

            # Estilo CSS del botón
            self.btn_play.setStyleSheet(STYLES["btn_outlined"])

            # Aplicar opacidad a la tarjeta si no está activa
            if "opacity" not in self.styleSheet():
                self.setStyleSheet(self.styleSheet() + "QFrame { opacity: 0.6; }")

        # 2. Asignar los iconos finales
        self.btn_play.setIcon(icon_preview)
        self.btn_toggle.setIcon(get_icon("eye.svg" if is_active else "eye-off.svg"))