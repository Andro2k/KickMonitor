# services/settings_service.py

import datetime
import os
import shutil
from typing import Dict, Any

class SettingsService:
    """
    Servicio para la Página de Ajustes Generales.
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
    
    # =========================================================================
    # REGIÓN 3: MANTENIMIENTO DE DATOS (NUEVO)
    # =========================================================================
    def get_database_info(self) -> Dict[str, str]:
        """Devuelve información sobre el archivo DB."""
        path = self.db.get_db_path()
        return {
            "path": path,
            "folder": os.path.dirname(path),
            "filename": os.path.basename(path)
        }

    def create_backup(self, target_folder: str) -> str:
        """Crea una copia de la DB en la carpeta indicada."""
        db_path = self.db.get_db_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError("No se encuentra la base de datos.")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"KickBackup_{timestamp}.db"
        target_path = os.path.join(target_folder, backup_name)

        shutil.copy2(db_path, target_path)
        return target_path

    def reset_user_data(self):
        """Wrapper para el reset de usuario."""
        self.db.factory_reset_user()

    def reset_economy(self):
        """Wrapper para el reset de economía."""
        self.db.wipe_economy_data()