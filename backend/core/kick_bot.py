# backend/kick_bot.py

import asyncio
import json
import os
import aiohttp
import cloudscraper
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
# --- LIBRERÍAS EXTERNAS ---
from kickpython import KickAPI
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

# --- MÓDULOS INTERNOS ---
from backend.core.db_controller import DBHandler 
from backend.utils.logger_text import Log
from backend.utils.paths import get_config_path
from backend.services.oauth_service import OAuthService

# ==========================================
# CONSTANTES & CONFIGURACIÓN
# ==========================================
CONFIG_DIR = get_config_path()
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")
DB_FILE_PATH = os.path.join(CONFIG_DIR, "kick_data.db")
KICK_API_BASE = "https://kick.com/api/v1"
KICK_CHAT_API = "https://api.kick.com/public/v1/chat"

class KickBotWorker(QThread):
    # --- SEÑALES UI ---
    chat_received = pyqtSignal(str, str, list, str)         
    log_received = pyqtSignal(str)               
    disconnected_signal = pyqtSignal()           
    user_info_signal = pyqtSignal(str, int, str)
    username_required = pyqtSignal() 

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.db = DBHandler()  
        self._is_running = True
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.api: Optional[KickAPI] = None 
        self.chatroom_id = str(self.config.get('chatroom_id', ''))
        self.broadcaster_user_id: Optional[int] = None       
        self.scraper = cloudscraper.create_scraper()

    # =========================================================================
    # REGIÓN 1: CICLO DE VIDA (THREAD & ASYNC LOOP)
    # =========================================================================
    def run(self):
        """Punto de entrada del QThread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._main_orchestrator())
        except asyncio.CancelledError:
            self.log_received.emit(Log.system("Bot detenido manualmente."))
        except Exception as e:
            self.log_received.emit(Log.error(f"Error Crítico en Bot: {e}"))
        finally:
            self._cleanup_loop()
            self.disconnected_signal.emit()

    def stop(self):
        """Señal externa para detener el bot."""
        self._is_running = False

    def _cleanup_loop(self):
        """Cierre limpio de recursos asíncronos."""
        if not self.loop or self.loop.is_closed():
            return
            
        try:
            self.loop.run_until_complete(self._shutdown_sequence())
            self.loop.close()
        except Exception as e:
            self.log_received.emit(Log.debug(f"Error cerrando loop asíncrono: {e}"))

    async def _shutdown_sequence(self):
        """Cierra conexiones WebSocket y HTTP pendientes."""
        self.log_received.emit(Log.system("Cerrando conexiones."))
        
        # 1. Cerrar WebSocket de Kick
        if self.api and hasattr(self.api, 'ws') and self.api.ws:
            try: await self.api.ws.close()
            except: pass
            
        # 2. Cerrar sesiones HTTP aiohttp
        if self.api:
            sessions = []
            if hasattr(self.api, 'http') and hasattr(self.api.http, 'session'): 
                sessions.append(self.api.http.session)
            if hasattr(self.api, 'session'): 
                sessions.append(self.api.session)
                
            for s in sessions: 
                if s and not s.closed:
                    try: await s.close()
                    except: pass
                    
        # 3. Cancelar tareas pendientes
        tasks = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task()]
        for t in tasks: t.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=1.0)

    # =========================================================================
    # REGIÓN 2: ORQUESTADOR PRINCIPAL
    # =========================================================================
    async def _main_orchestrator(self):
        """Controla el flujo lógico de inicio del bot."""
        self.log_received.emit(Log.info("Iniciando motor Kick."))

        # Inicializar Wrapper de API
        self.api = KickAPI(
            client_id=self.config.get('client_id'), 
            client_secret=self.config.get('client_secret'), 
            redirect_uri=self.config.get('redirect_uri'),
            db_path=DB_FILE_PATH 
        )
        # PASO 1: Autenticación OAuth
        if not await self._ensure_authentication():
            self.log_received.emit(Log.error("Autenticación fallida o cancelada."))
            return 
        # PASO 2: Identificar Usuario y Canal
        if not await self._detect_user_and_channel():
            self.log_received.emit(Log.warning("No se pudo detectar usuario automáticamente."))
            self.username_required.emit()
            return
        # PASO 3: Conexión al Chat
        if not await self._connect_chat():
            return
        # PASO 4: Loop de Mantenimiento (Keep-Alive)
        self.log_received.emit(Log.success("Sistema operativo y escuchando."))
        while self._is_running:
            try: 
                await asyncio.sleep(1)
            except asyncio.CancelledError: 
                break

    # =========================================================================
    # REGIÓN 3: AUTENTICACIÓN (OAUTH)
    # =========================================================================
    async def _ensure_authentication(self) -> bool:
        """Verifica si existe una sesión válida o inicia login."""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    token = data.get("access_token")
                if token:
                    self.api.access_token = token
                    self.log_received.emit(Log.success("Token de acceso restaurado."))
                    return True
            except Exception as e:
                self.log_received.emit(Log.warning(f"Sesión corrupta: {e}"))
        
        return await self._perform_oauth_login()

    async def _perform_oauth_login(self) -> bool:
        """Realiza el flujo completo de Login con Navegador."""
        self.log_received.emit(Log.system("Iniciando Login OAuth (Abre tu navegador)."))
        scopes = ["user:read", "channel:read", "channel:write", "chat:write", "events:subscribe", "channel:rewards:read"]
        
        try:
            auth_data = self.api.get_auth_url(scopes)
            verifier = auth_data["code_verifier"]
            
            # Servicio temporal para recibir el callback
            oauth_service = OAuthService(port=8080)
            
            QDesktopServices.openUrl(QUrl(auth_data["auth_url"]))
            code = await oauth_service.wait_for_code(timeout=60)
            
            if not code: 
                self.log_received.emit(Log.error("Login cancelado: Tiempo de espera agotado."))
                return False
            
            token_data = await self.api.exchange_code(code, verifier)
            if not token_data.get("access_token"):
                return False
            
            self._save_session(token_data)
            self.api.access_token = token_data.get("access_token")
            return True
            
        except Exception as e:
            self.log_received.emit(Log.error(f"Excepción durante Login: {e}"))
            return False

    async def _refresh_token_silently(self) -> bool:
        """Intenta renovar el token usando el refresh_token."""
        if not os.path.exists(SESSION_FILE): return False
        
        try:
            with open(SESSION_FILE, 'r') as f: 
                data = json.load(f)
            
            refresh_token = data.get("refresh_token")
            if not refresh_token: return False

            url = "https://id.kick.com/oauth/token"
            payload = {
                "grant_type": "refresh_token",
                "client_id": self.config.get("client_id"),
                "client_secret": self.config.get("client_secret"),
                "refresh_token": refresh_token
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as resp:
                    if resp.status == 200:
                        new_data = await resp.json()
                        # Preservar refresh token si no viene uno nuevo
                        if "refresh_token" not in new_data: 
                            new_data["refresh_token"] = refresh_token
                        
                        self._save_session(new_data)
                        self.api.access_token = new_data.get("access_token")
                        self.log_received.emit(Log.debug("Token renovado automáticamente."))
                        return True
                    else:
                        self.log_received.emit(Log.warning(f"Fallo al renovar token: {resp.status}"))
        except Exception as e:
            self.log_received.emit(Log.debug(f"Error renovando token: {e}"))
            
        return False

    def _save_session(self, data: dict):
        with open(SESSION_FILE, 'w') as f: 
            json.dump(data, f, indent=4)

    # =========================================================================
    # REGIÓN 4: DESCUBRIMIENTO DE USUARIO Y CANAL
    # =========================================================================
    async def _detect_user_and_channel(self) -> bool:
        """
        Obtiene los IDs del canal basándose estrictamente en la configuración local.
        """
        # 1. Recuperar usuario de la configuración (DB)
        target_user = self.config.get('kick_username') 
        
        if not target_user:
            self.log_received.emit(Log.error("Falta configurar el nombre de usuario del canal."))
            return False

        self.log_received.emit(Log.info(f"Cargando datos para el canal: {target_user}"))

        if self._load_from_cache(target_user):
            self.log_received.emit(Log.success("Datos de canal cargados desde caché."))
            return True

        if await self._fetch_channel_data(target_user): 
            return True
            
        return False

    async def _fetch_channel_data(self, target_user: str) -> bool:
        """Obtiene chatroom_id y broadcaster_id del canal."""
        try:
            token = getattr(self.api, 'access_token', None)
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            
            resp = await self.loop.run_in_executor(
                None, 
                lambda: self.scraper.get(f"{KICK_API_BASE}/channels/{target_user}", headers=headers)
            )
            
            if resp.status_code == 200:
                data = resp.json()
                self._process_channel_response(data, target_user)
                return True
                
        except Exception as e: 
            self.log_received.emit(Log.error(f"Error obteniendo datos del canal: {e}"))
        return False

    def _process_channel_response(self, data: dict, target_user: str):
        """Procesa y guarda la info del canal recibida de la API."""
        if 'chatroom' in data and 'id' in data['chatroom']:
            self.chatroom_id = str(data['chatroom']['id'])
            self.db.set("chatroom_id", self.chatroom_id)
        
        # Extraer IDs posibles
        uid = data.get('user_id') or data.get('id') or data.get('user', {}).get('id')
        if uid: 
            self.broadcaster_user_id = uid

        # Guardar en DB
        username = data.get('username') or data.get('user', {}).get('username') or target_user
        slug = data.get('slug') or target_user
        pic = data.get('profile_pic') or data.get('user', {}).get('profile_pic') or ""
        followers = data.get('followersCount') or data.get('followers_count') or 0

        self.db.save_kick_user(slug, username, followers, pic, self.chatroom_id, self.broadcaster_user_id)
        self.user_info_signal.emit(username, followers, pic)
        self.log_received.emit(Log.success(f"Datos actualizados para: {username}"))

    def _load_from_cache(self, target_user: str) -> bool:
        cached = self.db.get_kick_user(target_user)
        if cached and cached.get('user_id'):
            self.broadcaster_user_id = cached['user_id']
            chat_id_db = self.db.get("chatroom_id")
            if chat_id_db:
                self.chatroom_id = chat_id_db
                return True
        return False

    # =========================================================================
    # REGIÓN 5: GESTIÓN DEL CHAT (CONEXIÓN Y MENSAJES)
    # =========================================================================
    async def _connect_chat(self) -> bool:
        if not self.chatroom_id: 
            self.log_received.emit(Log.error("Error Fatal: Chatroom ID no encontrado."))
            return False
            
        self.log_received.emit(Log.debug(f"Conectando a sala de chat: {self.chatroom_id}"))

        self.api.add_message_handler(self._on_message_received)
        try:
            await self.api.connect_to_chatroom(self.chatroom_id)
            self.log_received.emit(Log.success(f"CHAT CONECTADO: {self.config.get('kick_username')}"))
            return True
        except Exception as e:
            self.log_received.emit(Log.error(f"Fallo conexión WebSocket: {e}"))
            return False

    async def _on_message_received(self, msg):
        """
        Callback principal.
        """
        try:
            # Si msg es string (json), intentamos convertirlo
            if isinstance(msg, str):
                try: msg = json.loads(msg)
                except: pass
            # Validación básica
            if not isinstance(msg, dict):
                return
            
            content = msg.get('content', '')
            if not content: return
            # 1. Extraer Usuario (Según tus logs es 'sender_username')
            sender = msg.get('sender_username')
            if not sender and 'sender' in msg and isinstance(msg['sender'], dict):
                sender = msg['sender'].get('username')
            
            if not sender: sender = "Desconocido"
            # 2. Extraer Insignias (Según tus logs es una lista directa de strings)
            badges = msg.get('badges', [])
            
            # 3. Timestamp actual
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 4. Emitir señal limpia
            self.chat_received.emit(sender, content, badges, timestamp)

        except Exception as e:
            self.log_received.emit(Log.error(f"Error procesando mensaje: {e}"))
            self.log_received.emit(Log.debug(f"Contenido crudo del mensaje fallido: {msg}"))

    def _parse_incoming_message(self, msg: dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrae usuario y contenido limpiando la estructura anidada de Kick/Pusher.
        """
        payload = msg
        # Desempaquetar string JSON en 'data' si existe
        if 'data' in msg:
            if isinstance(msg['data'], str):
                try: payload = json.loads(msg['data'])
                except json.JSONDecodeError: pass
            elif isinstance(msg['data'], dict):
                payload = msg['data']
        # Extraer contenido
        content = payload.get('content') or payload.get('message')
        # Extraer usuario
        sender = payload.get('sender', {})
        username = None
        
        if isinstance(sender, dict) and 'username' in sender:
            username = sender['username']
        elif 'sender_username' in payload:
            username = payload['sender_username']
        elif 'username' in payload:
            username = payload['username']

        return username, content

    def send_chat_message(self, text: str):
        """Encolar envío de mensaje al hilo asyncio."""
        if self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(self._send_safe(text), self.loop)

    async def _send_safe(self, text: str, retry_attempt: bool = True):
        """Envía mensaje vía HTTP con reintento automático si falla el token."""
        try:
            token = getattr(self.api, 'access_token', None)
            if not token: 
                self.log_received.emit(Log.warning("No se pudo enviar mensaje: Falta Token."))
                return

            headers = { 
                "Authorization": f"Bearer {token}", 
                "Content-Type": "application/json", 
                "Accept": "application/json" 
            }
            payload = { 
                "broadcaster_user_id": int(self.broadcaster_user_id), 
                "content": text, 
                "type": "bot" 
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(KICK_CHAT_API, json=payload, headers=headers) as resp:
                    # Si falla por autorización (401), intentar refrescar token y reintentar una vez
                    if resp.status == 401 and retry_attempt:
                        self.log_received.emit(Log.warning("Token expirado al enviar. Renovando."))
                        if await self._refresh_token_silently():
                            await self._send_safe(text, retry_attempt=False)
                    elif resp.status != 200:
                        self.log_received.emit(Log.error(f"Error enviando mensaje: Status {resp.status}"))
                        
        except Exception as e:
            self.log_received.emit(Log.error(f"Excepción al enviar mensaje: {e}"))