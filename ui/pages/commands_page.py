# ui/pages/commands_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QFrame,QFileDialog, QDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.utils import get_icon
from ui.components.modals import ModalConfirm
from ui.components.toast import ToastNotification
from backend.services.commands_service import CommandsService

# Modal importado
from ui.dialogs.command_modal import ModalEditCommand 

class CommandsPage(QWidget):
    def __init__(self, db_handler, parent=None):
        super().__init__(parent)
        self.service = CommandsService(db_handler)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # Layout Principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        # Contenedor Interno
        content = QWidget()
        l_content = QVBoxLayout(content)
        l_content.setContentsMargins(*LAYOUT["margins"])
        l_content.setSpacing(LAYOUT["spacing"])
        
        # 1. HEADER (Título y Botón Agregar)
        header = QHBoxLayout()
        
        lbl_title = QLabel("Comandos Personalizados")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header.addWidget(lbl_title)
        
        header.addStretch()
        
        btn_import = self._create_top_btn("upload.svg", "Importar", lambda: self._handle_import())
        btn_export = self._create_top_btn("download.svg", "Exportar", lambda: self._handle_export())

        header.addWidget(btn_import)
        header.addWidget(btn_export)
        
        # Botón Nuevo (Mantenemos el verde o destacado)
        btn_add = self._create_top_btn("plus.svg", "Nuevo Comando", lambda: self._open_add_modal())
        header.addWidget(btn_add)
        
        l_content.addLayout(header)

        # 2. TABLA
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Comando", "Respuesta", "CD (s)", "Acciones"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(STYLES["table_clean"])
        
        # Configurar Columnas
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Trigger
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Response
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Cooldown
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)            # Acciones
        self.table.setColumnWidth(3, 90)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.resizeRowsToContents()

        l_content.addWidget(self.table)
        
        main_layout.addWidget(content)

    def load_data(self):
        """Recarga la tabla desde el servicio."""
        rows = self.service.get_all_commands()
        self.table.setRowCount(0)
        
        for r in rows:
            # r = (trigger, response, is_active, cooldown)
            trigger, response, is_active, cooldown = r
            
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            
            # 1. Trigger
            item_trig = QTableWidgetItem(trigger)
            item_trig.setForeground(Qt.GlobalColor.white if is_active else Qt.GlobalColor.gray)
            
            # 2. Response (recortado si es muy largo)
            short_resp = (response[:150] + '...') if len(response) > 150 else response
            item_resp = QTableWidgetItem(short_resp)
            item_resp.setToolTip(response) # Tooltip con texto completo
            
            # 3. Cooldown
            item_cd = QTableWidgetItem(str(cooldown))
            item_cd.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 4. Acciones (Botones)
            container = QFrame()
            container.setStyleSheet("background-color: transparent;")
            l_actions = QHBoxLayout(container)
            l_actions.setContentsMargins(0, 0, 0, 0)
            l_actions.setSpacing(4)
            
            # Btn Editar
            # CORRECCIÓN AQUI: Agregamos 'checked' (o '_') como primer argumento
            btn_edit = self._create_action_btn("edit.svg", THEME_DARK['info'], 
                lambda _, t=trigger, r=response, c=cooldown: self._open_edit_modal(t, r, c))
            
            # Btn Eliminar
            # CORRECCIÓN AQUI: Lo mismo para eliminar
            btn_del = self._create_action_btn("trash.svg", THEME_DARK['Status_Red'], 
                lambda _, t=trigger: self._delete_command(t))

            l_actions.addWidget(btn_edit)
            l_actions.addWidget(btn_del)
            l_actions.addStretch()
            
            self.table.setItem(row_idx, 0, item_trig)
            self.table.setItem(row_idx, 1, item_resp)
            self.table.setItem(row_idx, 2, item_cd)
            self.table.setCellWidget(row_idx, 3, container)

    # --- HANDLERS ---
    def _open_add_modal(self):
        self._open_edit_modal("", "", 5)

    def _open_edit_modal(self, trigger, response, cooldown):
        # Instanciamos el Modal importado
        modal = ModalEditCommand(self, trigger, response, cooldown)
        
        if modal.exec() == QDialog.DialogCode.Accepted:
            # Recuperamos los datos del modal
            new_trig = modal.trigger_result
            new_resp = modal.response_result
            new_cd = modal.cooldown_result
            
            # Guardamos vía servicio
            if self.service.add_or_update_command(new_trig, new_resp, new_cd):
                self.load_data()
                ToastNotification(self, "Comandos", "Guardado correctamente", "Status_Green").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo guardar", "Status_Red").show_toast()

    def _delete_command(self, trigger):
        if ModalConfirm(self, "Eliminar Comando", f"¿Borrar {trigger}?").exec():
            if self.service.delete_command(trigger):
                self.load_data()
                ToastNotification(self, "Comandos", "Eliminado", "info").show_toast()

    # --- HELPERS UI ---
    def _create_top_btn(self, icon, text, func):
        btn = QPushButton("  " + text)
        btn.setIcon(get_icon(icon))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['Black_N2']}; color: {THEME_DARK['White_N1']};
                padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {THEME_DARK['Black_N4']}; 
                border-color: {THEME_DARK['NeonGreen_Main']}; 
            }}
        """)
        btn.clicked.connect(func)
        return btn

    def _create_action_btn(self, icon, color, func):
        btn = QPushButton()
        btn.setIcon(get_icon(icon))
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; }} 
            QPushButton:hover {{ background-color: {color}22; border: 1px solid {color}; }}
        """)
        btn.clicked.connect(func)
        return btn
    
    # --- IMPORTAR / EXPORTAR ---
    def _handle_export(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Comandos", "comandos.csv", "CSV Files (*.csv)")
        if not file_path: return
        
        if self.service.export_csv(file_path):
            ToastNotification(self, "Exportar", "Archivo guardado con éxito", "Status_Green").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo exportar el archivo", "Status_Red").show_toast()

    def _handle_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importar Comandos", "", "CSV Files (*.csv)")
        if not file_path: return
        
        if not ModalConfirm(self, "Importar CSV", "¿Deseas importar? Esto podría sobrescribir comandos existentes.").exec():
            return
            
        # Delegamos al servicio. Si el archivo es incorrecto, retorna 0,0
        ok, fail = self.service.import_csv(file_path)
        
        self.load_data() 
        
        # Validación de cabeceras
        if ok == 0 and fail == 0:
            # Si ambos son 0, significa que DataManager rechazó el archivo por cabeceras incorrectas
            ToastNotification(self, "Archivo Incorrecto", "El CSV no tiene las columnas 'Trigger' y 'Response'.", "Status_Red").show_toast()
        else:
            msg_type = "Status_Green" if fail == 0 else "Status_Yellow"
            ToastNotification(self, "Importación", f"Importados: {ok} | Fallidos: {fail}", msg_type).show_toast()