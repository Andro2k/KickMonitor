# backend/services/points_service.py

from typing import List, Any, Tuple
from backend.utils.data_manager import DataManager 

class PointsService:
    def __init__(self, db_handler):
        self.db = db_handler

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
        headers = ["Username", "Points", "Last_Seen", "Is_Paused", "Is_Muted", "Role", "Color"]
        users = self.db.get_all_points()

        formatted_rows = []
        for u in users:
            role_val = u[5] if u[5] else "user"
            color_val = u[6] if u[6] else ""
            formatted_rows.append([
                u[0], u[1], str(u[2]), int(u[3]), int(u[4]), role_val, color_val
            ])
        return DataManager.export_csv(path, headers, formatted_rows)

    def import_points_csv(self, path: str) -> Tuple[bool, str, str]:
        """
        Importa puntos y configuración de usuarios en bloque.
        """
        required = ["username", "points"]
        rows, error_msg = DataManager.import_csv(path, required)
        
        if rows is None:
            return False, "Error de Archivo", error_msg

        batch_data = []
        errors = 0
        
        for row in rows:
            try:
                user = row.get("username")
                if not user: continue

                # Construimos el diccionario de datos para esta fila
                user_dict = {
                    "username": user,
                    "points": int(row.get("points", 0)),
                    "is_paused": int(row["is_paused"]) if "is_paused" in row else None,
                    "is_muted": int(row["is_muted"]) if "is_muted" in row else None,
                    "role": row.get("role"),
                    "color": row.get("color")
                }
                batch_data.append(user_dict)
            except ValueError:
                errors += 1
                continue

        # Enviamos toda la lista a SQLite en una sola transacción
        if batch_data:
            self.db.bulk_import_points(batch_data)

        return True, "Importación Finalizada", f"Se actualizaron {len(batch_data)} usuarios. (Errores: {errors})"