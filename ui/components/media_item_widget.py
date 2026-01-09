# ui/components/media_item_widget.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QCheckBox, QDialog
)
from PyQt6.QtCore import QSize, Qt
from ui.theme import LAYOUT, THEME_DARK, get_switch_style
from ui.utils import get_icon
from ui.dialogs.edit_media_modal import ModalEditMedia

class MediaItemWidget(QWidget):
    def __init__(self, filename, ftype, data, page_controller):
        super().__init__()
        self.filename = filename
        self.ftype = ftype
        self.page = page_controller # Referencia al controlador de página
        self.data = data
        
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent;")
        l = QHBoxLayout(self)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        # 1. Checkbox Activo
        self.chk = QCheckBox()
        self.chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk.setChecked(bool(self.data.get("active", 1)))
        self.chk.setStyleSheet(get_switch_style("switch-on.svg"))
        self.chk.toggled.connect(self._handle_toggle_active)
        l.addWidget(self.chk)
        
        # 2. Icono Tipo
        icon_name = "video.svg" if self.ftype == "video" else "music.svg"
        lbl_ico = QLabel()
        lbl_ico.setPixmap(get_icon(icon_name).pixmap(QSize(24, 24)))
        lbl_ico.setStyleSheet("opacity: 0.8; border: none;")
        l.addWidget(lbl_ico)
        
        # 3. Información (Nombre + Comando)
        v_info = QVBoxLayout()
        v_info.setSpacing(0)
        v_info.setContentsMargins(0,0,0,0)
        
        display_name = self.filename[:30] + "..." if len(self.filename) > 30 else self.filename
        lbl_name = QLabel(display_name)
        lbl_name.setStyleSheet("font-weight: bold; border: none; color: white;")
        
        cmd_txt = self.data.get("cmd", "")
        self.lbl_cmd = QLabel(cmd_txt if cmd_txt else "Sin comando asignado")
        self.lbl_cmd.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main'] if cmd_txt else '#666'}; font-size: 11px; border: none;")
        
        v_info.addWidget(lbl_name)
        v_info.addWidget(self.lbl_cmd)
        l.addLayout(v_info, stretch=1)
        
        # 4. Botones (Editar / Play)
        h_act = QHBoxLayout()
        h_act.setSpacing(8)
        
        btn_edit = self._create_mini_btn("edit.svg", self._handle_open_edit)
        btn_play = self._create_mini_btn("play-circle.svg", self._handle_play_preview)
        
        h_act.addWidget(btn_edit)
        h_act.addWidget(btn_play)
        l.addLayout(h_act)

    def _create_mini_btn(self, icon, func):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {THEME_DARK['Black_N4']};  border-radius: 6px; }} 
            QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Main']}; border-color: {THEME_DARK['NeonGreen_Main']}; }}
        """)
        btn.clicked.connect(func)
        return btn

    def _handle_toggle_active(self, checked):
        self.data["active"] = 1 if checked else 0
        self.page.save_item(self.filename, self.ftype, self.data, silent=True)

    def _handle_open_edit(self):
        modal = ModalEditMedia(self.page, self.filename, self.ftype, self.data)
        if modal.exec() == QDialog.DialogCode.Accepted:
            # Actualizar datos locales
            self.data.update({
                "cmd": modal.cmd, 
                "cost": modal.cost, 
                "dur": modal.dur, 
                "volume": modal.vol, 
                "scale": modal.scale
            })
            
            # Actualizar UI inmediata
            self.lbl_cmd.setText(modal.cmd if modal.cmd else "Sin comando asignado")
            self.lbl_cmd.setStyleSheet(f"color: {THEME_DARK['NeonGreen_Main'] if modal.cmd else '#666'}; font-size: 11px; border: none;")
            
            # Guardar en DB
            self.page.save_item(self.filename, self.ftype, self.data)

    def _handle_play_preview(self):
        self.page.preview_item(self.filename, self.ftype, self.data)