# ui/dialogs/edit_media_modal.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSpinBox, QSlider
)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, STYLES, THEME_DARK
from ui.utils import get_icon

class ModalEditMedia(QDialog):
    def __init__(self, parent, filename, ftype, data):
        super().__init__(parent)
        self.filename = filename
        self.ftype = ftype
        
        # Cargar valores iniciales
        self.cmd = data.get("cmd", "")
        self.cost = int(data.get("cost", 0))
        self.dur = int(data.get("dur", 0))
        self.vol = int(data.get("volume", 100))
        self.scale = float(data.get("scale", 1.0))

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 480) 
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        body = QFrame()
        body.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_DARK['Black_N2']};
                border: 1px solid {THEME_DARK['NeonGreen_Main']}; 
                border-radius: 16px;
            }}
        """)
        l = QVBoxLayout(body)
        l.setContentsMargins(*LAYOUT["margins"])
        l.setSpacing(LAYOUT["spacing"])

        l.addWidget(QLabel(f"Editar: {self.filename}", styleSheet="border:none;", objectName="h3"))

        # 1. Comando
        l.addWidget(QLabel("Comando (Trigger):", styleSheet="border:none;", objectName="subtitle"))
        self.txt_cmd = QLineEdit(self.cmd)
        self.txt_cmd.setPlaceholderText("Ej: !susto")
        self.txt_cmd.setStyleSheet(STYLES["input"])
        l.addWidget(self.txt_cmd)

        # 2. Costo y Cooldown
        h_nums = QHBoxLayout()
        v_cost = QVBoxLayout()
        v_cost.addWidget(QLabel("Costo ($):", styleSheet="border:none;", objectName="subtitle"))
        self.spin_cost = QSpinBox()
        self.spin_cost.setRange(0, 100000)
        self.spin_cost.setValue(self.cost)
        self.spin_cost.setStyleSheet(STYLES["spinbox_modern"] + "color: #FFD700;")
        v_cost.addWidget(self.spin_cost)
        
        v_dur = QVBoxLayout()
        v_dur.addWidget(QLabel("Cooldown (s):", styleSheet="border:none;", objectName="subtitle"))
        self.spin_dur = QSpinBox()
        self.spin_dur.setRange(0, 3600)
        self.spin_dur.setValue(self.dur)
        self.spin_dur.setStyleSheet(STYLES["spinbox_modern"])
        v_dur.addWidget(self.spin_dur)
        
        h_nums.addLayout(v_cost)
        h_nums.addSpacing(15)
        h_nums.addLayout(v_dur)
        l.addLayout(h_nums)

        # 3. Volumen (Agregado btn default 75)
        h_lbl_vol = QHBoxLayout()
        h_lbl_vol.addWidget(QLabel("Volumen:", styleSheet="border:none;", objectName="subtitle"))
        h_lbl_vol.addStretch()
        
        btn_def_vol = self._create_mini_btn("75%", lambda: self.slider_vol.setValue(75))
        h_lbl_vol.addWidget(btn_def_vol)
        l.addLayout(h_lbl_vol)

        h_vol = QHBoxLayout()
        self.lbl_vol = QLabel(f"{self.vol}%", styleSheet="color: white; min-width: 35px; border:none;")
        self.slider_vol = QSlider(Qt.Orientation.Horizontal) 
        self.slider_vol.setStyleSheet("background-color: transparent;")
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.vol)
        self.slider_vol.valueChanged.connect(lambda v: self.lbl_vol.setText(f"{v}%"))
        h_vol.addWidget(self.slider_vol)
        h_vol.addWidget(self.lbl_vol)
        l.addLayout(h_vol)

        # 4. Zoom (Agregado btn default 0.4 y limite 1.5x)
        if self.ftype == "video":
            h_lbl_zoom = QHBoxLayout()
            h_lbl_zoom.addWidget(QLabel("Zoom / Escala:", styleSheet="border:none;", objectName="subtitle"))
            h_lbl_zoom.addStretch()
            
            # Botón para ponerlo en 0.4x (40)
            btn_def_zoom = self._create_mini_btn("0.4x", lambda: self.slider_zoom.setValue(40))
            h_lbl_zoom.addWidget(btn_def_zoom)
            l.addLayout(h_lbl_zoom)

            h_zoom = QHBoxLayout()
            self.lbl_zoom = QLabel(f"{self.scale:.1f}x", styleSheet="color: white; min-width: 35px; border:none;")
            
            self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
            self.slider_zoom.setStyleSheet("background-color: transparent;")
            self.slider_zoom.setRange(10, 150) 
            self.slider_zoom.setValue(int(self.scale * 100))
            self.slider_zoom.valueChanged.connect(lambda v: self.lbl_zoom.setText(f"{v/100:.1f}x"))
            
            h_zoom.addWidget(self.slider_zoom)
            h_zoom.addWidget(self.lbl_zoom)
            l.addLayout(h_zoom)

        l.addStretch()

        # Botones Acción
        h_btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save_data)
        btn_save.setStyleSheet(STYLES["btn_solid_primary"])
        
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        l.addLayout(h_btns)
        
        layout.addWidget(body)

    def _create_mini_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(50, 30)
        btn.clicked.connect(func)
        btn.setStyleSheet(STYLES["btn_nav"])
        return btn

    def _save_data(self):
        self.cmd = self.txt_cmd.text().strip()
        self.cost = self.spin_cost.value()
        self.dur = self.spin_dur.value()
        self.vol = self.slider_vol.value()
        self.scale = self.slider_zoom.value() / 100.0 if self.ftype == "video" else 1.0
        self.accept()