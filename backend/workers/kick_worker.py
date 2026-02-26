# backend/workers/kick_worker.py

import time
from typing import Dict, Any
from contextlib import suppress
from PyQt6.QtCore import QThread, pyqtSignal

KICK_API_BASE = "https://kick.com/api/v1/channels"
DEFAULT_MONITOR_INTERVAL = 10  

class KickApiWorker(QThread):
    """Worker efímero. Realiza una única consulta HTTP para validar."""    
    finished = pyqtSignal(bool, str, str, str, str, int, str)

    def __init__(self, username: str, shared_scraper):
        super().__init__()
        self.username = username
        self.scraper = shared_scraper

    def run(self):
        try:
            resp = self.scraper.get(f"{KICK_API_BASE}/{self.username}", timeout=10)
            if resp.status_code == 200:
                self._process_success(resp.json())
            else:
                self.finished.emit(False, f"Error {resp.status_code}: Usuario no encontrado", "", "", "", 0, "")
        except Exception as e:
            self.finished.emit(False, f"Error de Conexión: {str(e)}", "", "", "", 0, "")

    def _process_success(self, data: Dict[str, Any]):
        chat_id = str(data.get('chatroom', {}).get('id', ''))
        slug = data.get('slug', '')
        user_data = data.get('user', {})
        real_username = user_data.get('username', self.username)
        profile_pic = user_data.get('profile_pic', '')
        followers = data.get('followersCount', 0)
        
        self.finished.emit(True, "Encontrado", slug, chat_id, real_username, followers, profile_pic)

class FollowMonitorWorker(QThread):
    """Worker persistente que detecta cambios en el contador de seguidores.""" 
    new_follower = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)

    def __init__(self, username: str, shared_scraper, interval: int = DEFAULT_MONITOR_INTERVAL):
        super().__init__()
        self.username = username
        self.interval = interval
        self.scraper = shared_scraper
        self.is_running = True
        self.last_count = -1   

    def run(self):
        while self.is_running:
            with suppress(Exception):
                self._check_followers()
                
            for _ in range(self.interval):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait(1000)

    def _check_followers(self):
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
        with suppress(Exception):
            resp = self.scraper.get(f"https://kick.com/api/v2/channels/{self.username}/followers", timeout=10)            
            if resp.status_code == 200:
                data = resp.json().get('data', [])
                if data and isinstance(data, list):
                    primer_item = data[0]
                    nombre = primer_item.get('username') or primer_item.get('follower', {}).get('username')
                    if nombre: return nombre
        return "Nuevo Seguidor"