# frontend/dialogs/trigger_modal.py

import json
import os
import re
from PyQt6.QtWidgets import (
    QCheckBox, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QSlider, QComboBox,
    QTextEdit, QColorDialog, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QCursor, QTextCursor

# --- IMPORTACIONES DEL PROYECTO ---
from backend.utils.paths import get_config_path
from frontend.alerts.modal_alert import ModalConfirm
from frontend.alerts.toast_alert import ToastNotification
from frontend.factories import create_icon_btn
from frontend.theme import STYLES, THEME_DARK, get_switch_style
from frontend.components.base_modal import BaseModal

# =============================================================================
# WORKER: CARGA ASÍNCRONA DE KICK
# =============================================================================
class RewardsLoaderWorker(QThread):
    finished = pyqtSignal(bool, list)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        # 1. Verificar Token
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

        if not has_token:
            self.finished.emit(False, [])
            return

        # 2. Obtener Recompensas
        try:
            rewards = self.service.get_available_kick_rewards()
            self.finished.emit(True, rewards)
        except:
            self.finished.emit(False, [])

# =============================================================================
# CLASE PRINCIPAL: MODAL DE EDICIÓN
# =============================================================================
class ModalEditMedia(BaseModal):
    def __init__(self, parent_page, filename, ftype, data):
        super().__init__(parent_page, width=420, height=620)
        
        self.page = parent_page 
        self.filename = filename
        self.ftype = ftype
        
        # Carga de Datos Iniciales
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
        
        # Iniciar carga con retraso para asegurar que la UI existe
        QTimer.singleShot(100, self._start_async_loading)

    def _setup_ui(self):
        l = self.body_layout
        l.setSpacing(10)

        # 1. TÍTULO DEL ARCHIVO
        l.addWidget(QLabel(f"Configurar: {self.filename}", styleSheet=STYLES["label_title"]))

        # 2. SELECCIÓN DE RECOMPENSA (COMBO + BOTÓN REFRESH)
        l.addWidget(QLabel("Nombre del Canje (Kick) - Max 20 letras:", styleSheet="border:none; color: #AAA; font-size: 12px;"))
        
        h_combo = QHBoxLayout()
        h_combo.setSpacing(5)

        self.combo_rewards = QComboBox()
        self.combo_rewards.setEditable(True) 
        self.combo_rewards.setPlaceholderText("Cargando lista...") 
        self.combo_rewards.lineEdit().setMaxLength(20) # Límite físico de entrada
        self.combo_rewards.setStyleSheet(STYLES["combobox"])
        
        # Conexiones de Señales
        self.combo_rewards.editTextChanged.connect(self._validate_title)
        self.combo_rewards.currentIndexChanged.connect(self._on_reward_selected)
        
        h_combo.addWidget(self.combo_rewards)

        # Botón de Refrescar (Usando Factory)
        self.btn_refresh = create_icon_btn(
            "refresh-cw.svg",            
            self._start_async_loading,   
            tooltip="Recargar lista de Kick"
        )
        h_combo.addWidget(self.btn_refresh)

        l.addLayout(h_combo)

        # 3. APARIENCIA KICK (COLOR + DESCRIPCIÓN)
        frame_kick = QFrame()
        frame_kick.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border-radius: 8px; padding: 5px;")
        lk = QVBoxLayout(frame_kick)
        
        # Selector de Color
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
        
        # Descripción con Contador
        h_desc_lbl = QHBoxLayout()
        h_desc_lbl.addWidget(QLabel("Descripción:", styleSheet="border:none; color: #DDD;"))
        self.lbl_desc_count = QLabel("0/200")
        self.lbl_desc_count.setStyleSheet("border:none; color: #666; font-size: 11px;")
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
        l.addWidget(frame_kick)

        # 4. CONFIGURACIÓN NUMÉRICA (COSTO Y DURACIÓN)
        h_nums = QHBoxLayout()
        v_cost = QVBoxLayout()
        v_cost.addWidget(QLabel("Costo:", styleSheet="border:none; color: #888;"))
        self.spin_cost = QSpinBox()
        self.spin_cost.setRange(1, 1000000) # <--- CAMBIAR DE 0 A 1
        self.spin_cost.setValue(self.cost if self.cost > 0 else 1) # <--- ASEGURAR MÍNIMO 1
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

        # 5. COORDENADAS (X / Y) Y POSICIÓN ALEATORIA (AHORA CON SWITCH)
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
        
        l.addLayout(h_pos)

        # 6. SLIDERS (VOLUMEN Y ESCALA)
        # Volumen
        w_vol = QWidget()
        w_vol.setStyleSheet("background: transparent;")
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

        # Escala (Solo si es video)
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

        # 7. BOTONES DE ACCIÓN (NUEVO BOTÓN DESVINCULAR Y ELIMINAR KICK)
        h_btns = QHBoxLayout()
        
        self.btn_unlink = QPushButton("Desvincular")
        self.btn_unlink.clicked.connect(self._unlink_data)
        self.btn_unlink.setStyleSheet(f"""
            QPushButton {{ 
                background-color: transparent; 
                color: {THEME_DARK['status_error']}; 
                border: 1px solid {THEME_DARK['status_error']}; 
                border-radius: 4px; padding: 5px 15px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['status_error']}; 
                color: white; 
            }}
        """)

        # --- NUEVO BOTÓN: ELIMINAR DE KICK ---
        self.btn_delete_kick = QPushButton("Eliminar de Kick")
        self.btn_delete_kick.clicked.connect(self._delete_from_kick)
        self.btn_delete_kick.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {THEME_DARK['status_error']}; 
                color: white; 
                border: none; 
                border-radius: 4px; padding: 5px 15px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: #c0392b; 
            }}
        """)

        # Si no tiene recompensa asignada, ocultamos los botones destructivos
        if not self.cmd:
            self.btn_unlink.hide()
            self.btn_delete_kick.hide() # <--- Se oculta si no hay recompensa
            
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        self.btn_save = QPushButton("Guardar") 
        self.btn_save.clicked.connect(self._save_data)
        self.btn_save.setStyleSheet(STYLES["btn_primary"])
        
        # Agregamos los botones al layout horizontal
        h_btns.addWidget(self.btn_unlink)
        h_btns.addWidget(self.btn_delete_kick) # <--- Lo agregamos aquí
        h_btns.addStretch() # Empuja cancelar y guardar a la derecha
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(self.btn_save)
        
        l.addLayout(h_btns)
        self._validate_desc()

    # =========================================================================
    # LÓGICA DE VALIDACIÓN Y UI
    # =========================================================================
    def _validate_title(self, text):
        """Valida caracteres del título."""
        # Solo letras, números y espacios
        pattern = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ]*$"
        
        if not re.match(pattern, text):
            self.combo_rewards.setStyleSheet(STYLES["combobox"] + "border: 2px solid #e74c3c;")
            self.btn_save.setEnabled(False) 
        else:
            self.combo_rewards.setStyleSheet(STYLES["combobox"])
            self._check_save_enabled()

    def _validate_desc(self):
        """Valida longitud y caracteres de la descripción."""
        text = self.txt_desc.toPlainText()
        limit = 200
        
        # 1. Control de Longitud (Con bloqueo de señales para evitar recursividad)
        if len(text) > limit:
            self.txt_desc.blockSignals(True) # <--- CRÍTICO
            text = text[:limit]
            self.txt_desc.setPlainText(text)
            cursor = self.txt_desc.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.txt_desc.setTextCursor(cursor)
            self.txt_desc.blockSignals(False) # <--- CRÍTICO
        
        self.lbl_desc_count.setText(f"{len(text)}/{limit}")

        # 2. Validación de Símbolos
        # Permite: Letras, números, espacios y PUNTUACIÓN BÁSICA (.,;¿?!)
        pattern = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ.,;¿?!]*$"
        
        # re.DOTALL permite que el punto coincida con saltos de línea
        if not re.match(pattern, text, re.DOTALL):
            self.txt_desc.setStyleSheet(STYLES["text_edit_console"] + "border: 2px solid #e74c3c;")
            self.btn_save.setEnabled(False)
        else:
            self.txt_desc.setStyleSheet(STYLES["text_edit_console"])
            self._check_save_enabled()

    def _check_save_enabled(self):
        """Reactiva el botón guardar solo si AMBOS campos son válidos."""
        pat_title = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ]*$"
        pat_desc = r"^[a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚ.,;¿?!]*$"
        
        title_ok = bool(re.match(pat_title, self.combo_rewards.currentText()))
        desc_ok = bool(re.match(pat_desc, self.txt_desc.toPlainText(), re.DOTALL))
        
        if title_ok and desc_ok:
            self.btn_save.setEnabled(True)
        else:
            self.btn_save.setEnabled(False)

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

    # =========================================================================
    # LÓGICA ASÍNCRONA Y CARGA DE DATOS
    # =========================================================================
    def _start_async_loading(self):
        """Inicia la carga de Kick de forma segura y controlada."""
        # 1. PROTECCIÓN DE HILOS
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            return 

        # 2. Feedback Visual
        self.combo_rewards.clear()
        self.combo_rewards.setPlaceholderText("Buscando en Kick...")
        self.combo_rewards.setEnabled(False) 
        self.btn_refresh.setEnabled(False)

        # 3. Iniciar Worker
        if hasattr(self.page, 'service'):
            self.worker = RewardsLoaderWorker(self.page.service)
            self.worker.finished.connect(self._on_rewards_loaded)
            
            # Limpieza automática de memoria
            self.worker.finished.connect(lambda: setattr(self, 'worker', None))
            self.worker.finished.connect(self.worker.deleteLater)
            
            self.worker.start()

    def _on_rewards_loaded(self, is_connected, rewards):
        """Callback al terminar la carga."""
        self.combo_rewards.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        
        self.combo_rewards.clear() 
        
        if not is_connected:
            self.combo_rewards.setPlaceholderText("⚠️ Error de Conexión")
            self.combo_rewards.addItem("Offline - Revise conexión") 
            self.combo_rewards.setStyleSheet(STYLES["combobox"] + "border: 1px solid #e74c3c; color: #e74c3c;")
        else:
            self.combo_rewards.setStyleSheet(STYLES["combobox"])
            
            if not rewards:
                self.combo_rewards.setPlaceholderText("Sin recompensas")
                self.combo_rewards.addItem("(Ninguna recompensa en Kick)")
                self.combo_rewards.model().item(0).setEnabled(False)
            else:
                for r in rewards:
                    self.combo_rewards.addItem(r['title'], r)
                
                # Restaurar selección anterior
                if self.cmd:
                    self.combo_rewards.setEditText(self.cmd)
                    index = self.combo_rewards.findText(self.cmd)
                    if index >= 0:
                        self.combo_rewards.setCurrentIndex(index)
                else:
                    self.combo_rewards.setPlaceholderText("Seleccione una recompensa...")
                    self.combo_rewards.setCurrentIndex(-1)

        # Forzar repintado UI
        self.combo_rewards.update()
        self.combo_rewards.repaint()

    def _on_reward_selected(self, index):
        """Rellena el formulario si seleccionas una recompensa existente."""
        if not self.combo_rewards.isEnabled(): return
        data = self.combo_rewards.itemData(index)
        
        if data and isinstance(data, dict):
            # Costo
            self.spin_cost.setValue(data.get('cost', 0))
            # Color
            if 'background_color' in data:
                self.color = data['background_color']
                self._update_color_btn()
            # Descripción (Sincronización)
            kick_desc = data.get("description", "")
            if kick_desc:
                self.txt_desc.setText(kick_desc)

    def _unlink_data(self):
        """Desvincula la recompensa manteniendo la configuración del archivo local."""
        self.cmd = ""
        # Guardamos el resto de valores por si acaso
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
            
        self.random_pos = 1 if self.chk_rand.isChecked() else 0
        self.accept()
        
    def _delete_from_kick(self):
        """Elimina la recompensa permanentemente en Kick y la desvincula localmente."""
        if ModalConfirm(self, "Eliminar de Kick", "⚠️ ¿Estás seguro de eliminar esta recompensa DIRECTAMENTE en Kick?\n\nEsta acción NO se puede deshacer.").exec():
            
            # 1. Borrar de Kick a través del servicio
            if hasattr(self.page, 'service') and self.cmd:
                self.page.service.delete_reward_from_kick(self.cmd)
                ToastNotification(self.page, "Kick", "Recompensa eliminada de Kick.", "status_success").show_toast()
            
            # 2. Reutilizamos la lógica de desvincular para limpiar el archivo localmente y cerrar
            self._unlink_data()

    def _save_data(self):
        # Recopilación final de datos
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
            
        self.random_pos = 1 if self.chk_rand.isChecked() else 0
        self.accept()