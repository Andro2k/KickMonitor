# services/chat_service.py

from typing import List, Dict, Any
import pyttsx3

class ChatService:
    """
    Servicio de Configuración del Chat y TTS (Text-to-Speech).
    Actúa como intermediario entre la UI y el motor de voz/base de datos.
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
        Crea una instancia efímera de pyttsx3 para no bloquear el hilo principal.
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
            del engine # Importante: liberar el recurso COM
        except Exception as e:
            print(f"[TTS Error] Al cargar voces: {e}")
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
        # Nota: pyttsx3 usa volumen 0.0 a 1.0, normalizamos aquí.
        self.tts.update_config(voice_id, rate, volume / 100.0)

    def save_tts_command(self, command: str):
        """Configura el comando disparador (ej: !voz)."""
        clean_cmd = command.strip().lower()
        if not clean_cmd: 
            clean_cmd = "!voz"
        self.db.set("tts_command", clean_cmd)

    def set_filter_enabled(self, enabled: bool):
        """
        True: Solo lee mensajes que empiecen con el comando (!voz).
        False: Lee todos los mensajes del chat.
        """
        self.db.set('filter_enabled', enabled)