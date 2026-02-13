# backend/workers/redemption_worker.py

import time
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
        
        # El servicio centralizado ahora maneja toda la lógica HTTP y Tokens
        self.rewards_api = RewardsService() 
        
        self.normal_interval = 1.5  
        self.burst_interval = 0.5   
        self.processed_ids = set() 
        self.first_scan = True 

    def run(self):
        self.log_signal.emit(LoggerText.system("Monitor de Puntos: Iniciado"))
        
        while self.is_running:
            # Procesamos pendientes y completados de forma limpia
            found_p = self._process_redemptions(status="pending")
            found_f = self._process_redemptions(status="fulfilled")
            
            found_something = found_p or found_f
            
            # Al terminar la primera vuelta, desactivamos el primer escaneo
            self.first_scan = False

            # Calcular tiempo de espera (más rápido si hubo actividad reciente)
            sleep_time = self.burst_interval if found_something else self.normal_interval
            
            # Loop de espera fraccionado para permitir apagado rápido si cierras la app
            steps = int(sleep_time * 10)
            for _ in range(steps):
                if not self.is_running: break
                time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.wait()

    def _process_redemptions(self, status: str) -> bool:
        """Obtiene y procesa los canjes delegando el HTTP al RewardsService."""
        groups = self.rewards_api.get_redemptions(status)
        found_new = False

        if not groups: 
            return False

        for group in groups:
            reward_title = group.get("reward", {}).get("title", "")
            redemptions = group.get("redemptions", [])

            for red in redemptions:
                red_id = red.get("id")
                
                # Ignorar si ya lo procesamos previamente en esta sesión
                if red_id in self.processed_ids:
                    continue
                
                self.processed_ids.add(red_id)

                # Ignorar en el primer escaneo (evitar disparar eventos viejos al iniciar el bot)
                if self.first_scan:
                    continue 

                found_new = True 
                
                redeemer = red.get("redeemer", {})
                username = redeemer.get("username") or redeemer.get("slug") or "Anonimo"
                user_input = red.get("user_input", "")

                # 1. Disparar evento a la Interfaz / Controller (para ejecutar triggers/overlay)
                self.redemption_detected.emit(username, reward_title, user_input)
                self.log_signal.emit(LoggerText.success(f"Canje detectado: {reward_title} ({username})"))

                # 2. Aceptar el canje en Kick automáticamente si estaba pendiente
                if status == "pending":
                    self.rewards_api.accept_redemption(red_id)
        
        return found_new