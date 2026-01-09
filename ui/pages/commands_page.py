# ui/pages/commands_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QLineEdit, QCheckBox, QFrame, 
    QDialog, QAbstractItemView, QSpinBox, QPlainTextEdit,
    QFileDialog # <--- IMPORTANTE: Agregamos esto
)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, THEME_DARK, STYLES, RADIUS, get_switch_style
from ui.utils import get_icon
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from services.commands_service import CommandsService

# ==========================================
#      MODAL DE EDICIÓN (MULTILÍNEA)
# ==========================================
class ModalEditCommand(QDialog):
    # ... (MANTENER ESTA CLASE EXACTAMENTE IGUAL QUE ANTES) ...
    def __init__(self, parent, trigger, response, cooldown):
        super().__init__(parent)
        self.trigger_orig = trigger
        self.new_trigger = trigger
        self.new_response = response
        self.new_cooldown = cooldown
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(500, 450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        
        body = QFrame()
        body.setStyleSheet(f"background-color: {THEME_DARK['Black_N1']}; border: 1px solid {THEME_DARK['NeonGreen_Main']}; border-radius: 16px;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(15)

        lbl_tit = QLabel("Editar Comando", objectName="h3")
        lbl_tit.setStyleSheet("border: none;")
        body_layout.addWidget(lbl_tit)

        body_layout.addWidget(QLabel("Disparador (Trigger):", styleSheet="color:#888; font-size:12px; border:none;"))
        self.inp_trig = QLineEdit(self.trigger_orig)
        self.inp_trig.setStyleSheet(STYLES["input"])
        body_layout.addWidget(self.inp_trig)
        
        body_layout.addWidget(QLabel("Respuesta:", styleSheet="color:#888; font-size:12px; border:none;"))
        self.inp_resp = QPlainTextEdit(self.new_response)
        self.inp_resp.setPlaceholderText("Escribe la respuesta aquí...")
        self.inp_resp.setFixedHeight(120)
        self.inp_resp.setStyleSheet(f"QPlainTextEdit {{ background-color: {THEME_DARK['Black_N2']}; color: {THEME_DARK['White_N1']};  padding: 8px; font-size: 13px; border-radius: 6px; }} QPlainTextEdit:focus {{ border: 1px solid {THEME_DARK['NeonGreen_Main']}; }}")
        body_layout.addWidget(self.inp_resp)
        
        body_layout.addWidget(self._create_chips_layout())

        row_cd = QHBoxLayout()
        row_cd.addWidget(QLabel("Tiempo de Espera:", styleSheet="color:#888; font-size:12px; border:none;"))
        self.inp_cd = QSpinBox()
        self.inp_cd.setRange(0, 3600)
        self.inp_cd.setValue(self.new_cooldown)
        self.inp_cd.setSuffix("s")
        self.inp_cd.setFixedWidth(80)
        self.inp_cd.setStyleSheet(STYLES["spinbox_modern"])
        row_cd.addWidget(self.inp_cd)
        row_cd.addStretch()
        body_layout.addLayout(row_cd)

        body_layout.addStretch()

        h_btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"color: {THEME_DARK['Gray_N1']}; background: transparent;  border-radius: 8px; padding: 8px 16px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Guardar Cambios")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(f"background-color: {THEME_DARK['NeonGreen_Main']}; color: black; font-weight: bold; border-radius: 8px; padding: 8px 20px; border:none;")
        btn_save.clicked.connect(self._validate_and_accept)
        
        h_btns.addStretch()
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        body_layout.addLayout(h_btns)
        layout.addWidget(body)

    def _create_chips_layout(self):
        container = QWidget(); l = QHBoxLayout(container); l.setContentsMargins(0,0,0,0); l.setSpacing(5); container.setStyleSheet("background: transparent; border: none;")
        vars_list = ["{user}", "{target}", "{points}", "{song}", "{random}"]
        for v in vars_list:
            btn = QPushButton(v)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ background: {THEME_DARK['Black_N2']}; color: {THEME_DARK['NeonGreen_Main']};  border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ border-color: {THEME_DARK['NeonGreen_Main']}; }}")
            btn.clicked.connect(lambda _, t=v: (self.inp_resp.insertPlainText(t), self.inp_resp.setFocus()))
            l.addWidget(btn)
        l.addStretch()
        return container

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if ModalConfirm(self, "Cancelar", "¿Salir sin guardar?").exec(): self.reject()
        else: super().keyPressEvent(event)

    def _validate_and_accept(self):
        t = self.inp_trig.text().strip()
        r = self.inp_resp.toPlainText().strip()
        c = self.inp_cd.value()
        if t and r:
            self.new_trigger = t; self.new_response = r; self.new_cooldown = c
            self.accept()

