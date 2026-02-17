# backend/services/chat_service.py

from typing import List, Dict, Any
import pyttsx3
from backend.utils.logger_text import LoggerText

class ChatService:
    def __init__(self, db_handler, tts_worker):
        self.db = db_handler
        self.tts = tts_worker

    # =========================================================================
    # REGIÓN 1: SISTEMA Y DISCOVERY (VOCES HÍBRIDAS)
    # =========================================================================
    def get_available_voices(self) -> List[Dict[str, str]]:
        # 1. Añadimos las mejores voces IA de Edge-TTS (Premium)
        voices_list = [
            {"id": "es-MX-JorgeNeural", "name": "IA - Jorge (México)", "engine": "edge-tts"},
            {"id": "es-MX-DaliaNeural", "name": "IA - Dalia (México)", "engine": "edge-tts"},
            {"id": "es-ES-AlvaroNeural", "name": "IA - Álvaro (España)", "engine": "edge-tts"},
            {"id": "es-ES-ElviraNeural", "name": "IA - Elvira (España)", "engine": "edge-tts"},
            {"id": "es-CO-GonzaloNeural", "name": "IA - Gonzalo (Colombia)", "engine": "edge-tts"},
            {"id": "es-AR-TomasNeural", "name": "IA - Tomás (Argentina)", "engine": "edge-tts"}
        ]
        
        # 2. Escaneamos y añadimos las voces Locales Clásicas (Fallback)
        try:
            engine = pyttsx3.init()
            for v in engine.getProperty('voices'):
                voices_list.append({
                    "id": str(v.id), 
                    "name": f"Local - {str(v.name)}",
                    "engine": "pyttsx3"
                })
            del engine
        except Exception as e:
            print(f"[DEBUG_TTS] Error al cargar voces locales: {e}")
            
        return voices_list

    # =========================================================================
    # REGIÓN 2: LECTURA DE CONFIGURACIÓN
    # =========================================================================
    def get_tts_settings(self) -> Dict[str, Any]:
        return {
            "voice_id": self.db.get("voice_id"), # ID de Windows SAPI5
            "edge_voice": self.db.get("edge_voice", "es-MX-JorgeNeural"), # ID de IA
            "engine_type": self.db.get("tts_engine", "edge-tts"), # Qué motor usar
            "rate": self.db.get_int("voice_rate", 175),
            "volume": self.db.get_int("voice_vol", 100),
            "command": self.db.get("tts_command") or "!voz",
            "filter_enabled": self.db.get_bool('filter_enabled')
        }

    # =========================================================================
    # REGIÓN 3: PERSISTENCIA Y ACTUALIZACIÓN EN TIEMPO REAL
    # =========================================================================
    def save_tts_config(self, voice_data: dict, rate: int, volume: int):
        engine = voice_data["engine"]
        vid = voice_data["id"]

        # Guardamos el motor elegido
        self.db.set("tts_engine", engine)
        
        # Guardamos el ID en la variable correcta según su tipo
        if engine == "edge-tts":
            self.db.set("edge_voice", vid)
        else:
            self.db.set("voice_id", vid)

        self.db.set("voice_rate", rate)
        self.db.set("voice_vol", volume)
        
        # Recuperamos la contraparte para que el fallback del worker nunca falle
        local_id = vid if engine == "pyttsx3" else self.db.get("voice_id")
        edge_id = vid if engine == "edge-tts" else self.db.get("edge_voice", "es-MX-JorgeNeural")

        # Actualizamos el hilo de voz en vivo
        self.tts.update_config(local_id, rate, volume / 100.0, engine, edge_id)

    def save_tts_command(self, command: str):
        clean_cmd = command.strip().lower()
        self.db.set("tts_command", clean_cmd if clean_cmd else "!voz")

    def set_filter_enabled(self, enabled: bool):
        self.db.set('filter_enabled', enabled)

    # =========================================================================
    # REGIÓN 4: CONFIGURACIÓN DEL OVERLAY DEL CHAT (OBS)
    # =========================================================================
    def get_chat_overlay_settings(self) -> Dict[str, Any]:
        """Recupera la configuración visual y sincroniza los ignorados desde Puntos."""
        
        # 🔴 MAGIA 1: Buscamos a los usuarios silenciados directamente en la tabla de Puntos
        all_users = self.db.get_all_points()
        # u[0] es el nombre de usuario, u[4] es el estado is_muted
        muted_users = [u[0] for u in all_users if u[4] == 1] 
        ignored_str = ",".join(muted_users)

        return {
            "font_size": self.db.get_int("chat_font_size", 16),
            "bg_opacity": self.db.get_int("chat_bg_opacity", 50),
            "bg_color": self.db.get("chat_bg_color", "#000000"),
            "text_color": self.db.get("chat_text_color", "#ffffff"),
            "border_radius": self.db.get_int("chat_border_radius", 8),
            "spacing": self.db.get_int("chat_spacing", 8),
            "animation": self.db.get("chat_animation") or "fade",
            "theme": self.db.get("chat_theme") or "bubble",
            "hide_bots": self.db.get_bool("chat_hide_bots"),
            "hide_cmds": self.db.get_bool("chat_hide_cmds"),
            "show_time": self.db.get_bool("chat_show_time"),
            "hide_old": self.db.get_bool("chat_hide_old"),
            "hide_time": self.db.get_int("chat_hide_time", 10),
            "ignored_users": ignored_str # <--- Enviamos la lista unificada a la interfaz
        }

    def save_chat_overlay_settings(self, settings: Dict[str, Any]):
        """Guarda todas las variables visuales y sincroniza usuarios ignorados bidireccionalmente."""
        
        # 1. Guardamos TODA la configuración visual en la tabla general normalmente
        for key, value in settings.items():
            self.db.set(f"chat_{key}", value)

        # 🔴 MAGIA 2: Sincronizamos los nombres de la caja de texto con la tabla de Puntos
        ignored_str = settings.get("ignored_users", "")
        
        current_users = self.db.get_all_points()
        currently_muted = {u[0].lower() for u in current_users if u[4] == 1}
        new_muted = {u.strip().lower() for u in ignored_str.split(",") if u.strip()}

        # A) Des-silenciar en la tabla de puntos a los que borraste de la caja de texto
        for u in currently_muted - new_muted:
            self.db.set_user_muted(u, False)

        # B) Silenciar (y crear si no existen) a los nuevos que escribiste en la caja de texto
        for u in new_muted - currently_muted:
            self.db.set_user_muted(u, True)