# ui/pages/commands_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QFrame,QFileDialog, QDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt
from ui.factories import create_icon_btn, create_nav_btn, create_page_header
from ui.theme import LAYOUT, THEME_DARK, STYLES
from ui.alerts.modal_alert import ModalConfirm
from ui.alerts.toast_alert import ToastNotification
from backend.services.commands_service import CommandsService

# Modal importado (Ya refactorizado con BaseModal)
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
        
        # 1. HEADER
        header = QHBoxLayout()
        header.addWidget(create_page_header("Comandos Personalizados", "Configuración y Gestión de comandos."))
        header.addStretch()
        
        btn_import = create_nav_btn("Importar", "upload.svg", self._handle_import)
        btn_export = create_nav_btn("Exportar", "download.svg", self._handle_export)
        btn_add = create_nav_btn("Nuevo Comando", "plus.svg", self._open_add_modal)

        header.addWidget(btn_import)
        header.addWidget(btn_export)
        header.addWidget(btn_add)
        
        l_content.addLayout(header)

        # 2. TABLA
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Comando", "Respuesta", "CD (s)", "Acciones"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
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
            
            # 2. Response
            short_resp = (response[:150] + '...') if len(response) > 150 else response
            item_resp = QTableWidgetItem(short_resp)
            item_resp.setToolTip(response)
            
            # 3. Cooldown
            item_cd = QTableWidgetItem(str(cooldown))
            item_cd.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 4. Acciones
            container = QFrame()
            container.setStyleSheet("background-color: transparent;")
            l_actions = QHBoxLayout(container)
            l_actions.setContentsMargins(0, 0, 0, 0)
            l_actions.setSpacing(4)
            l_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = create_icon_btn(
                "edit.svg", 
                lambda _, t=trigger, r=response, c=cooldown: self._open_edit_modal(t, r, c),
                color_hover=THEME_DARK['info']
            )
            btn_del = create_icon_btn(
                "trash.svg",
                lambda _, t=trigger: self._delete_command(t),
                color_hover=THEME_DARK['status_error']
            )

            l_actions.addWidget(btn_edit)
            l_actions.addWidget(btn_del)
            
            self.table.setItem(row_idx, 0, item_trig)
            self.table.setItem(row_idx, 1, item_resp)
            self.table.setItem(row_idx, 2, item_cd)
            self.table.setCellWidget(row_idx, 3, container)

    # --- HANDLERS ---
    def _open_add_modal(self):
        self._open_edit_modal("", "", 5)

    def _open_edit_modal(self, trigger, response, cooldown):
        # Instanciamos el Modal
        modal = ModalEditCommand(self, trigger, response, cooldown)
        
        if modal.exec() == QDialog.DialogCode.Accepted:
            # Recuperamos los datos NUEVOS y el ORIGINAL
            new_trig = modal.trigger_result
            new_resp = modal.response_result
            new_cd = modal.cooldown_result
            original = modal.original_trigger # Accedemos a la variable que añadimos al modal

            # LÓGICA DE RENOMBRADO:
            # Si había un nombre original y es diferente al nuevo, borramos el viejo.
            if original and original != new_trig:
                self.service.delete_command(original)
            
            # Guardamos el nuevo (o el actualizado)
            if self.service.add_or_update_command(new_trig, new_resp, new_cd):
                self.load_data()
                ToastNotification(self, "Comandos", "Guardado correctamente", "status_success").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo guardar", "status_error").show_toast()

    def _delete_command(self, trigger):
        if ModalConfirm(self, "Eliminar Comando", f"¿Borrar {trigger}?").exec():
            if self.service.delete_command(trigger):
                self.load_data()
                ToastNotification(self, "Comandos", "Eliminado", "info").show_toast()
    
    # --- IMPORTAR / EXPORTAR (Sin cambios) ---
    def _handle_export(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Comandos", "comandos.csv", "CSV Files (*.csv)")
        if not file_path: return
        
        if self.service.export_csv(file_path):
            ToastNotification(self, "Exportar", "Archivo guardado con éxito", "status_success").show_toast()
        else:
            ToastNotification(self, "Error", "No se pudo exportar el archivo", "status_error").show_toast()

    def _handle_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Importar Comandos", "", "CSV Files (*.csv)")
        if not file_path: return
        
        if not ModalConfirm(self, "Importar CSV", "¿Deseas importar? Esto podría sobrescribir comandos existentes.").exec():
            return
            
        ok, fail = self.service.import_csv(file_path)
        self.load_data() 
        
        if ok == 0 and fail == 0:
            ToastNotification(self, "Archivo Incorrecto", "El CSV no tiene las columnas requeridas.", "status_error").show_toast()
        else:
            msg_type = "status_success" if fail == 0 else "status_warning"
            ToastNotification(self, "Importación", f"Importados: {ok} | Fallidos: {fail}", msg_type).show_toast()