# frontend/pages/commands_page.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QFrame, QFileDialog, QDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from frontend.components.core.factories import create_icon_btn, create_nav_btn, create_page_header
from frontend.components.core.layouts import FlowLayout
from frontend.theme import LAYOUT, THEME_DARK, STYLES, get_switch_style
from frontend.notifications.modal_alert import ModalConfirm
from frontend.notifications.toast_alert import ToastNotification
from backend.services.commands_service import CommandsService

from frontend.dialogs.command_modal import ModalEditCommand 

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
        
        content = QWidget()
        l_content = QVBoxLayout(content)
        l_content.setContentsMargins(*LAYOUT["level_03"])
        l_content.setSpacing(LAYOUT["space_01"])
        
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

        # 2. TABLA REDISEÑADA
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["", "Comando", "Respuesta", "Alias", "Costo", "CD", "Acciones"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(STYLES["table_clean"])
        
        # Configurar Columnas
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)            # Activo (Switch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Comando
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Respuesta
        
        # EL CAMBIO 1: Interactivo permite ajustar y FlowLayout hará el resto
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)      # Alias
        
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)            # Costo
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)            # CD
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)            # Acciones
        
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(3, 200) # Un ancho inicial generoso para Alias
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 50)
        self.table.setColumnWidth(6, 90)
        
        # Aumentamos un poquito la altura para que entren 2 líneas de Alias cómodamente
        self.table.verticalHeader().setDefaultSectionSize(60) 

        l_content.addWidget(self.table)
        main_layout.addWidget(content)

    def load_data(self):
        """Recarga la tabla desde el servicio."""
        rows = self.service.get_all_commands()
        self.table.setRowCount(0)
        
        for r in rows:
            trigger, response, is_active, cooldown, aliases, cost = r
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            
            # --- 0. ACTIVO (Switch) ---
            chk_container = QWidget()
            chk_container.setStyleSheet("background-color: transparent;")
            l_chk = QHBoxLayout(chk_container)
            l_chk.setContentsMargins(0,0,0,0)
            l_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            chk = QCheckBox()
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setStyleSheet(get_switch_style())
            chk.setChecked(bool(is_active))
            chk.toggled.connect(lambda v, t=trigger: self._toggle_command(t, v))
            l_chk.addWidget(chk)
            
            # --- 1. COMANDO ---
            item_trig = QTableWidgetItem(trigger)
            item_trig.setFont(self._font_bold()) # Añadimos negrita visual
            if is_active:
                item_trig.setForeground(QColor("#53fc18"))
            else:
                item_trig.setForeground(Qt.GlobalColor.gray)
            
            # --- 2. RESPUESTA ---
            short_resp = (response[:80] + '...') if len(response) > 80 else response
            item_resp = QTableWidgetItem(short_resp)
            item_resp.setToolTip(response)
            if not is_active: item_resp.setForeground(Qt.GlobalColor.gray)
            
            # --- 3. ALIAS (Etiquetas con FlowLayout) ---
            alias_container = QWidget()
            alias_container.setStyleSheet("background-color: transparent;")
            
            # EL CAMBIO 2: Usar FlowLayout en lugar de caja recta
            l_alias = FlowLayout(alias_container, margin=2, spacing=5, expand_items=False)
            
            alias_list = [a.strip() for a in aliases.split(',') if a.strip()]
            
            if not alias_list:
                lbl = QLabel("Sin alias")
                lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                lbl.setStyleSheet("background-color: rgba(255, 60, 60, 0.15); color: #ff5c5c; padding: 4px 10px; border-radius: 10px; font-size: 12px; font-weight: bold;")
                l_alias.addWidget(lbl)
            else:
                for a in alias_list:
                    lbl = QLabel(a)
                    # EL CAMBIO 3: Evita estrictamente que la píldora se apachurre
                    lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                    
                    if is_active:
                        lbl.setStyleSheet("background-color: rgba(83, 252, 24, 0.15); color: #53fc18; padding: 4px 10px; border-radius: 10px; font-size: 12px; font-weight: bold;")
                    else:
                        lbl.setStyleSheet("background-color: rgba(150, 150, 150, 0.15); color: #888; padding: 4px 10px; border-radius: 10px; font-size: 12px; font-weight: bold;")
                    l_alias.addWidget(lbl)
            
            # --- 4. COSTO ---
            item_cost = QTableWidgetItem(str(cost))
            item_cost.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not is_active: item_cost.setForeground(Qt.GlobalColor.gray)

            # --- 5. COOLDOWN ---
            item_cd = QTableWidgetItem(str(cooldown))
            item_cd.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not is_active: item_cd.setForeground(Qt.GlobalColor.gray)
            
            # --- 6. ACCIONES ---
            container_actions = QFrame()
            container_actions.setStyleSheet("background-color: transparent;")
            l_actions = QHBoxLayout(container_actions)
            l_actions.setContentsMargins(0, 0, 0, 0)
            l_actions.setSpacing(4)
            l_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = create_icon_btn(
                "edit.svg", 
                lambda _, t=trigger, r=response, c=cooldown, al=aliases, co=cost: self._open_edit_modal(t, r, c, al, co),
                color_hover=THEME_DARK['status_info']
            )
            btn_del = create_icon_btn(
                "trash.svg",
                lambda _, t=trigger: self._delete_command(t),
                color_hover=THEME_DARK['status_error']
            )

            l_actions.addWidget(btn_edit)
            l_actions.addWidget(btn_del)
            
            # Ensamblar fila
            self.table.setCellWidget(row_idx, 0, chk_container)
            self.table.setItem(row_idx, 1, item_trig)
            self.table.setItem(row_idx, 2, item_resp)
            self.table.setCellWidget(row_idx, 3, alias_container)
            self.table.setItem(row_idx, 4, item_cost)
            self.table.setItem(row_idx, 5, item_cd)
            self.table.setCellWidget(row_idx, 6, container_actions)

    # --- HANDLERS ---
    def _font_bold(self):
        f = self.font(); f.setBold(True); return f

    def _toggle_command(self, trigger, is_active):
        if self.service.toggle_status(trigger, is_active):
            self.load_data()

    def _open_add_modal(self):
        self._open_edit_modal("", "", 5, "", 0)

    def _open_edit_modal(self, trigger, response, cooldown, aliases, cost):
        modal = ModalEditCommand(self, trigger, response, cooldown, aliases, cost)
        
        if modal.exec() == QDialog.DialogCode.Accepted:
            new_trig = modal.trigger_result
            new_resp = modal.response_result
            new_cd = modal.cooldown_result
            new_al = modal.aliases_result
            new_co = modal.cost_result
            original = modal.original_trigger 

            if original and original != new_trig:
                self.service.delete_command(original)
            
            if self.service.add_or_update_command(new_trig, new_resp, new_cd, new_al, new_co):
                self.load_data()
                ToastNotification(self, "Comandos", "Guardado correctamente", "status_success").show_toast()
            else:
                ToastNotification(self, "Error", "No se pudo guardar", "status_error").show_toast()

    def _delete_command(self, trigger):
        if ModalConfirm(self, "Eliminar Comando", f"¿Borrar {trigger}?").exec():
            if self.service.delete_command(trigger):
                self.load_data()
                ToastNotification(self, "Comandos", "Eliminado", "info").show_toast()
    
    # --- IMPORTAR / EXPORTAR ---
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