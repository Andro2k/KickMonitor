# backend/handlers/music_handler.py

from typing import Callable
from backend.utils.logger_text import Log

class MusicHandler:
    """
    Maneja los comandos de música (Spotify).
    """   
    def __init__(self, db_handler, spotify_worker):
        self.db = db_handler
        self.spotify = spotify_worker      
        self.keys = {
            "song": "music_cmd_song",
            "skip": "music_cmd_skip",
            "pause": "music_cmd_pause",
            "req": "music_cmd_request"
        }

    # =========================================================================
    # REGIÓN 1: UTILIDADES PÚBLICAS
    # =========================================================================
    def get_current_song_info(self) -> str:
        """Helper para obtener la canción actual (usado por ChatHandler)."""
        if self.spotify.is_active:
            return self.spotify.get_current_track_text() or "Ninguna canción"
        return "(Spotify desconectado)"

    # =========================================================================
    # REGIÓN 2: PROCESAMIENTO DE COMANDOS
    # =========================================================================
    def handle_command(self, user: str, original_content: str, msg_lower: str, 
                      send_msg: Callable[[str], None], 
                      log_msg: Callable[[str], None]) -> bool:
        """
        Evalúa si el mensaje es un comando musical y lo ejecuta.
        """
        # Si Spotify no está activo, abortamos inmediatamente
        if not self.spotify.is_active:
            return False
        # Helpers para lectura limpia de configuración
        def is_active(k): return self.db.get(f"{self.keys[k]}_active") != "0"
        def get_trigger(k, default): return (self.db.get(self.keys[k]) or default).lower()

        cmd_song = get_trigger("song", "!song")
        cmd_req = get_trigger("req", "!sr")
        cmd_skip = get_trigger("skip", "!skip")
        cmd_pause = get_trigger("pause", "!pause")
        
        streamer_name = (self.db.get("kick_username") or "").lower()

        # CASO A: Mostrar canción actual (!song)
        if is_active("song") and msg_lower == cmd_song:
            info = self.spotify.get_current_track_text()
            if info: 
                send_msg(info)
            return True
        # CASO B: Pedir canción (!sr <nombre>)
        elif is_active("req") and msg_lower.startswith(cmd_req):
            query = original_content[len(cmd_req):].strip()
            
            if query:
                added_song_name = self.spotify.add_to_queue(query)
                if added_song_name:
                    send_msg(f"✅ Agregada: {added_song_name}")
                    log_msg(Log.success(f"🎵 Pedido {user}: {added_song_name}"))
                else:
                    send_msg(f"❌ No encontré: {query}")
            else:
                send_msg(f"@{user} Uso: {cmd_req} <nombre de canción>")
            return True
        # CASO C: Comandos de Moderación (Solo Streamer)
        if user.lower() == streamer_name:
            if is_active("skip") and msg_lower == cmd_skip:
                self.spotify.next_track()
                send_msg("⏭️ Saltando canción.")
                log_msg(Log.info("Música: Skip por streamer"))
                return True
            
            elif is_active("pause") and msg_lower == cmd_pause:
                self.spotify.play_pause()
                send_msg("⏯️ Pausa/Play")
                return True

        return False