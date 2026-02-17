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
    # REGIÓN 3: MANTENIMIENTO Y PELIGRO
    # =========================================================================
    def reset_user_data(self):
        """Wrapper para el reset de usuario y eliminación de sesión OAuth."""
        # 1. Limpiamos la base de datos (Usuario, IDs, etc)
        self.db.factory_reset_user()

        # 2. 🔴 EL FIX: Eliminamos el archivo físico que mantiene abierta la sesión de Kick
        session_file = os.path.join(get_config_path(), "session.json")
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except Exception as e:
                print(f"No se pudo borrar el archivo de sesión: {e}")

    def reset_economy(self):
        """Wrapper para el reset de economía."""
        self.db.wipe_economy_data()

    # =========================================================================
    # REGIÓN 4: RESPALDO Y RESTAURACIÓN (EXPORT / IMPORT DB)
    # =========================================================================
    def create_backup(self, target_folder: str) -> str:
        """Crea una copia de la DB actual en la carpeta seleccionada."""
        # 1. Obtenemos la ruta real directa desde el controlador
        source = self.db.get_db_path()
        
        if not os.path.exists(source):
            raise FileNotFoundError("No se encontró la base de datos original.")

        # 2. Creamos el nombre del archivo con la fecha exacta
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"backup_kickmonitor_{date_str}.db"
        destination = os.path.join(target_folder, filename)

        # 3. Copiamos
        shutil.copy2(source, destination)
        return destination

    def restore_backup(self, backup_file_path: str):
        """Sobrescribe la DB actual con el archivo seleccionado."""
        dest_path = self.db.get_db_path()
        
        if not os.path.exists(backup_file_path):
            raise FileNotFoundError("El archivo de respaldo seleccionado no existe.")

        try:
            # 🔴 EL FIX CLAVE: Cerramos la conexión activa de SQLite para liberar el archivo.
            # Esto evita el PermissionError en Windows.
            if hasattr(self.db, 'conn_handler') and hasattr(self.db.conn_handler, 'conn'):
                self.db.conn_handler.conn.close()
            
            # Reemplazamos el archivo físico
            shutil.copy2(backup_file_path, dest_path)
            
        except Exception as e:
            raise Exception(f"Error al restaurar: {str(e)}")