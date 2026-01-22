# backend/handlers/music_handler.py

from typing import Callable
from backend.utils.logger import Log

class MusicHandler:
    """
    Maneja los comandos de música, delegando a Spotify o YTMusic según config.
    """   
    def __init__(self, db_handler, spotify_worker, ytmusic_worker):
        self.db = db_handler
        self.spotify = spotify_worker      
        self.ytmusic = ytmusic_worker
        
        self.keys = {
            "song": "music_cmd_song",
            "skip": "music_cmd_skip",
            "pause": "music_cmd_pause",
            "req": "music_cmd_request"
        }

    def _get_active_worker(self):
        """Retorna el worker activo según la DB."""
        provider = self.db.get("music_provider", "spotify")
        if provider == "ytmusic":
            return self.ytmusic
        return self.spotify

    def get_current_song_info(self) -> str:
        worker = self._get_active_worker()
        # Verificamos si el worker tiene el método (Spotify y YTMusic deberían tenerlo)
        if hasattr(worker, 'get_current_track_text'):
            return worker.get_current_track_text() or "Nada sonando"
        return "Proveedor de música desconectado"

    def handle_command(self, user: str, original_content: str, msg_lower: str, 
                      send_msg: Callable[[str], None], 
                      log_msg: Callable[[str], None]) -> bool:
        
        worker = self._get_active_worker()
        
        # Validar si el servicio está activo (Spotify tiene .is_active, YTMusic ._is_active)
        is_service_active = False
        if hasattr(worker, 'is_active'): is_service_active = worker.is_active
        elif hasattr(worker, '_is_active'): is_service_active = worker._is_active
        
        if not is_service_active:
            # Opcional: Podrías retornar True y decir "Música desactivada"
            return False

        # Helpers config
        def is_cmd_active(k): return self.db.get(f"{self.keys[k]}_active") != "0"
        def get_trigger(k, default): return (self.db.get(self.keys[k]) or default).lower()

        cmd_song = get_trigger("song", "!song")
        cmd_req = get_trigger("req", "!sr")
        cmd_skip = get_trigger("skip", "!skip")
        cmd_pause = get_trigger("pause", "!pause")
        
        streamer_name = (self.db.get("kick_username") or "").lower()

        # --- LÓGICA DE COMANDOS ---

        # 1. !song
        if is_cmd_active("song") and msg_lower == cmd_song:
            info = self.get_current_song_info()
            send_msg(info)
            return True

        # 2. !sr (Request)
        elif is_cmd_active("req") and msg_lower.startswith(cmd_req):
            query = original_content[len(cmd_req):].strip()
            if query:
                # Polimorfismo: Ambos workers deben tener add_to_queue(query)
                added_song_name = worker.add_to_queue(query)
                
                if added_song_name:
                    send_msg(f"✅ Agregada: {added_song_name}")
                    log_msg(Log.success(f"🎵 Pedido {user}: {added_song_name}"))
                else:
                    send_msg(f"❌ No se pudo encontrar: {query}")
            else:
                send_msg(f"@{user} Uso: {cmd_req} <nombre>")
            return True

        # 3. Admin: Skip y Pause
        if user.lower() == streamer_name:
            if is_cmd_active("skip") and msg_lower == cmd_skip:
                if hasattr(worker, 'next_track'): worker.next_track() # Spotify
                elif hasattr(worker, 'skip'): worker.skip()           # YTMusic
                send_msg("⏭️ Saltando canción.")
                return True
            
            elif is_cmd_active("pause") and msg_lower == cmd_pause:
                worker.play_pause()
                send_msg("⏯️ Pausa/Play")
                return True

        return False