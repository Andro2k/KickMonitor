# backend/workers/redemption_worker.py

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from PyQt6.QtCore import QThread, pyqtSignal

from backend.utils.logger_text import LoggerText
from backend.services.rewards_service import RewardsService 

class RedemptionWorker(QThread):
    redemption_detected = pyqtSignal(str, str, str)
    log_signal = pyqtSignal(str)

    def __init__(self, db_handler, shared_scraper=None):
        super().__init__()
        self.db = db_handler
        self.is_running = True
        
        self.rewards_api = RewardsService(shared_scraper)
        
        # TIMERS OPTIMIZADOS
        self.normal_interval = 2.0  # Más rápido en inactividad
        self.burst_interval = 1.0   # Muy rápido cuando hay actividad reciente
        
        self.processed_ids = set() 
        self.first_scan = True
        
        # Ejecutor de hilos para paralelizar llamadas HTTP
        self.executor = ThreadPoolExecutor(max_workers=2)

    def run(self):
        self.log_signal.emit(LoggerText.system("Monitor de Puntos: Iniciado (Modo Alta Velocidad)"))
        
        cycle_count = 0
        
        while self.is_running:
            with suppress(Exception):
                # Usamos el ejecutor para lanzar ambas peticiones al mismo tiempo
                # pero los 'fulfilled' solo los revisamos cada 5 ciclos para ahorrar red y evitar rate-limits
                future_p = self.executor.submit(self._process_redemptions, "pending")
                
                check_fulfilled = (cycle_count % 5 == 0)
                future_f = self.executor.submit(self._process_redemptions, "fulfilled") if check_fulfilled else None
                
                # Esperar respuesta de pending (que es la que nos importa para disparar el trigger rápido)
                found_p = future_p.result()
                found_f = future_f.result() if future_f else False
                
                self.first_scan = False
                cycle_count += 1

                # Dormir usando el burst o normal
                sleep_time = self.burst_interval if (found_p or found_f) else self.normal_interval

                # Dormir de forma que podamos interrumpir rápidamente si self.is_running pasa a False
                for _ in range(int(sleep_time * 10)):
                    if not self.is_running: break
                    time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.executor.shutdown(wait=False)
        self.quit()
        self.wait(1000)

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

                # Emitimos la señal de inmediato para que el UnifiedServer mande la alerta
                self.redemption_detected.emit(username, title, user_input)
                self.log_signal.emit(LoggerText.success(f"Canje detectado: {title} ({username})"))

                if status == "pending":
                    ids_to_accept.append(red_id)
        
        # Aceptar redenciones en Kick
        if ids_to_accept:
            # Si aceptar también es lento, puedes lanzarlo en background:
            # self.executor.submit(self.rewards_api.accept_redemptions, ids_to_accept)
            self.rewards_api.accept_redemptions(ids_to_accept)
            
        return found_new