# backend/services/points_service.py

from typing import List, Any, Tuple
from backend.utils.data_manager import DataManager # <--- Usamos tu nuevo gestor

class PointsService:
    def __init__(self, db_handler):
        self.db = db_handler

    # ... (Tus métodos de lectura y toggle siguen igual) ...
    def get_users_data(self) -> List[Any]:
        return self.db.get_all_points()

    def toggle_pause(self, username: str, is_paused: bool) -> bool:
        return self.db.set_user_paused(username, is_paused)

    def toggle_mute(self, username: str, is_muted: bool) -> bool:
        return self.db.set_user_muted(username, is_muted)

    def delete_user(self, username: str) -> bool:
        return self.db.delete_user_points(username)

    def add_manual_points(self, username: str, amount: int) -> int:
        """Suma puntos y devuelve el nuevo total."""
        return self.db.add_points(username, amount)

    # =========================================================================
    # NUEVA LÓGICA: IMPORTAR / EXPORTAR
    # =========================================================================
    def export_points_csv(self, path: str) -> bool:
        """Prepara los datos de la DB y los guarda usando DataManager."""
        headers = ["Username", "Points", "Last_Seen", "Is_Paused", "Is_Muted", "Role"]
        users = self.db.get_all_points()
        
        # Formateamos los datos crudos para que se vean bien en el CSV
        formatted_rows = []
        for u in users:
            # u = (user, pts, last_seen, paused, muted, role)
            role_val = u[5] if u[5] else "user"
            formatted_rows.append([
                u[0], 
                u[1], 
                str(u[2]), 
                int(u[3]), 
                int(u[4]), 
                role_val
            ])

        return DataManager.export_csv(path, headers, formatted_rows)

    def import_points_csv(self, path: str) -> Tuple[bool, str, str]:
        """
        Importa puntos calculando la diferencia para ajustar el total.
        Retorna: (Exito: bool, Título: str, Mensaje: str)
        """
        # 1. Definimos columnas OBLIGATORIAS
        required = ["username", "points"]
        
        # 2. DataManager valida el archivo
        rows, error_msg = DataManager.import_csv(path, required)
        
        if rows is None:
            return False, "Error de Archivo", error_msg

        count = 0
        errors = 0
        
        # 3. Procesamos la lógica de negocio
        for row in rows:
            try:
                user = row.get("username")
                if not user: continue

                # Calculamos diferencia para llegar al valor exacto del CSV
                target_points = int(row.get("points", 0))
                current_points = self.db.get_points(user)
                diff = target_points - current_points
                
                if diff != 0:
                    self.db.add_points(user, diff)

                # Actualizamos estados opcionales si vienen en el CSV
                if "is_paused" in row:
                    self.toggle_pause(user, int(row["is_paused"]) == 1)
                
                if "is_muted" in row:
                    self.toggle_mute(user, int(row["is_muted"]) == 1)
                
                if "role" in row:
                    self.db.update_user_role(user, row["role"])
                
                count += 1
            except ValueError:
                errors += 1
                continue

        return True, "Importación Finalizada", f"Se actualizaron {count} usuarios. (Errores: {errors})"