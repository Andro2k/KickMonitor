# services/points_service.py

from typing import List, Any

class PointsService:
    """
    Servicio de Gestión de Usuarios y Puntos.
    Maneja la lógica para la tabla de clasificación y operaciones manuales.
    """
    
    def __init__(self, db_handler):
        self.db = db_handler

    # =========================================================================
    # REGIÓN 1: LECTURA DE DATOS
    # =========================================================================
    def get_users_data(self) -> List[Any]:
        """
        Recupera la lista completa de usuarios con sus estados.
        Retorna filas: (username, points, last_seen, is_paused, is_muted, role)
        """
        return self.db.get_all_points()

    # =========================================================================
    # REGIÓN 2: GESTIÓN DE ESTADO (PAUSA / MUTE / BAN)
    # =========================================================================
    def toggle_pause(self, username: str, is_paused: bool) -> bool:
        """
        Pausa la acumulación de puntos (ej: para bots o cuentas secundarias).
        """
        return self.db.set_user_paused(username, is_paused)

    def toggle_mute(self, username: str, is_muted: bool) -> bool:
        """
        Silencia al usuario para que el bot ignore sus comandos.
        """
        return self.db.set_user_muted(username, is_muted)

    def delete_user(self, username: str) -> bool:
        """
        Elimina permanentemente el registro de puntos de un usuario.
        """
        return self.db.delete_user_points(username)

    # =========================================================================
    # REGIÓN 3: OPERACIONES MANUALES
    # =========================================================================
    def add_manual_points(self, username: str, amount: int):
        """
        Permite sumar (o restar si es negativo) puntos manualmente desde la UI.
        """
        self.db.add_points(username, amount)