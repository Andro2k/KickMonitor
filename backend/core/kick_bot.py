# backend/kick_bot.py

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal

# Módulos Internos
from backend.core.db_controller import DBHandler 
from backend.utils.logger_text import LoggerText

# Nuevos Gestores Separados
from backend.core.kick.auth_manager import KickAuthManager
from backend.core.kick.api_manager import KickAPIManager
from backend.core.kick.chat_manager import KickChatManager

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
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Gestores (Se inician en el run)
        self.auth: Optional[KickAuthManager] = None
        self.api: Optional[KickAPIManager] = None
        self.chat: Optional[KickChatManager] = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main_orchestrator())
        except asyncio.CancelledError:
            self.log_received.emit(LoggerText.system("Bot detenido manualmente."))
        except Exception as e:
            self.log_received.emit(LoggerText.error(f"Error Crítico en Bot: {e}"))
        finally:
            self._cleanup_loop()
            self.disconnected_signal.emit()

    async def _main_orchestrator(self):
        self.log_received.emit(LoggerText.info("Iniciando motor Kick nativo."))
        self.http_session = aiohttp.ClientSession()

        # Instanciar Gestores
        self.auth = KickAuthManager(self.config, self.http_session, self.log_received.emit)
        self.api = KickAPIManager(self.auth, self.http_session, self.loop, self.db, self.config, self.log_received.emit, self.user_info_signal)
        self.chat = KickChatManager(self.http_session, self.loop, self.log_received.emit, self.chat_received.emit)

        # 1. Autenticación
        if not await self.auth.ensure_authentication():
            self.log_received.emit(LoggerText.error("Autenticación fallida o cancelada."))
            return 
            
        # 2. Descubrimiento (API)
        if not await self.api.detect_user_and_channel():
            self.username_required.emit()
            return
            
        # 3. Conexión al Chat (Pusher WebSocket)
        if not await self.chat.connect(self.api.chatroom_id, self.config.get('kick_username')):
            return
            
        # 4. Bucle principal
        try:
            while self._is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    def send_chat_message(self, text: str):
        """Llamado desde el Frontend para responder comandos"""
        if self.loop and self._is_running and self.api:
            asyncio.run_coroutine_threadsafe(self.api.send_message(text), self.loop)

    def stop(self):
        """Detiene el bot y despierta el loop de asyncio inmediatamente."""
        self._is_running = False

        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._cancel_all_tasks)

    def _cancel_all_tasks(self):
        """Función interna que se ejecuta DENTRO del hilo de asyncio para cancelar tareas."""
        for task in asyncio.all_tasks(self.loop):
            task.cancel()

    def _cleanup_loop(self):
        if not self.loop or self.loop.is_closed(): return
        try:
            self.loop.run_until_complete(self._shutdown_sequence())
            tasks = asyncio.all_tasks(self.loop)
            for t in tasks: t.cancel()
            self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            self.loop.close()
        except Exception as e:
            print(f"Error cerrando loop asíncrono: {e}")

    async def _shutdown_sequence(self):
        self.log_received.emit(LoggerText.system("Cerrando conexiones de red..."))

        if self.chat: 
            await self.chat.disconnect()
            
        if self.http_session and not self.http_session.closed: 
            await self.http_session.close()
            await asyncio.sleep(0.250)