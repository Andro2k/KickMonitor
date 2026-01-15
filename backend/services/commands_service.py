# services/commands_service.py

import time
from typing import List, Tuple, Dict, Optional
from backend.utils.data_manager import DataManager

class CommandsService:
    """
    Servicio de gestión de Comandos Personalizados.
    """   
    def __init__(self, db_handler):
        self.db = db_handler
        self._cooldown_tracker: Dict[str, float] = {}

    # =========================================================================
    # REGIÓN 1: GESTIÓN DE DATOS (CRUD)
    # =========================================================================
    def get_all_commands(self) -> List[Tuple]:
        """Obtiene la lista completa de comandos para la UI."""
        return self.db.get_all_commands()

    def add_or_update_command(self, trigger: str, response: str, cooldown: int = 5) -> bool:
        """Crea o actualiza un comando asegurando el formato correcto."""
        clean_trig = trigger.strip().lower()
        if not clean_trig.startswith("!"):
            clean_trig = "!" + clean_trig          
        return self.db.add_command(clean_trig, response, cooldown)

    def delete_command(self, trigger: str) -> bool:
        """Elimina un comando de la base de datos."""
        return self.db.delete_command(trigger)

    def toggle_status(self, trigger: str, is_active: bool) -> bool:
        """Activa o desactiva un comando sin borrarlo."""
        return self.db.toggle_command_active(trigger, is_active)

    # =========================================================================
    # REGIÓN 2: PERSISTENCIA (IMPORTAR / EXPORTAR CSV)
    # =========================================================================
    def export_csv(self, path: str) -> bool:
        headers = ["Trigger", "Response", "Is_Active", "Cooldown"]
        data_rows = self.db.get_all_commands() # Tu DB ya devuelve tuplas en orden
        return DataManager.export_csv(path, headers, data_rows)

    def import_csv(self, path: str) -> Tuple[int, int]:
        required = ["trigger", "response"]
        rows, error = DataManager.import_csv(path, required)
        
        if rows is None:
            print(f"[DEBUG_COMMANDS] Error en Import: {error}")
            return 0, 0

        count_ok = 0
        count_fail = 0

        for row in rows:
            try:
                trig = row["trigger"]
                resp = row["response"]
                # Parseo seguro
                act = int(row.get("is_active", 1))
                cd = int(row.get("cooldown", 5))

                self.add_or_update_command(trig, resp, cd)
                if act == 0:
                    self.toggle_status(trig, False)
                count_ok += 1
            except:
                count_fail += 1
        
        return count_ok, count_fail

    # =========================================================================
    # REGIÓN 3: LÓGICA DE EJECUCIÓN (RUNTIME)
    # =========================================================================
    def can_execute(self, trigger: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica reglas de negocio para ejecutar un comando
        """
        now = time.time()
        
        # 1. Obtener configuración
        data = self.db.get_command_details(trigger)
        if not data: 
            return False, None      
        response_text, is_active, cooldown_secs = data       
        if not is_active:
            return False, None

        # 2. Verificar Cooldown
        last_used = self._cooldown_tracker.get(trigger, 0.0)
        time_passed = now - last_used
        if time_passed >= cooldown_secs:
            self._cooldown_tracker[trigger] = now
            return True, response_text
        else:
            remaining = int(cooldown_secs - time_passed) + 1
            return False, f"⏳ El comando {trigger} estará listo en {remaining}s."