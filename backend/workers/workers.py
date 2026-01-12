# backend/workers.py

import time
import cloudscraper
from typing import Optional, Dict, Any
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
    """
    Worker efímero. Realiza una única consulta HTTP para validar 
    si un usuario existe y obtener sus datos básicos (ID, Foto, Slug).
    """    
    # Señal: (Exito, Mensaje, Slug, ChatID, UsernameReal, Followers, ProfilePic)
    finished = pyqtSignal(bool, str, str, str, str, int, str)

    def __init__(self, username: str):
        super().__init__()
        self.username = username

    def run(self):
        scraper = cloudscraper.create_scraper()
        try:
            url = f"{KICK_API_BASE}/{self.username}"
            resp = scraper.get(url)
            
            if resp.status_code == 200:
                data = resp.json()
                self._process_success(data)
            else:
                self.finished.emit(False, f"Error {resp.status_code}: Usuario no encontrado", "", "", "", 0, "")
                
        except Exception as e:
            self.finished.emit(False, f"Error de Conexión: {str(e)}", "", "", "", 0, "")

    def _process_success(self, data: Dict[str, Any]):
        """Extrae los datos del JSON de forma segura."""
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
    """
    Worker persistente. Consulta periódicamente la API de Kick para
    detectar cambios en el contador de seguidores.
    """ 
    # Señales UI
    new_follower = pyqtSignal(int, int, str) # (Total, Diferencia, Nombre)
    error_signal = pyqtSignal(str)           # Errores internos (Logs)

    def __init__(self, username: str, interval: int = DEFAULT_MONITOR_INTERVAL):
        super().__init__()
        self.username = username
        self.interval = interval     
        # Estado
        self.is_running = True
        self.last_count = -1   
        # Cliente HTTP persistente (reutiliza conexión TCP/TLS)
        self.scraper = cloudscraper.create_scraper()

    # =========================================================================
    # REGIÓN 1: BUCLE PRINCIPAL (THREAD RUN)
    # =========================================================================
    def run(self):
        """Ciclo de vida del hilo."""
        while self.is_running:
            try:
                self._check_followers()
            except Exception as e:
                self.error_signal.emit(f"Error Monitor: {e}")
            for _ in range(self.interval):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        """Señal para detener el bucle de forma segura."""
        self.is_running = False
        self.wait()

    # =========================================================================
    # REGIÓN 2: LÓGICA DE API (PRIVADA)
    # =========================================================================
    def _check_followers(self):
        """Consulta el contador actual y compara con el historial."""
        url = f"{KICK_API_BASE}/{self.username}"
        resp = self.scraper.get(url)
        
        if resp.status_code != 200:
            return # Fallo de red temporal, ignoramos este ciclo

        data = resp.json()
        current_count = data.get('followersCount', 0)        
        # Caso A: Primera ejecución (Inicialización)
        if self.last_count == -1:
            self.last_count = current_count
            return
        # Caso B: Cambio detectado (Nuevo seguidor)
        if current_count > self.last_count:
            diff = current_count - self.last_count
            new_name = self._fetch_latest_follower_name()
            
            self.new_follower.emit(current_count, diff, new_name)
            self.last_count = current_count

    def _fetch_latest_follower_name(self) -> str:
        """Obtiene el nombre del seguidor más reciente desde la lista."""
        try:
            # Endpoint específico para la lista de seguidores
            url_list = f"{KICK_API_BASE}/{self.username}/followers"
            resp = self.scraper.get(url_list)            
            if resp.status_code == 200:
                data = resp.json()
                # Kick devuelve los más recientes primero (índice 0)
                if data and 'followers' in data:
                    items = data['followers']
                    if items and len(items) > 0:
                        return items[0].get('username', 'Nuevo Seguidor')
        except:
            # Si falla esta sub-consulta, no rompemos el flujo, devolvemos genérico
            pass           
        return "Nuevo Seguidor"