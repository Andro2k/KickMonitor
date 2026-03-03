# backend/services/rewards_service.py

import json
import os
import random
import time
import cloudscraper
from backend.utils.paths import get_config_path
from backend.core.db_controller import DBHandler

# CONSTANTES
URL_REWARDS = "https://api.kick.com/public/v1/channels/rewards"
URL_REDEMPTIONS = "https://api.kick.com/public/v1/channels/rewards/redemptions"
URL_TOKEN = "https://id.kick.com/oauth/token"

class RewardsService:
    def __init__(self, shared_scraper=None):
        self.scraper = shared_scraper if shared_scraper else cloudscraper.create_scraper()
        self.db = DBHandler()
        
        # [OPTIMIZACIÓN]: Caché en memoria para evitar leer el disco duro en cada petición.
        self._access_token = None
        self._refresh_token_val = None
        self._load_tokens_to_memory()

    def _get_random_color(self):
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def _load_tokens_to_memory(self):
        """Carga los tokens desde el disco a la RAM una sola vez al arrancar."""
        try:
            path = os.path.join(get_config_path(), "session.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    self._access_token = data.get("access_token")
                    self._refresh_token_val = data.get("refresh_token")
        except: pass

    def _save_session_data(self, data):
        """Guarda en disco y actualiza la RAM automáticamente."""
        try:
            path = os.path.join(get_config_path(), "session.json")
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
                
            self._access_token = data.get("access_token")
            self._refresh_token_val = data.get("refresh_token")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar sesión: {e}")

    def _refresh_token(self) -> bool:
        print("[SISTEMA] Token expirado (401). Intentando renovar...")
        
        client_id = self.db.get("client_id")
        client_secret = self.db.get("client_secret")

        if not all([self._refresh_token_val, client_id, client_secret]):
            print("[ERROR] Faltan credenciales o Refresh Token para renovar.")
            return False

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": self._refresh_token_val
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            resp = self.scraper.post(URL_TOKEN, data=payload, headers=headers)
            if resp.status_code == 200:
                new_data = resp.json()
                if "refresh_token" not in new_data:
                    new_data["refresh_token"] = self._refresh_token_val
                
                self._save_session_data(new_data)
                print("[SISTEMA] Token renovado con éxito.")
                return True
            else:
                print(f"[ERROR RENOVACIÓN] Status: {resp.status_code}")
                return False
        except Exception as e:
            print(f"[EXCEPCIÓN RENOVACIÓN] {e}")
            return False

    def _make_request(self, method, url, json_data=None, retry=True):
        """Wrapper con token desde la memoria RAM (0 lag)."""
        if not self._access_token:
            return None

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
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

            if resp.status_code == 401 and retry:
                if self._refresh_token():
                    return self._make_request(method, url, json_data, retry=False)
                else:
                    print("[FATAL] Falló renovación. Requiere Login manual.")

            return resp

        except Exception as e:
            print(f"[EXCEPCIÓN REQUEST] {e}")
            return None

    # Las funciones de abajo (list_rewards, create_reward, etc.) quedan exactamente igual
    def list_rewards(self) -> list:
        resp = self._make_request("GET", URL_REWARDS)
        if resp and resp.status_code == 200:
            return resp.json().get("data", [])
        return []

    def create_reward(self, title: str, cost: int, color: str = None, description: str = None, is_active: bool = True) -> bool:
        payload = {
            "title": title, "cost": cost, "description": description or "Trigger KickMonitor", 
            "is_enabled": is_active, "is_paused": False, "is_user_input_required": False,
            "should_redemptions_skip_request_queue": False, "background_color": color or self._get_random_color()
        }
        resp = self._make_request("POST", URL_REWARDS, json_data=payload)
        return resp and resp.status_code in [200, 201]

    def edit_reward(self, reward_id: str, title: str, cost: int, color: str = None, description: str = None, is_active: bool = True) -> bool:
        url = f"{URL_REWARDS}/{reward_id}"
        payload = {
            "title": title, "cost": cost, "description": description or "Trigger KickMonitor",
            "is_enabled": is_active, "is_paused": False, "is_user_input_required": False,
            "should_redemptions_skip_request_queue": False, "background_color": color or "#53fc18"
        }
        resp = self._make_request("PATCH", url, json_data=payload)
        return resp and resp.status_code in [200, 204]

    def delete_reward_by_title(self, title: str):
        rewards = self.list_rewards()
        target_id = next((r.get("id") for r in rewards if r.get("title", "").strip().lower() == title.strip().lower()), None)
        if target_id:
            self._make_request("DELETE", f"{URL_REWARDS}/{target_id}")

    def get_redemptions(self, status: str) -> list:
        url = f"{URL_REDEMPTIONS}?status={status}"
        resp = self._make_request("GET", url)
        if not resp: return []
        if resp.status_code == 200: return resp.json().get("data", [])
        elif resp.status_code == 429: time.sleep(2)
        return []

    def accept_redemptions(self, red_ids: list):
        if not red_ids: return
        url = f"{URL_REDEMPTIONS}/accept"
        payload = {"ids": red_ids}
        self._make_request("POST", url, json_data=payload)