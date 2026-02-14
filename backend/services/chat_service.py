# backend/services/chat_service.py

from typing import List, Dict, Any
import pyttsx3

from backend.utils.logger_text import LoggerText

class ChatService:
    """
    Servicio de Configuración del Chat y TTS (Text-to-Speech).
    """
    
    def __init__(self, db_handler, tts_worker):
        self.db = db_handler
        self.tts = tts_worker

    # =========================================================================
    # REGIÓN 1: SISTEMA Y DISCOVERY (VOCES)
    # =========================================================================
    def get_available_voices(self) -> List[Dict[str, str]]:
        """
        Escanea las voces instaladas en el sistema operativo.
        """
        voices_list = []
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for v in voices:
                voices_list.append({
                    "id": str(v.id), 
                    "name": str(v.name)
                })
            del engine
        except Exception as e:
            print(f"[DEBUG_TTS] Error al cargar voces: {e}")
        return voices_list

    # =========================================================================
    # REGIÓN 2: LECTURA DE CONFIGURACIÓN
    # =========================================================================
    def get_tts_settings(self) -> Dict[str, Any]:
        """Recupera el estado actual del TTS desde la base de datos."""
        return {
            "voice_id": self.db.get("voice_id"),
            "rate": self.db.get_int("voice_rate", 175),
            "volume": self.db.get_int("voice_vol", 100),
            "command": self.db.get("tts_command") or "!voz",
            "filter_enabled": self.db.get_bool('filter_enabled')
        }

    # =========================================================================
    # REGIÓN 3: PERSISTENCIA Y ACTUALIZACIÓN EN TIEMPO REAL
    # =========================================================================
    def save_tts_config(self, voice_id: str, rate: int, volume: int):
        """
        Guarda en DB y actualiza el worker activo inmediatamente.
        """
        self.db.set("voice_id", voice_id)
        self.db.set("voice_rate", rate)
        self.db.set("voice_vol", volume)
        
        # Actualizar el hilo de voz sin reiniciar la app
        self.tts.update_config(voice_id, rate, volume / 100.0)

    def save_tts_command(self, command: str):
        """Configura el comando disparador (ej: !voz)."""
        clean_cmd = command.strip().lower()
        if not clean_cmd: 
            clean_cmd = "!voz"
        self.db.set("tts_command", clean_cmd)

    def set_filter_enabled(self, enabled: bool):
        self.db.set('filter_enabled', enabled)

    # =========================================================================
    # REGIÓN 4: CONFIGURACIÓN DEL OVERLAY DEL CHAT (OBS)
    # =========================================================================
    def get_chat_overlay_settings(self) -> Dict[str, Any]:
        """Recupera la configuración visual y de comportamiento para OBS."""
        return {
            "font_size": self.db.get_int("chat_font_size", 16),
            "bg_opacity": self.db.get_int("chat_bg_opacity", 50),
            "bg_color": self.db.get("chat_bg_color", "#000000"),
            "text_color": self.db.get("chat_text_color", "#ffffff"),
            "border_radius": self.db.get_int("chat_border_radius", 8),
            "spacing": self.db.get_int("chat_spacing", 8),
            
            # --- NUEVOS CAMPOS ---
            "animation": self.db.get("chat_animation") or "fade",
            "theme": self.db.get("chat_theme") or "bubble",
            "hide_bots": self.db.get_bool("chat_hide_bots"),
            "hide_cmds": self.db.get_bool("chat_hide_cmds"),
            "show_time": self.db.get_bool("chat_show_time"),
            "hide_old": self.db.get_bool("chat_hide_old"),
            "hide_time": self.db.get_int("chat_hide_time", 10),
            "ignored_users": self.db.get("chat_ignored_users") or ""
        }

    def save_chat_overlay_settings(self, settings: Dict[str, Any]):
        """Guarda todas las variables visuales y de comportamiento en la BD."""
        for key, value in settings.items():
            self.db.set(f"chat_{key}", value)