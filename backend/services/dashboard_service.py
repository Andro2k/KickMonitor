# services/dashboard_service.py

from typing import Dict, Any, List, Tuple

# Intentar cargar credenciales locales (dev/pre-carga)
try:
    from backend.config.credentials import KICK_CREDS, SPOTIFY_CREDS
except ImportError:
    KICK_CREDS, SPOTIFY_CREDS = {}, {}

class DashboardService:
    """
    Servicio de Datos para el Dashboard.
    Maneja la lógica de presentación del perfil, configuración rápida y credenciales.
    """

    def __init__(self, db_handler):
        self.db = db_handler

    # =========================================================================
    # REGIÓN 1: DATOS DE PERFIL Y ESTADÍSTICAS
    # =========================================================================
    def get_profile_data(self) -> Dict[str, Any]:
        """Obtiene datos formateados para la tarjeta de perfil."""
        target_user = self.db.get("kick_username")
        
        display_name = target_user or "Streamer"
        followers = 0
        pic_url = ""
        
        # Recuperar datos cacheados si existen
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

    # =========================================================================
    # REGIÓN 2: CONFIGURACIÓN GENERAL (AUTO-CONNECT)
    # =========================================================================
    def get_auto_connect_state(self) -> bool:
        return self.db.get_bool("auto_connect")

    def set_auto_connect_state(self, enabled: bool):
        self.db.set("auto_connect", enabled)

    # =========================================================================
    # REGIÓN 3: CONFIGURACIÓN DE COMANDOS MUSICALES
    # =========================================================================
    def get_music_commands_list(self) -> List[Tuple[str, str, str]]:
        """Define la estructura de la grilla de comandos: (KeyDB, Default, Label)."""
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
        # Por defecto activo (si no existe o es "1")
        return self.db.get(f"{key}_active") != "0"

    def save_command_active(self, key: str, is_active: bool):
        self.db.set(f"{key}_active", "1" if is_active else "0")

    # =========================================================================
    # REGIÓN 4: GESTIÓN DE CREDENCIALES
    # =========================================================================
    def get_default_creds(self, service_type: str) -> Dict[str, str]:
        """Recupera credenciales hardcodeadas si existen (para desarrollo)."""
        creds_map = {
            "kick": KICK_CREDS,
            "spotify": SPOTIFY_CREDS
        }
        target = creds_map.get(service_type, {})
        
        if target and all(v for v in target.values()):
            return target
        return {}

    def apply_creds(self, creds: Dict[str, str]):
        """Persiste un set de credenciales en la base de datos."""
        for key, value in creds.items():
            if value: 
                self.db.set(key, value)