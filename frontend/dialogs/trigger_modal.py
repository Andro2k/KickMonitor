# frontend/dialogs/trigger_modal.py

import json
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QSlider, QComboBox,
    QTextEdit, QColorDialog, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QCursor
from backend.utils.paths import get_config_path
from frontend.theme import STYLES, THEME_DARK
from frontend.components.base_modal import BaseModal

class RewardsLoaderWorker(QThread):
    finished = pyqtSignal(bool, list)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        # 1. Verificar si tenemos token guardado
        has_token = False
        try:
            path = os.path.join(get_config_path(), "session.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    if data.get("access_token"):
                        has_token = True
        except:
            has_token = False

        # Si no hay token, ni intentamos conectar
        if not has_token:
            self.finished.emit(False, [])
            return

        # 2. Intentar descargar recompensas
        try:
            rewards = self.service.get_available_kick_rewards()
            # Si devuelve una lista (aunque sea vacía), asumimos conexión exitosa
            self.finished.emit(True, rewards)
        except:
            # Si falla la petición (ej: sin internet), enviamos desconectado
            self.finished.emit(False, [])

class ModalEditMedia(BaseModal):
    def __init__(self, parent_page, filename, ftype, data):
        super().__init__(parent_page, width=420, height=560)
        
        self.page = parent_page 
        self.filename = filename
        self.ftype = ftype
        
        # Carga de datos
        self.cmd = data.get("cmd", "")
        self.cost = int(data.get("cost", 0))
        self.dur = int(data.get("dur", 0))
        self.vol = int(data.get("volume", 100))
        self.scale = float(data.get("scale", 1.0))
        self.pos_x = int(data.get("pos_x", 0))
        self.pos_y = int(data.get("pos_y", 0))
        self.color = data.get("color", "#53fc18") 
        self.description = data.get("description", "Trigger KickMonitor")
        
        self._setup_ui()
        self._start_async_loading()

    def _setup_ui(self):
        l = self.body_layout
        l.setSpacing(10)

        # 1. TÍTULO
        l.addWidget(QLabel(f"Configurar: {self.filename}", styleSheet=STYLES["label_title"]))

        # 2. SELECCIONAR RECOMPENSA
        l.addWidget(QLabel("Nombre del Canje (Kick):", styleSheet="border:none; color: #AAA;"))
        self.combo_rewards = QComboBox()
        self.combo_rewards.setEditable(True) 
        self.combo_rewards.setPlaceholderText("Cargando lista de Kick...") 
        self.combo_rewards.setEnabled(False) 
        self.combo_rewards.setStyleSheet(STYLES["combobox"])
        if self.cmd:
            self.combo_rewards.addItem(self.cmd)
            self.combo_rewards.setCurrentText(self.cmd)
        self.combo_rewards.currentIndexChanged.connect(self._on_reward_selected)
        l.addWidget(self.combo_rewards)

        # 3. APARIENCIA KICK
        frame_kick = QFrame()
        frame_kick.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border-radius: 8px; padding: 5px;")
        lk = QVBoxLayout(frame_kick)
        
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
        
        lk.addWidget(QLabel("Descripción:", styleSheet="border:none; color: #DDD;"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setStyleSheet(STYLES["text_edit_console"])
        self.txt_desc.setPlaceholderText("Instrucciones...")
        self.txt_desc.setText(self.description)
        self.txt_desc.setFixedHeight(65)
        lk.addWidget(self.txt_desc)
        l.addWidget(frame_kick)

        # 4. COSTO Y DURACIÓN
        h_nums = QHBoxLayout()
        v_cost = QVBoxLayout()
        v_cost.addWidget(QLabel("Costo:", styleSheet="border:none; color: #888;"))
        self.spin_cost = QSpinBox()
        self.spin_cost.setRange(0, 1000000)
        self.spin_cost.setValue(self.cost)
        self.spin_cost.setStyleSheet(STYLES["spinbox_modern"] + "color: #53fc18; font-weight: bold;")
        v_cost.addWidget(self.spin_cost)
        h_nums.addLayout(v_cost)
        
        v_dur = QVBoxLayout()
        v_dur.addWidget(QLabel("Duración (s):", styleSheet="border:none; color: #888;"))
        self.spin_dur = QSpinBox()
        self.spin_dur.setRange(0, 300)
        self.spin_dur.setValue(self.dur)
        self.spin_dur.setStyleSheet(STYLES["spinbox_modern"])
        v_dur.addWidget(self.spin_dur)
        h_nums.addLayout(v_dur)
        l.addLayout(h_nums)

        # 5. COORDENADAS
        h_pos = QHBoxLayout()
        self.spin_x = self._create_coord_spin("Pos X:", self.pos_x)
        self.spin_y = self._create_coord_spin("Pos Y:", self.pos_y)
        h_pos.addLayout(self.spin_x)
        h_pos.addLayout(self.spin_y)
        l.addLayout(h_pos)

        # 6. SLIDERS CON ETIQUETAS (Fondo Transparente)
        
        # --- VOLUMEN ---
        # Contenedor para alinear etiqueta y valor
        w_vol = QWidget()
        w_vol.setStyleSheet("background: transparent;") # <--- CLAVE: Fondo transparente
        l_vol = QVBoxLayout(w_vol)
        l_vol.setContentsMargins(0,0,0,0)
        l_vol.setSpacing(2)

        h_vol_lbl = QHBoxLayout()
        h_vol_lbl.addWidget(QLabel("Volumen:", styleSheet="border:none; color: #888; background: transparent;"))
        self.lbl_vol_val = QLabel(f"{self.vol}%")
        self.lbl_vol_val.setStyleSheet("color: #AAA; font-weight: bold; border:none; background: transparent;")
        h_vol_lbl.addWidget(self.lbl_vol_val)
        h_vol_lbl.addStretch()
        l_vol.addLayout(h_vol_lbl)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.vol)
        self.slider_vol.valueChanged.connect(lambda v: self.lbl_vol_val.setText(f"{v}%"))
        l_vol.addWidget(self.slider_vol)
        l.addWidget(w_vol)

        # --- ESCALA (SOLO SI ES VIDEO) ---
        if self.ftype == "video":
            w_zoom = QWidget()
            w_zoom.setStyleSheet("background: transparent;")
            l_zoom = QVBoxLayout(w_zoom)
            l_zoom.setContentsMargins(0,0,0,0)
            l_zoom.setSpacing(2)

            h_zoom_lbl = QHBoxLayout()
            h_zoom_lbl.addWidget(QLabel("Tamaño (Escala):", styleSheet="border:none; color: #888; background: transparent;"))
            self.lbl_zoom_val = QLabel(f"{int(self.scale * 100)}%")
            self.lbl_zoom_val.setStyleSheet("color: #AAA; font-weight: bold; border:none; background: transparent;")
            h_zoom_lbl.addWidget(self.lbl_zoom_val)
            h_zoom_lbl.addStretch()
            l_zoom.addLayout(h_zoom_lbl)

            self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
            self.slider_zoom.setRange(10, 200) 
            self.slider_zoom.setValue(int(self.scale * 100))
            self.slider_zoom.valueChanged.connect(lambda v: self.lbl_zoom_val.setText(f"{v}%"))
            l_zoom.addWidget(self.slider_zoom)
            l.addWidget(w_zoom)
        
        l.addStretch()

        # 7. BOTONES
        h_btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self._save_data)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        l.addLayout(h_btns)

    def _create_coord_spin(self, label_text, val):
        # CORRECCIÓN: Creamos el layout directamente sin un widget padre temporal
        l = QVBoxLayout() 
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(2)
        
        # Etiqueta con fondo transparente
        l.addWidget(QLabel(label_text, styleSheet="border:none; color:#888; background: transparent;"))
        
        # SpinBox configurado sin negativos
        spin = QSpinBox()
        spin.setRange(0, 5000) # Mínimo 0
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

    def _start_async_loading(self):
        if hasattr(self.page, 'service'):
            self.worker = RewardsLoaderWorker(self.page.service)
            self.worker.finished.connect(self._on_rewards_loaded)
            self.worker.start()

    def _on_rewards_loaded(self, is_connected, rewards):
        self.combo_rewards.clear()
        
        if not is_connected:
            # ESTADO: DESCONECTADO
            self.combo_rewards.setPlaceholderText("⚠️ Desconectado (Requiere Login)")
            self.combo_rewards.setStyleSheet(STYLES["combobox"] + "border: 1px solid #e74c3c; color: #e74c3c;")
            self.combo_rewards.setEnabled(False)
        else:
            # ESTADO: CONECTADO
            self.combo_rewards.setEnabled(True)
            self.combo_rewards.setStyleSheet(STYLES["combobox"])
            
            if not rewards:
                self.combo_rewards.setPlaceholderText("Conectado (Sin recompensas creadas)")
            else:
                for r in rewards:
                    self.combo_rewards.addItem(r['title'], r)
                
                # Restaurar selección previa si existe
                if self.cmd:
                    self.combo_rewards.setEditText(self.cmd)
                    index = self.combo_rewards.findText(self.cmd)
                    if index >= 0:
                        self.combo_rewards.setCurrentIndex(index)
                else:
                    self.combo_rewards.setPlaceholderText("Seleccione una recompensa...")
                    self.combo_rewards.setCurrentIndex(-1)

    def _on_reward_selected(self, index):
        if not self.combo_rewards.isEnabled(): return
        data = self.combo_rewards.itemData(index)
        if data and isinstance(data, dict):
            self.spin_cost.setValue(data.get('cost', 0))
            if 'background_color' in data:
                self.color = data['background_color']
                self._update_color_btn()

    def _save_data(self):
        self.cmd = self.combo_rewards.currentText().strip()
        self.description = self.txt_desc.toPlainText()
        self.cost = self.spin_cost.value()
        self.dur = self.spin_dur.value()
        self.vol = self.slider_vol.value()
        self.pos_x = self.spin_x.itemAt(1).widget().value()
        self.pos_y = self.spin_y.itemAt(1).widget().value()
        
        if hasattr(self, 'slider_zoom'):
            self.scale = self.slider_zoom.value() / 100.0
        else:
            self.scale = 1.0
            
        self.accept()