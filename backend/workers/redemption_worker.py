# backend/workers/redemption_worker.py

import time
import json
import cloudscraper
import os
from PyQt6.QtCore import QThread, pyqtSignal

from backend.utils.logger_text import LoggerText
from backend.utils.paths import get_config_path

URL_REDEMPTIONS = "https://api.kick.com/public/v1/channels/rewards/redemptions"

class RedemptionWorker(QThread):
    # Señal: (usuario, recompensa, mensaje)
    redemption_detected = pyqtSignal(str, str, str)
    log_signal = pyqtSignal(str)

    def __init__(self, db_handler):
        super().__init__()
        self.db = db_handler
        self.is_running = True
        self.scraper = cloudscraper.create_scraper()
        
        self.normal_interval = 1.5  
        self.burst_interval = 0.5   
        self.processed_ids = set() 
        self.first_scan = True 
        
        # Anti-Spam de logs de error
        self._last_error_time = 0

    def run(self):
        self.log_signal.emit(LoggerText.system("Monitor de Puntos: Iniciado"))
        
        while self.is_running:
            token = self._get_token()
            found_something = False

            if token:
                # Revisar PENDIENTES
                found_p = self._check_redemptions(token, status="pending")
                # Revisar COMPLETADOS
                found_f = self._check_redemptions(token, status="fulfilled")
                
                found_something = found_p or found_f
            else:
                # Solo loguear esto una vez cada 60 segundos para no spamear
                if time.time() - self._last_error_time > 60:
                    self.log_signal.emit(LoggerText.warning("Monitor Puntos: No se encontró token."))
                    self._last_error_time = time.time()

            if self.first_scan:
                self.first_scan = False

            sleep_time = self.burst_interval if found_something else self.normal_interval
            
            # Loop de espera fraccionado para poder detener el hilo rápido
            steps = int(sleep_time * 10)
            for _ in range(steps):
                if not self.is_running: break
                time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.wait()

    def _get_token(self):
        try:
            path = os.path.join(get_config_path(), "session.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f).get("access_token")
        except Exception as e:
            print(f"Error leyendo token: {e}")
            return None

    def _check_redemptions(self, token, status) -> bool:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        url = f"{URL_REDEMPTIONS}?status={status}"
        
        try:
            resp = self.scraper.get(url, headers=headers)
        except Exception as e:
            if time.time() - self._last_error_time > 30:
                self.log_signal.emit(LoggerText.error(f"Error de Red (Kick): {e}"))
                self._last_error_time = time.time()
            return False

        # Manejo de Rate Limit (429)
        if resp.status_code == 429:
            time.sleep(2)
            return False
        
        # Manejo de Token Expirado (401)
        if resp.status_code == 401:
            if time.time() - self._last_error_time > 30:
                self.log_signal.emit(LoggerText.warning("Monitor Puntos: Token expirado (401). Esperando renovación..."))
                self._last_error_time = time.time()
            return False

        # Otros errores (500, 403, etc)
        if resp.status_code != 200:
            if time.time() - self._last_error_time > 30:
                self.log_signal.emit(LoggerText.debug(f"Monitor Puntos API Error: {resp.status_code}"))
                self._last_error_time = time.time()
            return False

        try:
            data = resp.json()
            groups = data.get("data", [])
        except Exception as e:
            return False

        found_new = False

        for group in groups:
            reward_title = group.get("reward", {}).get("title", "")
            redemptions = group.get("redemptions", [])

            for red in redemptions:
                red_id = red.get("id")
                
                if red_id in self.processed_ids:
                    continue
                
                self.processed_ids.add(red_id)

                if self.first_scan:
                    continue 

                found_new = True 
                
                redeemer = red.get("redeemer", {})
                username = redeemer.get("username") or redeemer.get("slug") or "Anonimo"
                user_input = red.get("user_input", "")

                # 1. Disparar Trigger
                self.redemption_detected.emit(username, reward_title, user_input)
                
                # 2. Aceptar en Kick si está pendiente
                if status == "pending":
                    self._fulfill_redemption(red_id, token, headers)
        
        return found_new

    def _fulfill_redemption(self, red_id, token, headers):
        url = f"{URL_REDEMPTIONS}/accept"
        payload = {"ids": [red_id]}
        try:
            self.scraper.post(url, headers=headers, json=payload)
        except: pass