# ==========================================
#      PÁGINA PRINCIPAL
# ==========================================
class CommandsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = CommandsService(db_handler)
        self.init_ui()

    # ==========================================
    # 1. UI SETUP
    # ==========================================
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*LAYOUT["margins"])
        layout.setSpacing(LAYOUT["spacing"])

        self._setup_header(layout)
        self._setup_form(layout)
        self._setup_table(layout)
        
        self.load_table_data()

    def _setup_header(self, layout):
        h_head = QHBoxLayout()
        
        # Títulos (Izquierda)
        v_tit = QVBoxLayout()
        v_tit.setSpacing(2)
        v_tit.addWidget(QLabel("Comandos de Chat", objectName="h2"))
        v_tit.addWidget(QLabel("Configura respuestas automáticas y tiempo de espera.", objectName="subtitle"))
        h_head.addLayout(v_tit)
        
        h_head.addStretch()
        
        # Botones (Derecha)
        btn_export = self._create_top_btn("download.svg", "Exportar", self._handle_export)
        btn_import = self._create_top_btn("upload.svg", "Importar", self._handle_import)
        
        h_head.addWidget(btn_export)
        h_head.addWidget(btn_import)
        
        layout.addLayout(h_head)

    def _setup_form(self, layout):
        """Formulario de creación rápida."""
        form_frame = QFrame()
        form_frame.setStyleSheet(f"background: {THEME_DARK['Black_N3']}; border-radius: 10px; ")
        
        main_form_layout = QVBoxLayout(form_frame)
        main_form_layout.setContentsMargins(10, 10, 10, 10)
        main_form_layout.setSpacing(5)

        # 1. Barra de Chips (Variables rápidas)
        self.txt_response = QLineEdit() 
        chips_widget = self._create_variable_chips(self.txt_response)

        # 2. Inputs (Horizontal)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        # Trigger
        self.txt_trigger = QLineEdit()
        self.txt_trigger.setPlaceholderText("!comando")
        self.txt_trigger.setStyleSheet(STYLES["input"])
        self.txt_trigger.setFixedWidth(130)

        # Response
        self.txt_response.setPlaceholderText("Escribe la respuesta aquí...")
        self.txt_response.setStyleSheet(STYLES["input"])

        # Cooldown
        lbl_cd = QLabel("Espera:", styleSheet="border:none; color:#888; font-size:12px;")
        self.spin_cd = QSpinBox()
        self.spin_cd.setRange(0, 3600)
        self.spin_cd.setValue(5)
        self.spin_cd.setSuffix("s")
        self.spin_cd.setFixedWidth(120)
        self.spin_cd.setStyleSheet(STYLES["spinbox_modern"])

        # Botón Agregar
        btn_add = QPushButton("Agregar")
        btn_add.setIcon(get_icon("plus.svg"))
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"QPushButton {{ background-color: {THEME_DARK['Black_N3']};  padding: 8px 15px; border-radius: {RADIUS['button']}; }} QPushButton:hover {{ background-color: {THEME_DARK['NeonGreen_Dark']}; border-color: {THEME_DARK['NeonGreen_Main']};}}")
        btn_add.clicked.connect(self._handle_add_command)

        input_layout.addWidget(self.txt_trigger)
        input_layout.addWidget(self.txt_response)
        input_layout.addWidget(lbl_cd)
        input_layout.addWidget(self.spin_cd)
        input_layout.addWidget(btn_add)

        main_form_layout.addWidget(chips_widget)
        main_form_layout.addLayout(input_layout)
        
        layout.addWidget(form_frame)

    def _setup_table(self, layout):
        self.table = QTableWidget()
        self.table.setColumnCount(6) 
        self.table.setHorizontalHeaderLabels(["Trigger", "Respuesta", "Espera", "Estado", "Editar", "Borrar"])
        self.table.setStyleSheet(STYLES["table_clean"])
        
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 140)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 70)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(3, 70)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(4, 70)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(5, 70)
        
        layout.addWidget(self.table)

    # ==========================================
    # 2. CARGA DE DATOS
    # ==========================================
    def load_table_data(self):
        self.table.setRowCount(0)
        rows = self.service.get_all_commands()
        
        for idx, (trigger, response, is_active, cooldown) in enumerate(rows):
            self.table.insertRow(idx)
            
            it_trig = QTableWidgetItem(trigger)
            it_trig.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            short_resp = response[:50] + "..." if len(response) > 50 else response
            it_resp = QTableWidgetItem(short_resp.replace("\n", " "))
            it_resp.setToolTip(response)
            it_resp.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            it_cd = QTableWidgetItem(f"{cooldown}s")
            it_cd.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_cd.setForeground(Qt.GlobalColor.gray)

            w_sw = QWidget(); w_sw.setStyleSheet("background: transparent;")
            l_sw = QHBoxLayout(w_sw); l_sw.setContentsMargins(0,0,0,0); l_sw.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox(); chk.setCursor(Qt.CursorShape.PointingHandCursor); chk.setStyleSheet(get_switch_style())
            chk.setChecked(bool(is_active))
            chk.clicked.connect(lambda c, t=trigger: self.service.toggle_status(t, c))
            l_sw.addWidget(chk)

            btn_edit = self._create_action_btn("edit.svg", "#4dabf7", lambda _, t=trigger, r=response, c=cooldown: self._handle_edit_command(t, r, c))
            btn_del = self._create_action_btn("trash.svg", "#ff453a", lambda _, t=trigger: self._handle_delete_command(t))

            self.table.setItem(idx, 0, it_trig)
            self.table.setItem(idx, 1, it_resp)
            self.table.setItem(idx, 2, it_cd)
            self.table.setCellWidget(idx, 3, w_sw)
            self.table.setCellWidget(idx, 4, btn_edit)
            self.table.setCellWidget(idx, 5, btn_del)
    
    # ==========================================
    # 3. HANDLERS (LOGICA)
    # ==========================================
    def _handle_add_command(self):
        trig = self.txt_trigger.text().strip()
        resp = self.txt_response.text().strip()
        cd = self.spin_cd.value()
        
        if not trig or not resp:
            return ToastNotification(self, "Campos Vacíos", "Falta trigger o respuesta.", "Status_Yellow").show_toast()
            
        if self.service.add_or_update_command(trig, resp, cd):
            self.txt_trigger.clear()
            self.txt_response.clear()
            self.spin_cd.setValue(5)
            self.load_table_data()
            ToastNotification(self, "Creado", f"Comando {trig} guardado.", "Status_Green").show_toast()

    def _handle_delete_command(self, trigger):
        if ModalConfirm(self, "Eliminar", f"¿Estás seguro de borrar {trigger}?").exec():
            self.service.delete_command(trigger)
            self.load_table_data()

    def _handle_edit_command(self, trigger, response, cooldown):
        modal = ModalEditCommand(self, trigger, response, cooldown)
        if modal.exec() == QDialog.DialogCode.Accepted:
            if modal.new_trigger != trigger:
                self.service.delete_command(trigger)
            
            self.service.add_or_update_command(modal.new_trigger, modal.new_response, modal.new_cooldown)
            self.load_table_data()
            ToastNotification(self, "Actualizado", "Comando editado correctamente.", "Status_Green").show_toast()

    # --- NUEVO: HANDLERS IMPORT/EXPORT ---
    def _handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Comandos", "comandos_backup.csv", "CSV Files (*.csv)")
        if not path: return
        
        if self.service.export_csv(path):
            ToastNotification(self, "Exportado", "Comandos guardados en CSV.", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "Fallo al exportar archivo.", "Status_Red").show_toast()

    def _handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Comandos", "", "CSV Files (*.csv)")
        if not path: return
        
        if not ModalConfirm(self, "Importar", "Esto actualizará o creará nuevos comandos. ¿Continuar?").exec():
            return

        ok, fail = self.service.import_csv(path)
        self.load_table_data()
        
        if fail == 0:
            ToastNotification(self, "Importación Exitosa", f"Se importaron {ok} comandos.", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Importación con Errores", f"OK: {ok} | Errores: {fail}", "Status_Yellow").show_toast()

    # ==========================================
    # 4. HELPERS VISUALES
    # ==========================================
    def _create_variable_chips(self, target_input):
        container = QWidget()
        layout = QHBoxLayout(container)
        # layout.setContentsMargins(*LAYOUT["margins"])
        # layout.setSpacing(LAYOUT["spacing"])
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        variables = [("{user}", "Usuario"), 
                     ("{target}", "Objetivo"), 
                     ("{points}", "Puntos"), 
                     ("{coin}", "Cara/Cruz"), 
                     ("{dice}", "Dado"), 
                     ("{song}", "Canción"), 
                     ("{random}", "Azar")]
        layout.addWidget(QLabel("Insertar:", styleSheet="color: #6c757d; font-size: 12px; font-weight: bold; border: none;"))
        for var_text, desc in variables:
            btn = QPushButton(var_text); btn.setToolTip(desc); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ background-color: {THEME_DARK['NeonGreen_Light']}; color: {THEME_DARK['Black_Pure']}; padding: 2px 8px; font-size: 12px; font-weight: bold; border-radius: 4px; border: none; }}")
            btn.clicked.connect(lambda _, t=var_text: self._insert_variable(target_input, t))
            layout.addWidget(btn)
        return container

    def _insert_variable(self, input_widget, text):
        input_widget.insert(text); input_widget.setFocus()

    def _create_action_btn(self, icon, color, func):
        w = QWidget(); w.setStyleSheet("background: transparent;"); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton(); btn.setIcon(get_icon(icon)); btn.setFixedSize(28, 28); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; }} QPushButton:hover {{ background-color: {color}; border: 1px solid {color}; border-radius: 4px; }}")
        btn.clicked.connect(func); l.addWidget(btn); return w

    def _create_top_btn(self, icon, text, func):
        """Botón de cabecera estilo Overlay/Puntos."""
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N3']};
                color: {THEME_DARK['White_N1']};
                
                padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['Black_N4']}; 
                border-color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(func)
        return btn