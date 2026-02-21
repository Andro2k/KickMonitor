# backend/workers/redemption_worker.py

import time
from contextlib import suppress
from PyQt6.QtCore import QThread, pyqtSignal

from backend.utils.logger_text import LoggerText
from backend.services.rewards_service import RewardsService 

class RedemptionWorker(QThread):
    # Señal: (usuario, recompensa, mensaje_opcional)
    redemption_detected = pyqtSignal(str, str, str)
    log_signal = pyqtSignal(str)

    def __init__(self, db_handler):
        super().__init__()
        self.db = db_handler
        self.is_running = True
        
        self.rewards_api = RewardsService()
        self.normal_interval = 3.5  
        self.burst_interval = 1.5   
        self.processed_ids = set() 
        self.first_scan = True
    # =========================================================================
    # REGIÓN 1: BUCLE PRINCIPAL
    # =========================================================================
    def run(self):
        self.log_signal.emit(LoggerText.system("Monitor de Puntos: Iniciado"))
        
        while self.is_running:
            with suppress(Exception):
                found_p = self._process_redemptions("pending")
                found_f = self._process_redemptions("fulfilled")
                
                self.first_scan = False

                sleep_time = self.burst_interval if (found_p or found_f) else self.normal_interval

                for _ in range(int(sleep_time * 10)):
                    if not self.is_running: break
                    time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait(1000)

    # =========================================================================
    # REGIÓN 2: LÓGICA DE PROCESAMIENTO
    # =========================================================================
    def _process_redemptions(self, status: str) -> bool:
        groups = self.rewards_api.get_redemptions(status)
        if not groups: return False

        found_new = False
        ids_to_accept = []

        for group in groups:
            title = group.get("reward", {}).get("title", "")
            
            for red in group.get("redemptions", []):
                red_id = red.get("id")

                if not red_id or red_id in self.processed_ids: 
                    continue
                
                self.processed_ids.add(red_id)
                
                if self.first_scan: 
                    continue 

                found_new = True 

                user_data = red.get("user", {})
                username = user_data.get("username") or user_data.get("slug") or "Anonimo"
                user_input = red.get("user_input", "")

                self.redemption_detected.emit(username, title, user_input)
                self.log_signal.emit(LoggerText.success(f"Canje detectado: {title} ({username})"))

                if status == "pending":
                    ids_to_accept.append(red_id)
        
        if ids_to_accept:
            self.rewards_api.accept_redemptions(ids_to_accept)
            
        return found_new