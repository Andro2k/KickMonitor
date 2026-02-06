# frontend/dialogs/trigger_modal.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSpinBox, QSlider, QComboBox,
    QTextEdit, QColorDialog, QWidget, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QCursor
from frontend.theme import STYLES, THEME_DARK
from frontend.components.base_modal import BaseModal

class RewardsLoaderWorker(QThread):
    finished = pyqtSignal(list)
    def __init__(self, service):
        super().__init__()
        self.service = service
    def run(self):
        try:
            rewards = self.service.get_available_kick_rewards()
            self.finished.emit(rewards)
        except:
            self.finished.emit([])

class ModalEditMedia(BaseModal):
    def __init__(self, parent_page, filename, ftype, data):
        super().__init__(parent_page, width=420, height=650) # Aumenté un poco la altura
        
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
        l.addWidget(QLabel(f"Configurar: {self.filename}", styleSheet="border:none; font-size: 14px; font-weight: bold; color: white;"))

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
        self.txt_desc.setPlaceholderText("Instrucciones...")
        self.txt_desc.setText(self.description)
        self.txt_desc.setFixedHeight(45)
        self.txt_desc.setStyleSheet(STYLES["input_cmd"])
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

        # 6. SLIDERS CON ETIQUETAS
        # Volumen
        h_vol_lbl = QHBoxLayout()
        h_vol_lbl.addWidget(QLabel("Volumen:", styleSheet="border:none; color: #888;"))
        self.lbl_vol_val = QLabel(f"{self.vol}%")
        self.lbl_vol_val.setStyleSheet("color: #AAA; font-weight: bold; border:none;")
        h_vol_lbl.addWidget(self.lbl_vol_val)
        h_vol_lbl.addStretch()
        l.addLayout(h_vol_lbl)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.vol)
        self.slider_vol.valueChanged.connect(lambda v: self.lbl_vol_val.setText(f"{v}%"))
        l.addWidget(self.slider_vol)

        # Escala (SOLO SI ES VIDEO)
        if self.ftype == "video":
            h_zoom_lbl = QHBoxLayout()
            h_zoom_lbl.addWidget(QLabel("Tamaño (Escala):", styleSheet="border:none; color: #888;"))
            self.lbl_zoom_val = QLabel(f"{int(self.scale * 100)}%")
            self.lbl_zoom_val.setStyleSheet("color: #AAA; font-weight: bold; border:none;")
            h_zoom_lbl.addWidget(self.lbl_zoom_val)
            h_zoom_lbl.addStretch()
            l.addLayout(h_zoom_lbl)

            self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
            self.slider_zoom.setRange(10, 200) # 10% a 200%
            self.slider_zoom.setValue(int(self.scale * 100))
            self.slider_zoom.valueChanged.connect(lambda v: self.lbl_zoom_val.setText(f"{v}%"))
            l.addWidget(self.slider_zoom)
        
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

    def _create_coord_spin(self, label, val):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label, styleSheet="border:none; color:#888;"))
        spin = QSpinBox()
        spin.setRange(-5000, 5000)
        spin.setValue(val)
        spin.setStyleSheet(STYLES["spinbox_modern"])
        layout.addWidget(spin)
        return layout

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

    def _on_rewards_loaded(self, rewards):
        self.combo_rewards.clear()
        for r in rewards:
            self.combo_rewards.addItem(r['title'], r)
        
        if self.cmd:
            self.combo_rewards.setEditText(self.cmd)
            index = self.combo_rewards.findText(self.cmd)
            if index >= 0:
                self.combo_rewards.setCurrentIndex(index)
        else:
            self.combo_rewards.setPlaceholderText("Nuevo o existente...")
            self.combo_rewards.setCurrentIndex(-1)
        self.combo_rewards.setEnabled(True)

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