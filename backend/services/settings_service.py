# backend/services/settings_service.py

from datetime import datetime
import os
import shutil
from typing import Dict, Any

from backend.utils.paths import get_config_path

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

    # ==========================================
    # LÓGICA DE RESPALDO Y RESTAURACIÓN
    # ==========================================
    
    def create_backup(self, target_folder):
        """Crea una copia de la DB actual en la carpeta seleccionada."""
        source = os.path.join(get_config_path(), "kick_data.db")
        
        if not os.path.exists(source):
            raise FileNotFoundError("No se encontró la base de datos original.")

        # --- 2. CORRECCIÓN AQUÍ ---
        # Usamos datetime.now() que es inequívoco, en lugar de time.strftime
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        filename = f"backup_kickmonitor_{date_str}.db"
        destination = os.path.join(target_folder, filename)

        shutil.copy2(source, destination)
        return destination

    def restore_backup(self, backup_file_path):
        """Sobrescribe la DB actual con el archivo seleccionado."""
        
        # 1. Ruta destino (La DB activa en /config)
        dest_path = os.path.join(get_config_path(), "kick_data.db")
        
        # 2. Validaciones básicas
        if not os.path.exists(backup_file_path):
            raise FileNotFoundError("El archivo de respaldo seleccionado no existe.")

        # 3. Intentar el reemplazo
        try:
            
            shutil.copy2(backup_file_path, dest_path)
            
        except PermissionError:
            raise Exception("La base de datos está en uso. Cierra completamente la app y reemplaza el archivo manualmente en la carpeta /config.")
        except Exception as e:
            raise Exception(f"Error al restaurar: {str(e)}")