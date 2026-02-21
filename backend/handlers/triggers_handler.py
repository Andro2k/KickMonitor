# backend/handlers/triggers_handler.py

import os
from urllib.parse import quote
from typing import Callable

# --- MÓDULOS INTERNOS ---
from backend.utils.logger_text import LoggerText
from backend.services.rewards_service import RewardsService

class TriggerHandler:
    """
    Maneja la lógica de negocio para las Alertas Multimedia (Triggers).
    """  
    def __init__(self, db_handler, overlay_worker):
        self.db = db_handler
        self.server = overlay_worker
        self.rewards_api = RewardsService() 

    def handle_redemption(self, user: str, reward_title: str, user_input: str, log_callback: Callable) -> bool:
        """
        Recibe un canje, busca el archivo asociado y lo reproduce.
        """
        # 1. Verificar si el Overlay está activado globalmente
        if not self.db.get_bool("overlay_enabled"):
            return False
            
        # 2. Búsqueda Inteligente (Nombre exacto vs Nombre con !)
        clean_title = reward_title.strip().lower()
        trigger_data = self.db.get_trigger_file(clean_title)
        if not trigger_data:
            trigger_data = self.db.get_trigger_file(f"!{clean_title}")

        if not trigger_data:
            return False
        try:
            filename = trigger_data[0]
            ftype = trigger_data[1] or "audio"
            duration = trigger_data[2] or 0
            scale = trigger_data[3] or 1.0
            is_active = bool(trigger_data[4])
            volume = trigger_data[6] if trigger_data[6] is not None else 100
            pos_x = trigger_data[7] if len(trigger_data) > 7 else 0
            pos_y = trigger_data[8] if len(trigger_data) > 8 else 0
            file_path = trigger_data[9] if len(trigger_data) > 9 else ""
            random_pos = bool(trigger_data[10]) if len(trigger_data) > 10 else False
        except IndexError:
            log_callback(LoggerText.error("Error DB: Índices de trigger incorrectos."))
            return False

        if not is_active:
            return False

        # 4. Validar Archivo (USANDO LA RUTA INDIVIDUAL, YA NO LA CARPETA GLOBAL)
        if not file_path or not os.path.exists(file_path):
            log_callback(LoggerText.error(f"Archivo 404 o no configurado correctamente: {filename}"))
            return False
        
        # 5. Construir URL y Payload
        file_url = f"http://127.0.0.1:8081/media/{quote(filename)}"

        payload = {
            "url": file_url,
            "type": ftype,
            "duration": duration * 1000, 
            "scale": scale,
            "volume": volume,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "random": random_pos,
            "user": user,          
            "reward_name": reward_title,
            "input_text": user_input
        }     

        # 6. Enviar al Overlay
        self.server.send_event("play_media", payload)
        
        return True

    # =========================================================================
    # GESTIÓN DESDE LA UI
    # =========================================================================
    def create_trigger(self, title: str, filename: str, ftype: str, cost: int, 
                       duration: int, scale: float, volume: int, 
                       pos_x: int, pos_y: int, create_in_kick: bool = True) -> bool:
        
        db_key = title.strip().lower()
        
        success_db = self.db.set_trigger(
            cmd=db_key,
            file=filename,
            ftype=ftype,
            dur=duration,
            sc=scale,
            act=1,
            cost=cost,
            vol=volume,
            pos_x=pos_x,
            pos_y=pos_y
        )

        if not success_db: return False

        # Crear en Kick
        if create_in_kick:
            self.rewards_api.create_reward(title, cost)
        
        return True

    def delete_trigger(self, title: str, delete_in_kick: bool = True) -> bool:
        db_key = title.strip().lower()
        self.db.conn_handler.execute_query("DELETE FROM triggers WHERE command=?", (db_key,))
        self.db.conn_handler.execute_query("DELETE FROM triggers WHERE command=?", (f"!{db_key}",))

        if delete_in_kick:
            self.rewards_api.delete_reward_by_title(title)
            
        return True