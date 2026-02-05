# frontend/components/trigger_card.py

import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSizePolicy, QDialog
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
        
        folder = self.page.service.get_media_folder() if hasattr(self.page, 'service') else ""
        self.full_path = os.path.join(folder, filename)

        self._init_ui()
        self._load_values()

        if self.ftype == "video":
            self._load_async_thumbnail()

    def _init_ui(self):
        self.setMinimumWidth(180) 
        self.setFixedHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['Black_N1']};
            }}
            QFrame:hover {{
                background-color: {THEME_DARK['Black_N4']};
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
        self.lbl_icon.setFixedHeight(100)
        self.lbl_icon.setScaledContents(False)

        bg_icon = QFrame()
        bg_icon.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border-radius: 8px; border: none;")
        l_bg = QVBoxLayout(bg_icon)
        l_bg.setContentsMargins(0,0,0,0)
        l_bg.addWidget(self.lbl_icon)
        layout.addWidget(bg_icon)

        # Nombre
        self.lbl_name = QLabel(self.filename)
        self.lbl_name.setStyleSheet(STYLES["label_text"])
        self.lbl_name.setWordWrap(True) 
        layout.addWidget(self.lbl_name)

        # Input Comando
        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("!comando")
        self.txt_cmd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_cmd.setStyleSheet(STYLES["input_cmd"] + f"background: {THEME_DARK['Black_N1']};")
        self.txt_cmd.editingFinished.connect(self._save_quick_cmd) 
        layout.addWidget(self.txt_cmd)

        # --- SECCIÓN DE BOTONES MODIFICADA ---
        row_btns = QHBoxLayout()
        row_btns.setSpacing(5)

        # 1. Botón Principal: Activar/Desactivar (Ahora es el grande)
        self.btn_toggle = QPushButton("Activar")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFixedHeight(32)
        self.btn_toggle.clicked.connect(self._toggle_active)

        # 2. Botones Pequeños: Ajustes, Preview, Borrar
        self.btn_conf = create_icon_btn("sliders.svg", self._open_advanced_settings, tooltip="Ajustes Avanzados")
        self.btn_play = create_icon_btn("play-circle.svg", self._preview, tooltip="Previsualizar")
        self.btn_del = create_icon_btn("trash.svg", self._delete_config, color_hover=THEME_DARK['status_error'])

        # 3. Orden: Toggle (Grande) -> Ajustes -> Preview -> Borrar
        row_btns.addWidget(self.btn_toggle, stretch=1)
        row_btns.addWidget(self.btn_conf)
        row_btns.addWidget(self.btn_play)
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
                "volume": dlg.vol, "scale": dlg.scale,
                # Guardamos los nuevos valores en el config local
                "pos_x": dlg.pos_x, "pos_y": dlg.pos_y
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
        """
        Maneja el click del botón Activar/Desactivar con respuesta inmediata.
        """
        # 1. Calcular y cambiar el estado en memoria
        curr = bool(self.config.get("active", 0))
        new_state = 0 if curr else 1
        self.config["active"] = new_state
        
        # 2. FEEDBACK VISUAL INMEDIATO (Optimistic UI)
        self._update_active_style(bool(new_state))

        # 3. Guardar en segundo plano
        QTimer.singleShot(10, self._deferred_save)

    def _deferred_save(self):
        """Ejecuta las tareas pesadas después de que la UI se haya actualizado."""
        # 1. Guardar en DB (Esto es lo que causaba el retardo)
        self.page.save_item(self.filename, self.ftype, self.config, silent=True)

        # 2. Refrescar filtros si es necesario
        if hasattr(self.page, 'check_filter_refresh'):
            self.page.check_filter_refresh()

    def _delete_config(self):
        if ModalConfirm(self, "Eliminar", "¿Borrar configuración?").exec():
            self.config = {"cmd": "", "active": 0, "volume": 100, "scale": 1.0}
            self.page.save_item(self.filename, self.ftype, self.config)
            self._load_values()

    def _preview(self):
        self.page.preview_item(self.filename, self.ftype, self.config)

    def _update_active_style(self, is_active):
        """Actualiza el estilo visual basado en si está activo o no."""
        
        if is_active:
            # ESTADO ACTIVO: Botón verde, Texto "Activo", Opacidad full
            self.btn_toggle.setText("Activo")
            self.btn_toggle.setIcon(get_icon_colored("eye.svg", THEME_DARK['NeonGreen_Main'])) # Icono oscuro para contraste
            self.btn_toggle.setStyleSheet(STYLES["btn_primary"]) # Estilo verde/primario
            
            # Quitamos la opacidad del frame si estaba puesta
            self.setStyleSheet(self.styleSheet().replace("QFrame { opacity: 0.6; }", ""))

        else:
            # ESTADO INACTIVO: Botón gris/outline, Texto "Activar", Opacidad reducida
            self.btn_toggle.setText("Activar")
            self.btn_toggle.setIcon(get_icon("eye-off.svg"))
            self.btn_toggle.setStyleSheet(STYLES["btn_outlined"]) # Estilo borde gris
            
            # Agregamos opacidad visual al card entero para indicar inactividad
            if "opacity" not in self.styleSheet():
                self.setStyleSheet(self.styleSheet() + "QFrame { opacity: 0.6; }")

    def _load_async_thumbnail(self):
        """Inicia el worker en un hilo separado para no congelar la frontend."""
        if not os.path.exists(self.full_path):
            return
        worker = ThumbnailWorker(self.full_path, width=300)
        worker.signals.finished.connect(self._update_thumbnail)
        QThreadPool.globalInstance().start(worker)

    def _update_thumbnail(self, pixmap):
        """Recibe el pixmap generado por el worker."""
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
            
            rounded = get_rounded_pixmap(scaled, radius=8)
            
            self.lbl_icon.setPixmap(rounded)
            self.lbl_icon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)