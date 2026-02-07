# frontend/components/trigger_card.py

import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSizePolicy, QDialog
)
from PyQt6.QtCore import QThreadPool, QTimer, Qt
from frontend.theme import LAYOUT, THEME_DARK, STYLES
from frontend.utils import ThumbnailWorker, get_icon_colored, get_icon, get_rounded_pixmap
from frontend.factories import create_icon_btn
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.dialogs.trigger_modal import ModalEditMedia

class MediaCard(QFrame):
    def __init__(self, filename, ftype, config, parent_page):
        super().__init__()
        self.filename = filename
        self.ftype = ftype
        self.config = config.copy()
        self.page = parent_page 
        
        folder = ""
        if hasattr(self.page, 'service'):
            folder = self.page.service.get_media_folder()
            
        self.full_path = os.path.join(folder, filename)
        self.setFixedSize(360, 160)
        self._init_ui()
        self._load_values()

        if self.ftype == "video":
            self._load_async_thumbnail()

    def _init_ui(self):
        self.setMinimumWidth(180) 
        self.setFixedHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid {THEME_DARK['Gray_N1']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["level_01"])
        layout.setSpacing(8)

        # 1. Icono / Thumbnail
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        icon_name = "video.svg" if self.ftype == "video" else "music.svg"
        self.lbl_icon.setPixmap(get_icon(icon_name).pixmap(52, 52))
        self.lbl_icon.setFixedHeight(120)
        
        bg_icon = QFrame()
        bg_icon.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border-radius: 8px; border: none;")
        l_bg = QVBoxLayout(bg_icon)
        l_bg.setContentsMargins(0,0,0,0)
        l_bg.addWidget(self.lbl_icon)
        layout.addWidget(bg_icon)

        # 2. Nombre del Archivo
        self.lbl_name = QLabel(self.filename)
        self.lbl_name.setStyleSheet("color: #AAA; font-size: 12px; font-weight: bold; border:none;")
        self.lbl_name.setWordWrap(False) 
        layout.addWidget(self.lbl_name)

        # 3. Label: Nombre de la Recompensa (Kick) - SOLO LECTURA
        self.lbl_reward_display = QLabel("Sin Asignar")
        self.lbl_reward_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_reward_display.setFixedHeight(26)
        layout.addWidget(self.lbl_reward_display)

        # 4. Botones
        row_btns = QHBoxLayout()
        row_btns.setSpacing(5)

        # Botón Principal (Toggle)
        self.btn_toggle = QPushButton("Asignar")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedHeight(30)
        self.btn_toggle.clicked.connect(self._handle_main_action)
        
        row_btns.addWidget(self.btn_toggle, stretch=1)
        
        # Botones pequeños
        self.btn_conf = create_icon_btn("sliders.svg", self._open_advanced_settings, tooltip="Editar Configuración")
        self.btn_play = create_icon_btn("play-circle.svg", self._preview, tooltip="Probar Sonido")
        self.btn_del = create_icon_btn("trash.svg", self._delete_config, color_hover=THEME_DARK['status_error'])

        row_btns.addWidget(self.btn_conf)
        row_btns.addWidget(self.btn_play)
        row_btns.addWidget(self.btn_del)

        layout.addLayout(row_btns)

    def _load_values(self):
        cmd = self.config.get("cmd", "")
        self._update_display_label(cmd)
        self._update_btn_state()

    def _update_display_label(self, cmd_text):
        """Actualiza el label visual."""
        if cmd_text:
            self.lbl_reward_display.setText(cmd_text)
            self.lbl_reward_display.setStyleSheet(f"""
                background-color: {THEME_DARK['Black_N3']};
                color: #53fc18; /* Verde Kick */
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid {THEME_DARK['Black_N1']};
            """)
        else:
            self.lbl_reward_display.setText("Sin Asignar")
            self.lbl_reward_display.setStyleSheet(f"""
                background-color: {THEME_DARK['Black_N3']};
                color: #666;
                border-radius: 4px;
                font-style: italic;
                border: 1px dashed #444;
            """)

    def _handle_main_action(self):
        cmd = self.config.get("cmd", "")
        if not cmd:
            self._open_advanced_settings()
        else:
            self._toggle_active()

    def _toggle_active(self):
        curr = bool(self.config.get("active", 0))
        new_state = 0 if curr else 1
        self.config["active"] = new_state
        self._update_btn_state()
        QTimer.singleShot(10, self._deferred_save)

    def _update_btn_state(self):
        cmd = self.config.get("cmd", "")
        is_active = bool(self.config.get("active", 0))
        if not cmd:
            self.btn_toggle.setText("Asignar / Crear")
            self.btn_toggle.setStyleSheet(STYLES["btn_nav"]) 
            self.btn_toggle.setIcon(get_icon_colored("check.svg", "#ffffff"))
        else:
            if is_active:
                self.btn_toggle.setText("Activo")
                self.btn_toggle.setStyleSheet(STYLES["btn_primary"])
                self.btn_toggle.setIcon(get_icon_colored("check.svg", "#53fc18"))
            else:
                self.btn_toggle.setText("Inactivo")
                self.btn_toggle.setStyleSheet(STYLES["btn_nav"])
                self.btn_toggle.setIcon(get_icon_colored("x-circle.svg", "#e74c3c"))

    def _deferred_save(self):
        # SIEMPRE True para que Kick se entere de que debe apagarse/encenderse
        self.page.save_item(self.filename, self.ftype, self.config, silent=True, sync_kick=True)
        
        if hasattr(self.page, 'check_filter_refresh'):
            self.page.check_filter_refresh()

    def _open_advanced_settings(self):
        dlg = ModalEditMedia(self.page, self.filename, self.ftype, self.config)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # 1. Unicidad
            if hasattr(self.page, 'service'):
                self.page.service.ensure_unique_assignment(self.filename, dlg.cmd)

            # 2. Actualizar config (INCLUYENDO COLOR Y DESC)
            self.config.update({
                "cmd": dlg.cmd, 
                "cost": dlg.cost, 
                "dur": dlg.dur,
                "volume": dlg.vol, 
                "scale": dlg.scale,
                "pos_x": dlg.pos_x, 
                "pos_y": dlg.pos_y,
                "active": 1,
                "color": dlg.color,
                "description": dlg.description
            })
            
            # --- CORRECCIÓN CLAVE: Usamos el método helper, no txt_reward ---
            self._update_display_label(dlg.cmd)
            self._update_btn_state()
            
            # 3. Guardar con sincronización
            self.page.save_item(self.filename, self.ftype, self.config, sync_kick=True)
            self.page.load_data()

    def _delete_config(self):
        if ModalConfirm(self, "Eliminar", "¿Desvincular y eliminar recompensa de Kick?").exec():
            reward_name = self.config.get("cmd", "")
            if hasattr(self.page, 'service'):
                self.page.service.delete_trigger_data(self.filename, reward_name)
            
            self.config = {"cmd": "", "active": 0, "volume": 100}
            self._load_values()
            ToastNotification(self.page, "Eliminado", "Configuración borrada.", "status_success").show_toast()

    def _preview(self):
        self.page.preview_item(self.filename, self.ftype, self.config)
    
    def refresh_state_from_config(self, new_config):
        self.config = new_config.copy()
        self._update_display_label(self.config.get("cmd", ""))
        self._update_btn_state()

    def _load_async_thumbnail(self):
        if not os.path.exists(self.full_path): return
        worker = ThumbnailWorker(self.full_path, width=300)
        worker.signals.finished.connect(self._update_thumbnail)
        QThreadPool.globalInstance().start(worker)

    def _update_thumbnail(self, pixmap):
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaledToHeight(90, Qt.TransformationMode.SmoothTransformation)
            rounded = get_rounded_pixmap(scaled, radius=6)
            self.lbl_icon.setPixmap(rounded)