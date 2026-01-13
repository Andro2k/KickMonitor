# services/dashboard_service.py

from typing import Dict, Any, List, Tuple
try:
    from backend.config.credentials import KICK_CREDS, SPOTIFY_CREDS
except ImportError:
    KICK_CREDS, SPOTIFY_CREDS = {}, {}

class DashboardService:
    def __init__(self, db_handler):
        self.db = db_handler

    # --- PERFIL Y ESTADÍSTICAS ---
    def get_profile_data(self) -> Dict[str, Any]:
        target_user = self.db.get("kick_username")
        display_name = target_user or "Streamer"
        followers = 0
        pic_url = ""
        
        if target_user:
            user_data = self.db.get_kick_user(target_user)
            if user_data:
                display_name = user_data.get('username', display_name)
                followers = user_data.get('followers', 0)
                pic_url = user_data.get('profile_pic', "")
            
        return {
            "greeting": f"Hola, {display_name}",
            "stats": f"{followers:,} seguidores • Kick Monitor",
            "pic_url": pic_url
        }

    def get_kick_username(self) -> str:
        return self.db.get("kick_username")

    def set_kick_username(self, username: str):
        self.db.set("kick_username", username)

    # --- CONFIGURACIÓN DE CONEXIÓN ---
    def get_auto_connect_state(self) -> bool:
        return self.db.get_bool("auto_connect")

    def set_auto_connect_state(self, enabled: bool):
        self.db.set("auto_connect", enabled)

    def is_spotify_enabled(self) -> bool:
        return self.db.get_bool("spotify_enabled")

    def set_spotify_enabled(self, enabled: bool):
        self.db.set("spotify_enabled", "1" if enabled else "0")

    # --- GESTIÓN DE CREDENCIALES ---
    def has_credentials(self, service_type: str) -> bool:
        """Verifica si existen credenciales guardadas para el servicio."""
        key = "client_id" if service_type == "kick" else "spotify_client_id"
        return bool(self.db.get(key))

    def get_default_creds(self, service_type: str) -> Dict[str, str]:
        creds_map = {"kick": KICK_CREDS, "spotify": SPOTIFY_CREDS}
        target = creds_map.get(service_type, {})
        if target and all(v for v in target.values()):
            return target
        return {}

    def apply_creds(self, creds: Dict[str, str]):
        for key, value in creds.items():
            if value: self.db.set(key, value)

    # --- DATOS DE INTERFAZ (Listas Estáticas) ---
    def get_shortcuts_data(self) -> List[Tuple[str, str, int]]:
        """Retorna la lista de accesos directos: (Icono, Texto, IndexPagina)."""
        return [
            ("chat.svg", "Chat", 1), 
            ("terminal.svg", "Comandos", 2),
            ("bell.svg", "Alertas", 3), 
            ("layers.svg", "Overlay", 4), 
            ("users.svg", "Usuarios", 5), 
            ("casino.svg", "Casino", 6), 
            ("settings.svg", "Ajustes", 7)
        ]

    # --- COMANDOS DE MÚSICA ---
    def get_music_commands_list(self) -> List[Tuple[str, str, str]]:
        return [
            ("music_cmd_song", "!song", "Canción Actual"),
            ("music_cmd_request", "!sr", "Pedir Canción"),
            ("music_cmd_skip", "!skip", "Saltar (Admin)"),
            ("music_cmd_pause", "!pause", "Pausa (Admin)")
        ]
    
    def get_command_value(self, key: str, default: str) -> str:
        return self.db.get(key) or default

    def save_command(self, key: str, value: str):
        self.db.set(key, value)

    def get_command_active(self, key: str) -> bool:
        return self.db.get(f"{key}_active") != "0"

    def save_command_active(self, key: str, is_active: bool):
        self.db.set(f"{key}_active", "1" if is_active else "0")