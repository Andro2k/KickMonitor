# services/gambling_service.py

from typing import List, Any

class GamblingService:
    """
    Servicio de Lógica para el Casino.
    Maneja el historial, los límites de apuestas y los multiplicadores de los juegos.
    """
    
    def __init__(self, db_handler):
        self.db = db_handler

    # =========================================================================
    # REGIÓN 1: GESTIÓN DE HISTORIAL
    # =========================================================================
    def get_history_log(self, limit: int = 50) -> List[Any]:
        """Obtiene las últimas jugadas para la tabla de la UI."""
        return self.db.get_gamble_history(limit)
    
    def clear_all_history(self) -> bool:
        """Elimina todos los registros de apuestas de la base de datos."""
        return self.db.clear_gamble_history()

    # =========================================================================
    # REGIÓN 2: CONTROL MAESTRO (ON/OFF)
    # =========================================================================
    def get_status(self) -> bool:
        """Retorna True si el casino está habilitado para jugar."""
        return self.db.get_bool("gamble_enabled")

    def set_status(self, enabled: bool):
        """Habilita o deshabilita todos los juegos de casino."""
        self.db.set("gamble_enabled", enabled)

    # =========================================================================
    # REGIÓN 3: LÍMITES DE APUESTA (SAFEGUARDS)
    # =========================================================================
    def get_min_bet(self) -> int:
        return self.db.get_int("gamble_min", 10)

    def set_min_bet(self, value: int):
        # Aseguramos que el mínimo sea al menos 1
        self.db.set("gamble_min", max(1, value))

    def get_max_bet(self) -> int:
        return self.db.get_int("gamble_max", 1000)

    def set_max_bet(self, value: int):
        self.db.set("gamble_max", max(1, value))

    # =========================================================================
    # REGIÓN 4: CONFIGURACIÓN ESPECÍFICA POR JUEGO
    # =========================================================================
    def get_int_setting(self, key: str, default: int) -> int:
        """Helper para obtener enteros (ej: Probabilidad de ganar)."""
        return self.db.get_int(key, default)

    def get_float_setting(self, key: str, default: float) -> float:
        """Helper para obtener multiplicadores (ej: Pago 2.5x)."""
        val = self.db.get(key)
        try:
            return float(val) if val else default
        except ValueError:
            return default

    def set_setting(self, key: str, value: Any):
        """Guarda configuraciones, limpiando floats a 2 decimales."""
        if isinstance(value, float):
            value = round(value, 2)
        self.db.set(key, value)