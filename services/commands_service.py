# services/commands_service.py

import time
import csv
from typing import List, Tuple, Dict, Optional

class CommandsService:
    """
    Servicio de gestión de Comandos Personalizados.
    Maneja el CRUD, persistencia (CSV) y la lógica de enfriamiento (Cooldowns).
    """   
    def __init__(self, db_handler):
        self.db = db_handler
        # Tracker volátil en memoria: {"!comando": timestamp_ultimo_uso}
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
        """Exporta la base de datos de comandos a un archivo CSV."""
        try:
            # Data: [(trigger, response, is_active, cooldown), ...]
            data = self.db.get_all_commands()
            
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["trigger", "response", "is_active", "cooldown"])
                
                for row in data:
                    writer.writerow([row[0], row[1], row[2], row[3]])
            return True
        except Exception as e:
            print(f"[Export Error] {e}")
            return False

    def import_csv(self, path: str) -> Tuple[int, int]:
        """
        Importa comandos desde un CSV externo.
        Retorna: (Cantidad Importados, Cantidad Fallidos)
        """
        count_ok = 0
        count_fail = 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, []) # Saltar cabecera
                
                if len(headers) < 2: 
                    return 0, 0

                for row in reader:
                    if len(row) < 2:
                        count_fail += 1
                        continue
                    
                    try:
                        trig = row[0]
                        resp = row[1]
                        # Índices flexibles por si el CSV es antiguo
                        active = int(row[2]) if len(row) > 2 and row[2].isdigit() else 1
                        cd = int(row[3]) if len(row) > 3 and row[3].isdigit() else 5                        
                        # 1. Guardar (Upsert)
                        self.add_or_update_command(trig, resp, cd)                      
                        # 2. Restaurar estado (add_or_update lo activa por defecto)
                        if active == 0:
                            self.toggle_status(trig, False)
                        
                        count_ok += 1
                    except:
                        count_fail += 1
            return count_ok, count_fail
        except Exception as e:
            print(f"[Import Error] {e}")
            return 0, 0

    # =========================================================================
    # REGIÓN 3: LÓGICA DE EJECUCIÓN (RUNTIME)
    # =========================================================================
    def can_execute(self, trigger: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica reglas de negocio para ejecutar un comando:
        1. Existencia en DB
        2. Estado Activo
        3. Tiempo de Cooldown
        Retorna: (PuedeEjecutar, MensajeDeRespuesta/Error)
        """
        now = time.time()
        
        # 1. Obtener configuración
        data = self.db.get_command_details(trigger)
        if not data: 
            return False, None # No existe           
        response_text, is_active, cooldown_secs = data       
        if not is_active:
            return False, None # Desactivado manualmente

        # 2. Verificar Cooldown
        last_used = self._cooldown_tracker.get(trigger, 0.0)
        time_passed = now - last_used
        if time_passed >= cooldown_secs:
            # ✅ OK: Actualizar timestamp y permitir ejecución
            self._cooldown_tracker[trigger] = now
            return True, response_text
        else:
            # ⛔ BLOQUEADO: Retornar mensaje de espera
            remaining = int(cooldown_secs - time_passed) + 1
            return False, f"⏳ El comando {trigger} estará listo en {remaining}s."