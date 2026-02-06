# backend/services/rewards_service.py

import json
import os
import random
import cloudscraper
from backend.utils.paths import get_config_path
from backend.core.db_controller import DBHandler

# CONSTANTES
URL_REWARDS = "https://api.kick.com/public/v1/channels/rewards"
URL_TOKEN = "https://id.kick.com/oauth/token"

class RewardsService:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.db = DBHandler() # Instanciamos DB para leer credenciales

    def _get_random_color(self):
        """Genera un color hexadecimal aleatorio."""
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def _get_session_data(self):
        """Lee el archivo session.json completo."""
        try:
            path = os.path.join(get_config_path(), "session.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except: pass
        return {}

    def _save_session_data(self, data):
        """Guarda los nuevos tokens en session.json."""
        try:
            path = os.path.join(get_config_path(), "session.json")
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] No se pudo guardar sesión: {e}")

    def _refresh_token(self) -> bool:
        """
        Intenta renovar el token usando el refresh_token almacenado.
        """
        print("[SISTEMA] Token expirado (401). Intentando renovar...")
        
        # 1. Obtener credenciales necesarias
        session = self._get_session_data()
        refresh_token = session.get("refresh_token")
        client_id = self.db.get("client_id")
        client_secret = self.db.get("client_secret")

        if not all([refresh_token, client_id, client_secret]):
            print("[ERROR] Faltan credenciales (Client ID/Secret) o Refresh Token para renovar.")
            return False

        # 2. Hacer petición a Kick OAuth
        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            resp = self.scraper.post(URL_TOKEN, data=payload, headers=headers)
            
            if resp.status_code == 200:
                new_data = resp.json()
                
                # A veces Kick no devuelve un nuevo refresh_token, así que mantenemos el viejo
                if "refresh_token" not in new_data:
                    new_data["refresh_token"] = refresh_token
                
                # Guardamos en disco para que el Bot y otros servicios lo vean
                self._save_session_data(new_data)
                print("[SISTEMA] Token renovado con éxito.")
                return True
            else:
                print(f"[ERROR RENOVACIÓN] Status: {resp.status_code} | Resp: {resp.text}")
                return False
        except Exception as e:
            print(f"[EXCEPCIÓN RENOVACIÓN] {e}")
            return False

    def _make_request(self, method, url, json_data=None, retry=True):
        """
        Wrapper inteligente que maneja autenticación y reintentos.
        """
        # 1. Obtener token actual
        session = self._get_session_data()
        token = session.get("access_token")
        
        if not token:
            print("[ERROR] No hay token de acceso disponible.")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            # 2. Ejecutar petición
            if method == "GET":
                resp = self.scraper.get(url, headers=headers)
            elif method == "POST":
                resp = self.scraper.post(url, headers=headers, json=json_data)
            elif method == "PATCH":
                resp = self.scraper.patch(url, headers=headers, json=json_data)
            elif method == "DELETE":
                resp = self.scraper.delete(url, headers=headers)
            else:
                return None

            # 3. Manejo de Token Expirado (401)
            if resp.status_code == 401 and retry:
                # Intentamos renovar
                if self._refresh_token():
                    # REINTENTO RECURSIVO (Solo una vez)
                    return self._make_request(method, url, json_data, retry=False)
                else:
                    print("[FATAL] No se pudo renovar el token. Necesitas volver a loguearte.")

            return resp

        except Exception as e:
            print(f"[EXCEPCIÓN REQUEST] {e}")
            return None

    # =========================================================================
    # MÉTODOS PÚBLICOS (Ahora usan _make_request)
    # =========================================================================

    def list_rewards(self) -> list:
        resp = self._make_request("GET", URL_REWARDS)
        if resp and resp.status_code == 200:
            return resp.json().get("data", [])
        return []

    def create_reward(self, title: str, cost: int, color: str = None, description: str = None, is_active: bool = True) -> bool:
        # Payload completo obligatorio para Kick
        payload = {
            "title": title, 
            "cost": cost, 
            "description": description or "Trigger KickMonitor", 
            "is_enabled": is_active,      # True = Visible, False = Oculto
            "is_paused": False,           # Siempre False para que no salga "Pausado" sino que se oculte
            "is_user_input_required": False,
            "should_redemptions_skip_request_queue": False,
            "background_color": color or self._get_random_color()
        }
        
        resp = self._make_request("POST", URL_REWARDS, json_data=payload)
        
        if resp:
            if resp.status_code in [200, 201]:
                return True
            else:
                print(f"[ERROR KICK CREAR] Código: {resp.status_code}")
                print(f"[DETALLE]: {resp.text}") 
        return False

    def edit_reward(self, reward_id: str, title: str, cost: int, color: str = None, description: str = None, is_active: bool = True) -> bool:
        url = f"{URL_REWARDS}/{reward_id}"
        
        # Payload completo obligatorio para editar
        payload = {
            "title": title,
            "cost": cost,
            "description": description or "Trigger KickMonitor",
            "is_enabled": is_active,       # Aquí mandamos el estado del botón
            "is_paused": False,
            "is_user_input_required": False,
            "should_redemptions_skip_request_queue": False,
            "background_color": color or "#53fc18"
        }
        
        resp = self._make_request("PATCH", url, json_data=payload)
        
        if resp:
            if resp.status_code in [200, 204]:
                return True
            else:
                print(f"[ERROR KICK EDITAR] Código: {resp.status_code}")
                print(f"[DETALLE]: {resp.text}")
        return False

    def delete_reward_by_title(self, title: str):
        # Primero necesitamos listar para encontrar el ID
        rewards = self.list_rewards()
        for r in rewards:
            if r.get("title", "").strip().lower() == title.strip().lower():
                url = f"{URL_REWARDS}/{r['id']}"
                self._make_request("DELETE", url)
                break