# backend/workers/kick_worker.py

import time
from typing import Dict, Any
from contextlib import suppress
import cloudscraper
from PyQt6.QtCore import QThread, pyqtSignal

# ==========================================
# CONSTANTES Y CONFIGURACIÓN
# ==========================================
KICK_API_BASE = "https://kick.com/api/v1/channels"
DEFAULT_MONITOR_INTERVAL = 30

# =========================================================================
# WORKER 1: API CHECKER (Búsqueda inicial de un solo uso)
# =========================================================================
class KickApiWorker(QThread):
    """Worker efímero. Realiza una única consulta HTTP para validar."""    
    finished = pyqtSignal(bool, str, str, str, str, int, str)

    def __init__(self, username: str):
        super().__init__()
        self.username = username

    def run(self):
        scraper = cloudscraper.create_scraper()
        try:
            resp = scraper.get(f"{KICK_API_BASE}/{self.username}", timeout=10)
            
            if resp.status_code == 200:
                self._process_success(resp.json())
            else:
                self.finished.emit(False, f"Error {resp.status_code}: Usuario no encontrado", "", "", "", 0, "")
                
        except Exception as e:
            self.finished.emit(False, f"Error de Conexión: {str(e)}", "", "", "", 0, "")

    def _process_success(self, data: Dict[str, Any]):
        """Extrae los datos del JSON de forma segura y directa."""
        chat_id = str(data.get('chatroom', {}).get('id', ''))
        slug = data.get('slug', '')
        
        user_data = data.get('user', {})
        real_username = user_data.get('username', self.username)
        profile_pic = user_data.get('profile_pic', '')
        followers = data.get('followersCount', 0)
        
        self.finished.emit(True, "Encontrado", slug, chat_id, real_username, followers, profile_pic)

# =========================================================================
# WORKER 2: MONITOR DE SEGUIDORES (Proceso en segundo plano)
# =========================================================================
class FollowMonitorWorker(QThread):
    """Worker persistente que detecta cambios en el contador de seguidores.""" 
    new_follower = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)

    def __init__(self, username: str, interval: int = DEFAULT_MONITOR_INTERVAL):
        super().__init__()
        self.username = username
        self.interval = interval
        self.is_running = True
        self.last_count = -1   
        self.scraper = cloudscraper.create_scraper()

    # =========================================================================
    # REGIÓN 1: BUCLE PRINCIPAL (THREAD RUN)
    # =========================================================================
    def run(self):
        """Ciclo de vida del hilo."""
        while self.is_running:
            with suppress(Exception):
                self._check_followers()
                
            for _ in range(self.interval):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        """Señal para detener el bucle de forma segura."""
        self.is_running = False
        self.quit()
        self.wait(1000)

    # =========================================================================
    # REGIÓN 2: LÓGICA DE API (PRIVADA)
    # =========================================================================
    def _check_followers(self):
        """Consulta el contador actual y compara con el historial."""
        resp = self.scraper.get(f"{KICK_API_BASE}/{self.username}", timeout=10)
        
        if resp.status_code != 200: return

        current_count = resp.json().get('followersCount', 0)        
        
        if self.last_count == -1:
            self.last_count = current_count
            return
            
        if current_count > self.last_count:
            diff = current_count - self.last_count
            new_name = self._fetch_latest_follower_name()
            
            self.new_follower.emit(current_count, diff, new_name)
            self.last_count = current_count

    def _fetch_latest_follower_name(self) -> str:
        """Obtiene el nombre del seguidor más reciente desde la lista."""
        with suppress(Exception):
            resp = self.scraper.get(f"{KICK_API_BASE}/{self.username}/followers", timeout=10)            
            if resp.status_code == 200:
                data = resp.json().get('data', [])
                if data:
                    return data[0].get('follower', {}).get('username', 'Nuevo Seguidor')
                    
        return "Nuevo Seguidor"