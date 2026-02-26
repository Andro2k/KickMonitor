# frontend/dialogs/command_modal.py

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSpinBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from frontend.components.core.factories import DynamicTagInput
from frontend.theme import THEME_DARK, STYLES
from frontend.components.core.modals import BaseModal
# =============================================================================
# MODAL DE EDICIÓN
# =============================================================================
class ModalEditCommand(BaseModal):
    def __init__(self, parent=None, trigger="", response="", cooldown=5, aliases="", cost=0):
        super().__init__(parent, width=500, height=640)
        self.original_trigger = trigger
        
        self.trigger_result = trigger
        self.response_result = response
        self.cooldown_result = cooldown
        self.aliases_result = aliases
        self.cost_result = cost
        
        self._setup_ui(trigger, response, cooldown, aliases, cost)

    def _setup_ui(self, trigger, response, cooldown, aliases, cost):
        layout = self.body_layout
        
        lbl_title = QLabel("Editar Comando" if trigger else "Nuevo Comando")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; border: none;")
        layout.addWidget(lbl_title)
        
        # --- FILA 1: COMANDO PRINCIPAL ---
        layout.addWidget(QLabel("Comando Principal (Ej: !redes):", styleSheet="color: #AAA; border: none;"))
        self.txt_trigger = QLineEdit(trigger)
        self.txt_trigger.setMaxLength(30)
        self.txt_trigger.setPlaceholderText("!comando")
        self.txt_trigger.setStyleSheet(STYLES["input"])
        layout.addWidget(self.txt_trigger)
        
        # --- FILA 2: ALIAS ---
        layout.addWidget(QLabel("Alias (Máx 5. Presiona Enter para agregar):", styleSheet="color: #AAA; border: none; margin-top: 5px;"))
        
        # Usando el nuevo componente unificado
        self.txt_aliases = DynamicTagInput(
            placeholder="Escribe un alias y presiona Enter...", 
            theme="green",  
            max_tags=5,     
            max_length=20,  # <--- AÑADIDO: Límite estricto de 20 caracteres por alias
            prefix="!"      
        )
        self.txt_aliases.input.setStyleSheet(STYLES["input"])
        self.txt_aliases.set_tags_from_string(aliases)
        layout.addWidget(self.txt_aliases)
        
        # --- FILA 3: RESPUESTA ---
        h_resp = QHBoxLayout()
        h_resp.addWidget(QLabel("Respuesta del Bot:", styleSheet="color: #AAA; border: none; margin-top: 5px;"))
        h_resp.addStretch()
        
        # Contador visual de caracteres
        self.lbl_char_count = QLabel("0/450", styleSheet="color: #666; font-size: 12px; border: none; margin-top: 5px;")
        h_resp.addWidget(self.lbl_char_count)
        layout.addLayout(h_resp)
        
        self.txt_response = QPlainTextEdit(response)
        self.txt_response.setPlaceholderText("Escribe aquí lo que dirá el bot.")
        self.txt_response.setStyleSheet(STYLES["textarea"])
        self.txt_response.textChanged.connect(self._on_response_changed)
        layout.addWidget(self.txt_response)
        self._on_response_changed() # Llamada inicial para setear el contador
        
        texto_variables = "Variables: {user}, {touser}, {input}, {points}, {target_points}, {followers}, {8ball}, {coin}, {dice}, {time}, {date}"
        lbl_vars = QLabel(texto_variables, styleSheet=f"color: {THEME_DARK['Gray_N2']}; font-size: 12px; border: none;")
        lbl_vars.setWordWrap(True)
        layout.addWidget(lbl_vars)

        # --- FILA 4: NUMÉRICAS ---
        row_numbers = QHBoxLayout()
        row_numbers.setSpacing(20)
        
        col_cd = QHBoxLayout()
        col_cd.addWidget(QLabel("Cooldown (seg):", styleSheet="color: #AAA; border: none;"))
        self.spin_cd = QSpinBox()
        self.spin_cd.setRange(0, 3600)
        self.spin_cd.setValue(cooldown)
        self.spin_cd.setStyleSheet(STYLES["spinbox_modern"])
        col_cd.addWidget(self.spin_cd)
        row_numbers.addLayout(col_cd)
        
        col_cost = QHBoxLayout()
        col_cost.addWidget(QLabel("Costo (Puntos):", styleSheet="color: #AAA; border: none;"))
        self.spin_cost = QSpinBox()
        self.spin_cost.setRange(0, 100000)
        self.spin_cost.setSingleStep(10)
        self.spin_cost.setValue(cost)
        self.spin_cost.setStyleSheet(STYLES["spinbox_modern"])
        col_cost.addWidget(self.spin_cost)
        row_numbers.addLayout(col_cost)
        
        row_numbers.addStretch()
        layout.addLayout(row_numbers)
        layout.addStretch()
        
        # --- BOTONES ---
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(STYLES["btn_outlined"])
        
        btn_save = QPushButton("Guardar")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_save.setStyleSheet(STYLES["btn_primary"])
        
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        layout.addLayout(h_btns)

    def _on_response_changed(self):
        """Bloquea dinámicamente la entrada si se superan los 450 caracteres y actualiza el contador."""
        text = self.txt_response.toPlainText()
        max_chars = 450
        
        if len(text) > max_chars:
            # Restaurar el cursor para que no salte al inicio al cortar el texto
            cursor = self.txt_response.textCursor()
            pos = cursor.position()
            self.txt_response.setPlainText(text[:max_chars])
            cursor.setPosition(min(pos, max_chars))
            self.txt_response.setTextCursor(cursor)
            text = text[:max_chars]
            
        color = "#ff4c4c" if len(text) >= max_chars else "#666"
        self.lbl_char_count.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; border: none; margin-top: 5px;")
        self.lbl_char_count.setText(f"{len(text)}/{max_chars}")

    def _save(self):
        # Extraemos limpiando y reemplazando espacios por guiones
        raw_trig = self.txt_trigger.text().strip().replace(" ", "-")
        
        if raw_trig and not raw_trig.startswith("!"):
            raw_trig = "!" + raw_trig
            
        self.trigger_result = raw_trig
        self.response_result = self.txt_response.toPlainText().strip()
        self.cooldown_result = self.spin_cd.value()
        self.aliases_result = self.txt_aliases.get_tags_string()
        self.cost_result = self.spin_cost.value()
        
        if self.trigger_result and self.response_result:
            self.accept()

    def keyPressEvent(self, event):
        """Intercepta las teclas presionadas para evitar que el Enter cierre el modal."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            return # Ignoramos el Enter
        super().keyPressEvent(event)