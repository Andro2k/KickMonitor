# backend/handlers/triggers_handler.py

import time
from urllib.parse import quote
from typing import Callable, Dict

from backend.utils.logger_text import LoggerText

# ==========================================
# CONFIGURACIÓN
# ==========================================
OVERLAY_URL_TEMPLATE = "http://127.0.0.1:8081/media/{}"
CHAT_MAX_CHARS = 400  # Límite seguro para mensajes de Kick

class TriggerHandler:
    """
    Gestiona las alertas multimedia (Overlay) y la Tienda del Chat.
    """
    def __init__(self, db_handler, overlay_worker):
        self.db = db_handler
        self.overlay = overlay_worker
        self.cooldowns: Dict[str, float] = {}

    # =========================================================================
    # REGIÓN 1: PUNTO DE ENTRADA (DISPATCHER)
    # =========================================================================
    def handle_trigger(self, user: str, msg_lower: str, 
                      send_msg: Callable[[str], None], 
                      log_msg: Callable[[str], None]) -> bool:
        """
        Evalúa si el mensaje activa la tienda o una alerta multimedia.
        """       
        # 1. Comando Especial: !tienda
        if msg_lower == "!tienda":
            return self._handle_shop_command(user, send_msg)
        # 2. Buscar Trigger en Base de Datos
        trigger_data = self.db.get_trigger_file(msg_lower)
        if not trigger_data: 
            return False       
        # 3. Procesar Alerta Multimedia
        return self._process_media_trigger(user, msg_lower, trigger_data, send_msg, log_msg)

    # =========================================================================
    # REGIÓN 2: LÓGICA DE TIENDA (!TIENDA)
    # =========================================================================
    def _handle_shop_command(self, user: str, send_msg: Callable[[str], None]) -> bool:
        """Obtiene ítems activos, los pagina y los envía al chat."""
        items = self.db.get_active_shop_items()
        
        if not items:
            send_msg(f"@{user} 🛒 La tienda de alertas está vacía.")
            return True       
        # Formatear lista: "!susto (500)"
        shop_list = [f"{row[0]} ({row[1]})" for row in items]       
        # Paginación (Chunks) para respetar límites de Kick
        current_msg = "🛒 Alertas: "
        messages_to_send = []
        
        for item_str in shop_list:
            # +3 por el separador " | "
            if len(current_msg) + len(item_str) + 3 > CHAT_MAX_CHARS:
                messages_to_send.append(current_msg)
                current_msg = "🛒 ... " + item_str
            else:
                if current_msg == "🛒 Alertas: ":
                    current_msg += item_str
                else:
                    current_msg += " | " + item_str
        
        # Agregar el último bloque remanente
        if current_msg:
            messages_to_send.append(current_msg)       
        # Enviar bloques secuencialmente
        for msg in messages_to_send:
            send_msg(msg)           
        return True

    # =========================================================================
    # REGIÓN 3: PROCESAMIENTO DE ALERTAS (TRIGGER)
    # =========================================================================
    def _process_media_trigger(self, user: str, command: str, data: tuple, 
                               send_msg: Callable[[str], None], 
                               log_msg: Callable[[str], None]) -> bool:
        
        # A) Desempaquetar datos ACTUALIZADO
        pos_x = 0
        pos_y = 0
        # Verificamos longitud para evitar errores si la DB no se actualizó bien aún
        if len(data) >= 9:
            # Desempaquetamos
            fn, ftype, cd, scale, active, cost, vol, raw_x, raw_y = data[:9]
            pos_x = int(raw_x) if raw_x is not None else 0
            pos_y = int(raw_y) if raw_y is not None else 0
        elif len(data) == 7:
            fn, ftype, cd, scale, active, cost, vol = data
        else:
            fn, ftype, cd, scale, active, cost = data[:6]
            vol = 100
            pos_x = 0 
            pos_y = 0
        if not active: 
            return False

        # B) Verificar Cooldown (Tiempo de espera)
        now = time.time()
        last_used = self.cooldowns.get(command, 0)       
        if cd > 0:
            time_passed = now - last_used
            if time_passed < cd:
                remaining = int(cd - time_passed) + 1
                send_msg(f"@{user} ⏳ {command} espera ({remaining}s).")
                return True 

        # C) Verificar Costo y Cobrar
        if cost > 0:
            if not self.db.spend_points(user, cost):
                current_points = self.db.get_points(user)
                send_msg(f"@{user} 💸 Te faltan puntos. Costo: {cost} (Tienes: {current_points}).")
                return True

        # D) Ejecutar Alerta en Overlay
        try:
            full_url = OVERLAY_URL_TEMPLATE.format(quote(fn))
            
            payload = {
                "url": full_url, 
                "type": ftype, 
                "duration": 0,
                "scale": scale, 
                "volume": vol, 
                "random": self.db.get_bool("random_pos"),
                "pos_x": pos_x,
                "pos_y": pos_y
            }           
            
            self.overlay.send_event("play_media", payload)          
            self.cooldowns[command] = time.time()
            log_msg(LoggerText.info(f"🎬 {user} canjeó {command} (-{cost} pts)"))
            return True

        except Exception as e:
            log_msg(LoggerText.error(f"Error lanzando alerta '{command}': {e}"))
            return False