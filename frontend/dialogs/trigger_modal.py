# frontend/dialogs/trigger_modal.py

import json
import os
import re
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QSlider, QComboBox,
    QTextEdit, QColorDialog, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QCursor, QTextCursor

from backend.utils.paths import get_config_path
from frontend.notifications.modal_alert import ModalConfirm
from frontend.notifications.toast_alert import ToastNotification
from frontend.components.core.factories import create_icon_btn
from frontend.theme import STYLES, THEME_DARK, get_switch_style
from frontend.components.core.modals import BaseModal

# =============================================================================
# WORKER: CARGA ASÍNCRONA DE KICK
# =============================================================================
class RewardsLoaderWorker(QThread):
    finished = pyqtSignal(bool, list)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        has_token = False
        try:
            path = os.path.join(get_config_path(), "session.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    if data.get("access_token"):
                        has_token = True
        except Exception:
            has_token = False

        if not has_token:
            self.finished.emit(False, [])
            return

        try:
            rewards = self.service.get_available_kick_rewards()
            self.finished.emit(True, rewards)
        except Exception:
            self.finished.emit(False, [])

# =============================================================================
# CLASE PRINCIPAL: MODAL DE EDICIÓN
# =============================================================================
class ModalEditMedia(BaseModal):
    def __init__(self, parent_page, filename, ftype, data, used_commands=None):
        super().__init__(parent_page, width=500, height=620)
        self.body.setStyleSheet(f"""
            QFrame#ModalBody {{
                background-color: {THEME_DARK['Black_N1']};
                border-radius: 12px;
            }}
        """)
        self.page = parent_page 
        self.filename = filename
        self.ftype = ftype
        self.full_path = data.get("path", "")
        self.used_commands = used_commands or set()
        self.cmd = data.get("cmd", "")
        self.cost = int(data.get("cost", 0))
        self.dur = int(data.get("dur", 0))
        self.vol = int(data.get("volume", 100))
        self.scale = float(data.get("scale", 1.0))
        self.pos_x = int(data.get("pos_x", 0))
        self.pos_y = int(data.get("pos_y", 0))
        self.color = data.get("color", "#53fc18") 
        self.description = data.get("description", "Trigger KickMonitor")
        self.random_pos = int(data.get("random_pos", 0))
        
        self._setup_ui()
        QTimer.singleShot(100, self._start_async_loading)

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE INTERFAZ (UI) MODULARIZADA
    # -------------------------------------------------------------------------
    def _setup_ui(self):
        layout = self.body_layout
        layout.setSpacing(10)

        self.lbl_title = QLabel(f"Configurar: {self.filename}" if self.filename else "Nuevo Trigger")
        self.lbl_title.setStyleSheet(STYLES["label_title"])
        layout.addWidget(self.lbl_title)

        self._setup_file_selection(layout)
        self._setup_reward_selection(layout)
        self._setup_kick_appearance(layout)
        self._setup_numeric_config(layout)
        self._setup_position_config(layout)
        self._setup_sliders(layout)
        self._setup_buttons(layout)

        self._validate_desc() # Validación inicial

    # 🔴 AÑADIR ESTAS DOS FUNCIONES NUEVAS EN CUALQUIER PARTE DE LA CLASE:
    def _setup_file_selection(self, layout):
        h_file = QHBoxLayout()
        self.inp_path = QLineEdit(self.full_path)
        self.inp_path.setReadOnly(True)
        self.inp_path.setPlaceholderText("Selecciona un archivo multimedia...")
        self.inp_path.setStyleSheet(STYLES["input"])
        
        btn_browse = QPushButton("Buscar")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet(STYLES["btn_outlined"]) 
        btn_browse.clicked.connect(self._browse_file)
        
        h_file.addWidget(self.inp_path)
        h_file.addWidget(btn_browse)
        layout.addLayout(h_file)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo Multimedia", "", "Media Files (*.mp4 *.webm *.mp3 *.wav *.ogg)")
        if path:
            self.full_path = path
            self.inp_path.setText(path)
            self.filename = os.path.basename(path)
            self.ftype = "video" if path.lower().endswith(('.mp4', '.webm')) else "audio"
            self.lbl_title.setText(f"Configurar: {self.filename}")
            self._check_save_enabled()
            
    def _setup_reward_selection(self, layout):
        layout.addWidget(QLabel("Nombre del Canje (Kick) - Max 20 letras:", styleSheet="border:none; color: #AAA; font-size: 12px;"))
        
        h_combo = QHBoxLayout()
        h_combo.setSpacing(5)

        self.combo_rewards = QComboBox()
        self.combo_rewards.setEditable(True) 
        self.combo_rewards.setPlaceholderText("Cargando lista...") 
        self.combo_rewards.lineEdit().setMaxLength(20) 
        self.combo_rewards.setStyleSheet(STYLES["combobox_modern"])
        
        self.combo_rewards.editTextChanged.connect(self._validate_title)
        self.combo_rewards.currentIndexChanged.connect(self._on_reward_selected)
        
        self.btn_refresh = create_icon_btn("refresh-cw.svg", self._start_async_loading, tooltip="Recargar lista de Kick")
        
        h_combo.addWidget(self.combo_rewards)
        h_combo.addWidget(self.btn_refresh)
        layout.addLayout(h_combo)

    def _setup_kick_appearance(self, layout):
        frame_kick = QFrame()
        frame_kick.setStyleSheet(f"background-color: {THEME_DARK['Black_N2']}; border-radius: 8px;")
        lk = QVBoxLayout(frame_kick)
        
        # Color
        h_color = QHBoxLayout()
        h_color.addWidget(QLabel("Color:", styleSheet="border:none; color: #DDD;"))
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(50, 24)
        self.btn_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_color.clicked.connect(self._pick_color)
        self._update_color_btn()
        h_color.addWidget(self.btn_color)
        h_color.addStretch()
        lk.addLayout(h_color)
        
        # Descripción
        h_desc_lbl = QHBoxLayout()
        h_desc_lbl.addWidget(QLabel("Descripción:", styleSheet="border:none; color: #DDD;"))
        self.lbl_desc_count = QLabel("0/200")
        self.lbl_desc_count.setStyleSheet("border:none; color: #666; font-size: 12px;")
        h_desc_lbl.addWidget(self.lbl_desc_count)
        h_desc_lbl.addStretch()
        lk.addLayout(h_desc_lbl)

        self.txt_desc = QTextEdit()
        self.txt_desc.setStyleSheet(STYLES["text_edit_console"])
        self.txt_desc.setPlaceholderText("Instrucciones para el usuario...")
        self.txt_desc.setText(self.description)
        self.txt_desc.setFixedHeight(65)
        self.txt_desc.textChanged.connect(self._validate_desc)
        
        lk.addWidget(self.txt_desc)
        layout.addWidget(frame_kick)

    def _setup_numeric_config(self, layout):
        h_nums = QHBoxLayout()
        
        # Costo
        v_cost = QVBoxLayout()
        v_cost.addWidget(QLabel("Costo:", styleSheet="border:none; color: #888;"))
        self.spin_cost = QSpinBox()
        self.spin_cost.setRange(1, 1000000) 
        self.spin_cost.setValue(self.cost if self.cost > 0 else 1) 
        self.spin_cost.setStyleSheet(STYLES["spinbox_modern"] + "color: #53fc18; font-weight: bold;")
        v_cost.addWidget(self.spin_cost)
        h_nums.addLayout(v_cost)
        
        # Duración
        v_dur = QVBoxLayout()
        v_dur.addWidget(QLabel("Duración (s):", styleSheet="border:none; color: #888;"))
        self.spin_dur = QSpinBox()
        self.spin_dur.setRange(0, 300)
        self.spin_dur.setValue(self.dur)
        self.spin_dur.setStyleSheet(STYLES["spinbox_modern"])
        v_dur.addWidget(self.spin_dur)
        h_nums.addLayout(v_dur)
        
        layout.addLayout(h_nums)

    def _setup_position_config(self, layout):
        h_pos = QHBoxLayout()
        self.spin_x = self._create_coord_spin("Pos X:", self.pos_x)
        self.spin_y = self._create_coord_spin("Pos Y:", self.pos_y)
        h_pos.addLayout(self.spin_x)
        h_pos.addLayout(self.spin_y)
        
        v_rand = QVBoxLayout()
        v_rand.setContentsMargins(0, 0, 0, 0)
        v_rand.setSpacing(2)
        v_rand.addWidget(QLabel("Posición Aleatoria:", styleSheet="border:none; color: #888; background: transparent;"))
        
        self.chk_rand = QCheckBox()
        self.chk_rand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_rand.setStyleSheet(get_switch_style())
        self.chk_rand.setChecked(bool(self.random_pos))
        
        v_rand.addWidget(self.chk_rand)
        h_pos.addLayout(v_rand)
        layout.addLayout(h_pos)

    def _setup_sliders(self, layout):
        # Helper interno para no repetir código de creación de sliders
        def create_slider_row(label_text, min_val, max_val, current_val):
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            l = QVBoxLayout(w)
            l.setContentsMargins(0,0,0,0)
            l.setSpacing(2)

            h_lbl = QHBoxLayout()
            h_lbl.addWidget(QLabel(label_text, styleSheet="border:none; color: #888; background: transparent;"))
            lbl_val = QLabel(f"{current_val}%")
            lbl_val.setStyleSheet("color: #AAA; font-weight: bold; border:none; background: transparent;")
            h_lbl.addWidget(lbl_val)
            h_lbl.addStretch()
            l.addLayout(h_lbl)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(current_val)
            slider.valueChanged.connect(lambda v: lbl_val.setText(f"{v}%"))
            l.addWidget(slider)
            
            return w, slider, lbl_val

        # Volumen
        w_vol, self.slider_vol, self.lbl_vol_val = create_slider_row("Volumen:", 0, 100, self.vol)
        layout.addWidget(w_vol)

        # Escala (Solo si es video)
        if self.ftype == "video":
            w_zoom, self.slider_zoom, self.lbl_zoom_val = create_slider_row("Tamaño (Escala):", 10, 200, int(self.scale * 100))
            layout.addWidget(w_zoom)
        
        layout.addStretch()

    def _setup_buttons(self, layout):
        h_btns = QHBoxLayout()
        
        self.btn_unlink = QPushButton("Desvincular")
        self.btn_unlink.clicked.connect(self._unlink_data)
        self.btn_unlink.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; color: {THEME_DARK['status_error']}; 
                border: 1px solid {THEME_DARK['status_error']}; border-radius: 4px; padding: 5px 15px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {THEME_DARK['status_error']}; color: white; }}
        """)

        self.btn_delete_kick = QPushButton("Eliminar de Kick")
        self.btn_delete_kick.clicked.connect(self._delete_from_kick)
        self.btn_delete_kick.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['status_error']}; color: white; border: none; 
                border-radius: 4px; padding: 5px 15px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)

        if not self.cmd:
            self.btn_unlink.hide()
            self.btn_delete_kick.hide() 
            
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        self.btn_save = QPushButton("Guardar") 
        self.btn_save.clicked.connect(self._save_data)
        self.btn_save.setStyleSheet(STYLES["btn_primary"])
        
        h_btns.addWidget(self.btn_unlink)
        h_btns.addWidget(self.btn_delete_kick)
        h_btns.addStretch() 
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(self.btn_save)
        
        layout.addLayout(h_btns)

    # -------------------------------------------------------------------------
    # LÓGICA DE VALIDACIÓN Y HELPERS UI
    # -------------------------------------------------------------------------
    def _create_coord_spin(self, label_text, val):
        l = QVBoxLayout() 
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(2)
        l.addWidget(QLabel(label_text, styleSheet="border:none; color:#888; background: transparent;"))
        spin = QSpinBox()
        spin.setRange(0, 5000)
        spin.setValue(val if val >= 0 else 0)
        spin.setStyleSheet(STYLES["spinbox_modern"])
        l.addWidget(spin)
        return l

    def _update_color_btn(self):
        self.btn_color.setStyleSheet(f"background-color: {self.color}; border: 2px solid #555; border-radius: 4px;")

    def _pick_color(self):
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(self.color))
        if dialog.exec():
            self.color = dialog.selectedColor().name()
            self._update_color_btn()

    def _validate_title(self, text):
        pattern = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ]*$"
        if not re.match(pattern, text):
            self.combo_rewards.setStyleSheet(STYLES["combobox_modern"] + "border: 2px solid #e74c3c;")
            self.btn_save.setEnabled(False) 
        else:
            self.combo_rewards.setStyleSheet(STYLES["combobox_modern"])
            self._check_save_enabled()

    def _validate_desc(self):
        text = self.txt_desc.toPlainText()
        limit = 200
        
        if len(text) > limit:
            self.txt_desc.blockSignals(True) 
            text = text[:limit]
            self.txt_desc.setPlainText(text)
            cursor = self.txt_desc.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.txt_desc.setTextCursor(cursor)
            self.txt_desc.blockSignals(False) 
        
        self.lbl_desc_count.setText(f"{len(text)}/{limit}")

        pattern = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ.,;¿?!]*$"
        if not re.match(pattern, text, re.DOTALL):
            self.txt_desc.setStyleSheet(STYLES["text_edit_console"] + "border: 2px solid #e74c3c;")
            self.btn_save.setEnabled(False)
        else:
            self.txt_desc.setStyleSheet(STYLES["text_edit_console"])
            self._check_save_enabled()

    def _check_save_enabled(self):
        pat_title = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ]*$"
        pat_desc = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ.,;¿?!]*$"
        
        title_ok = bool(re.match(pat_title, self.combo_rewards.currentText()))
        desc_ok = bool(re.match(pat_desc, self.txt_desc.toPlainText(), re.DOTALL))
        file_ok = bool(self.full_path)
        
        self.btn_save.setEnabled(title_ok and desc_ok and file_ok)

    # -------------------------------------------------------------------------
    # LÓGICA ASÍNCRONA Y EVENTOS DE GUARDADO
    # -------------------------------------------------------------------------
    def _start_async_loading(self):
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            return 

        self.combo_rewards.clear()
        self.combo_rewards.setPlaceholderText("Buscando en Kick...")
        self.combo_rewards.setEnabled(False) 
        self.btn_refresh.setEnabled(False)

        if hasattr(self.page, 'service'):
            self.worker = RewardsLoaderWorker(self.page.service)
            self.worker.finished.connect(self._on_rewards_loaded)
            self.worker.finished.connect(lambda: setattr(self, 'worker', None))
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.start()

    def _on_rewards_loaded(self, is_connected, rewards):
        self.combo_rewards.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.combo_rewards.clear() 
        
        if not is_connected:
            self.combo_rewards.setPlaceholderText("⚠️ Error de Conexión")
            self.combo_rewards.addItem("Offline - Revise conexión") 
            self.combo_rewards.setStyleSheet(STYLES["combobox_modern"] + "border: 1px solid #e74c3c; color: #e74c3c;")
        else:
            self.combo_rewards.setStyleSheet(STYLES["combobox_modern"])
            
            if not rewards:
                self.combo_rewards.setPlaceholderText("Sin recompensas")
                self.combo_rewards.addItem("(Ninguna recompensa en Kick)")
                self.combo_rewards.model().item(0).setEnabled(False)
            else:
                for r in rewards:
                    title = r['title']
                    if title in self.used_commands and title != self.cmd:
                        continue

                    self.combo_rewards.addItem(title, r)
                
                if self.cmd:
                    self.combo_rewards.setEditText(self.cmd)
                    index = self.combo_rewards.findText(self.cmd)
                    if index >= 0:
                        self.combo_rewards.setCurrentIndex(index)
                else:
                    self.combo_rewards.setPlaceholderText("Seleccione una recompensa...")
                    self.combo_rewards.setCurrentIndex(-1)

        self.combo_rewards.update()
        self.combo_rewards.repaint()

    def _on_reward_selected(self, index):
        if not self.combo_rewards.isEnabled(): return
        data = self.combo_rewards.itemData(index)
        
        if data and isinstance(data, dict):
            self.spin_cost.setValue(data.get('cost', 0))
            if 'background_color' in data:
                self.color = data['background_color']
                self._update_color_btn()
            kick_desc = data.get("description", "")
            if kick_desc:
                self.txt_desc.setText(kick_desc)

    def _unlink_data(self):
        self.cmd = ""
        self.description = self.txt_desc.toPlainText()
        self.cost = self.spin_cost.value()
        self.dur = self.spin_dur.value()
        self.vol = self.slider_vol.value()
        self.pos_x = self.spin_x.itemAt(1).widget().value()
        self.pos_y = self.spin_y.itemAt(1).widget().value()
        self.scale = self.slider_zoom.value() / 100.0 if hasattr(self, 'slider_zoom') else 1.0
        self.random_pos = 1 if self.chk_rand.isChecked() else 0
        self.accept()
        
    def _delete_from_kick(self):
        if ModalConfirm(self, "Eliminar de Kick", "⚠️ ¿Estás seguro de eliminar esta recompensa DIRECTAMENTE en Kick?\n\nEsta acción NO se puede deshacer.").exec():
            if hasattr(self.page, 'service') and self.cmd:
                self.page.service.delete_reward_from_kick(self.cmd)
                ToastNotification(self.page, "Kick", "Recompensa eliminada de Kick.", "status_success").show_toast()
            self._unlink_data()

    def _save_data(self):
        self.cmd = self.combo_rewards.currentText().strip()
        self.description = self.txt_desc.toPlainText()
        self.cost = self.spin_cost.value()
        self.dur = self.spin_dur.value()
        self.vol = self.slider_vol.value()
        self.pos_x = self.spin_x.itemAt(1).widget().value()
        self.pos_y = self.spin_y.itemAt(1).widget().value()
        self.scale = self.slider_zoom.value() / 100.0 if hasattr(self, 'slider_zoom') else 1.0
        self.random_pos = 1 if self.chk_rand.isChecked() else 0
        self.accept()