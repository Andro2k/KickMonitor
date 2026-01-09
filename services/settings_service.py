# services/settings_service.py

from typing import Dict, Any

class SettingsService:
    """
    Servicio para la Página de Ajustes Generales.
    Centraliza la configuración global y del sistema de economía (puntos).
    """
    
    def __init__(self, db_handler):
        self.db = db_handler

    # =========================================================================
    # REGIÓN 1: CONFIGURACIÓN GENÉRICA (KEY-VALUE)
    # =========================================================================
    def set_setting(self, key: str, value: Any):
        """Guarda un valor de configuración arbitrario."""
        self.db.set(key, value)

    def get_setting(self, key: str, default: Any = "") -> str:
        """Recupera un valor de configuración."""
        val = self.db.get(key)
        return val if val else default

    # =========================================================================
    # REGIÓN 2: CONFIGURACIÓN DE ECONOMÍA (PUNTOS)
    # =========================================================================
    def get_points_config(self) -> Dict[str, Any]:
        """Obtiene la configuración actual del sistema de puntos."""
        return {
            "command": self.db.get("points_command") or "!puntos",
            "per_msg": self.db.get_int("points_per_msg", 10),
            "per_min": self.db.get_int("points_per_min", 20)
        }