# backend/workers/unified_server.py

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Set

from aiohttp import web
from PyQt6.QtCore import QThread, pyqtSignal

from backend.core.db_controller import DBHandler
from backend.utils.logger_text import LoggerText 

# ==========================================
# 1. CONSTANTES & CONFIGURACIÓN
# ==========================================
SERVER_PORT = 8081
CHUNK_SIZE = 1024 * 1024

LOG_MODULES_TO_SILENCE = ['aiohttp.access', 'aiohttp.server', 'comtypes', 'kickpython']
for lib in LOG_MODULES_TO_SILENCE:
    logging.getLogger(lib).setLevel(logging.WARNING)

class UnifiedOverlayWorker(QThread):
    """
    Servidor Web unificado (aiohttp). 
    Maneja Triggers, Chat y Alertas en un solo puerto y Event Loop.
    """    
    log_signal = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.db = DBHandler()        
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None        
        
        # Sets de WebSockets separados por módulo
        self.ws_triggers: Set[web.WebSocketResponse] = set()        
        self.ws_chat: Set[web.WebSocketResponse] = set()        
        self.ws_alerts: Set[web.WebSocketResponse] = set()        
        
        self.latest_chat_config = {}
        self.is_active = self.db.get_bool("overlay_enabled")

    # =========================================================================
    # REGIÓN 2: CICLO DE VIDA DEL SERVIDOR (THREAD RUN)
    # =========================================================================
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)       
        app = web.Application()
        self._setup_routes(app)
        self.runner = web.AppRunner(app, access_log=None)       
        
        try:
            self.loop.run_until_complete(self._async_start(app))
            self.loop.run_forever() 
        except Exception as e:
            self.error_occurred.emit(f"Excepción Crítica en Servidor Unificado: {e}")
            self.log_signal.emit(LoggerText.error(f"Excepción Crítica en Servidor: {e}"))
        finally:
            tasks = asyncio.all_tasks(self.loop)
            for t in tasks: t.cancel()
            self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            self.loop.close()

    async def _async_start(self, app):
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', SERVER_PORT)
        await self.site.start()
        self.log_signal.emit(LoggerText.success(f"Overlay Unificado Online: http://127.0.0.1:{SERVER_PORT}"))

    def stop(self):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._safe_shutdown(), self.loop)
        self.quit()
        self.wait(1500)

    async def _safe_shutdown(self):
        all_ws = self.ws_triggers | self.ws_chat | self.ws_alerts
        if all_ws:
            await asyncio.gather(
                *(ws.close(code=1001, message=b"Server shutting down") for ws in list(all_ws)),
                return_exceptions=True
            )
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()
        self.loop.stop()

    # =========================================================================
    # REGIÓN 3: ENRUTAMIENTO HTTP
    # =========================================================================
    def _setup_routes(self, app):
        # Páginas HTML
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/chat', self.handle_chat)
        app.router.add_get('/alerts', self.handle_alerts)
        
        # Conexiones WebSocket
        app.router.add_get('/ws/triggers', self.ws_triggers_handler)        
        app.router.add_get('/ws/chat', self.ws_chat_handler)        
        app.router.add_get('/ws/alerts', self.ws_alerts_handler)        
        
        # Archivos Dinámicos y Estáticos
        app.router.add_get('/media/{filename}', self.handle_media_request)       
        assets_path = self._get_asset_path("") 
        if assets_path.exists():
            app.router.add_static('/assets', path=str(assets_path))

    async def _serve_html(self, filename: str):
        path = self._get_asset_path(filename)
        if path.exists():
            return web.FileResponse(path)
        return web.Response(status=404, text=f"<h1>Error 404</h1><p>{filename} no encontrado.</p>", content_type='text/html')

    async def handle_index(self, request): return await self._serve_html("triggers_overlay.html")
    async def handle_chat(self, request): return await self._serve_html("chat_overlay.html")
    async def handle_alerts(self, request): return await self._serve_html("alerts_overlay.html")

    async def handle_media_request(self, request):
        filename = request.match_info['filename']
        config = self.db.get_all_triggers().get(filename)
        if not config or "path" not in config:
            return web.Response(status=404, text="Archivo no registrado.")
        
        full_path = Path(config["path"]).resolve()
        if full_path.is_file():
            return web.FileResponse(full_path, chunk_size=CHUNK_SIZE)
        return web.Response(status=404, text="Archivo no encontrado.")

    # =========================================================================
    # REGIÓN 4: HANDLERS DE WEBSOCKETS (SEPARADOS POR SALA)
    # =========================================================================
    async def ws_triggers_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_triggers.add(ws)
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.ERROR:
                    self.log_signal.emit(LoggerText.error(f'WS Triggers Error: {ws.exception()}'))
        finally:
            self.ws_triggers.discard(ws)
        return ws

    async def ws_chat_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_chat.add(ws)
        if self.latest_chat_config:
            await ws.send_json({"type": "update_chat_styles", "payload": self.latest_chat_config})
        try:
            async for msg in ws: pass
        finally:
            self.ws_chat.discard(ws)
        return ws

    async def ws_alerts_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_alerts.add(ws)
        try:
            async for msg in ws: pass
        finally:
            self.ws_alerts.discard(ws)
        return ws

    async def _broadcast(self, target_set: Set[web.WebSocketResponse], data: dict):
        if not target_set: return
        await asyncio.gather(
            *(ws.send_json(data) for ws in target_set if not ws.closed),
            return_exceptions=True
        )

    # =========================================================================
    # REGIÓN 5: API PÚBLICA DE DIFUSIÓN (LLAMADAS DESDE EL CONTROLLER)
    # =========================================================================
    def set_active(self, state: bool):
        self.is_active = state
        self.log_signal.emit(LoggerText.system(f"Servidor Overlay: {'ACTIVO' if state else 'INACTIVO'}"))

    # --- TRIGGERS ---
    def send_event(self, action: str, payload: dict = None):
        if not self.is_active or not self.loop: return        
        data = {"action": action} | (payload or {})
        asyncio.run_coroutine_threadsafe(self._broadcast(self.ws_triggers, data), self.loop)

    # --- CHAT ---
    def send_chat_message_to_overlay(self, sender, content, badges=None, user_color=None, timestamp=""):
        if not self.loop: return
        payload = {
            "type": "new_message",
            "payload": {"sender": sender, "content": content, "badges": badges or [], "color": user_color, "timestamp": timestamp}
        }
        asyncio.run_coroutine_threadsafe(self._broadcast(self.ws_chat, payload), self.loop)

    def update_chat_styles(self, style_dict):
        if not self.loop: return
        self.latest_chat_config |= style_dict
        payload = {"type": "update_chat_styles", "payload": style_dict}
        asyncio.run_coroutine_threadsafe(self._broadcast(self.ws_chat, payload), self.loop)

    # --- ALERTAS ---
    def send_alert(self, alert_type: str, title: str, message: str, color: str = None, 
                   image_url: str = None, sound_url: str = None, duration: int = 5, 
                   layout_style: str = "Imagen Arriba", animation: str = "Pop In"):
        if not self.loop: return
        payload = {
            "type": "new_alert",
            "payload": {"alert_type": alert_type, "title": title, "message": message, "color": color, 
                        "image_url": image_url, "sound_url": sound_url, "duration": duration, 
                        "layout_style": layout_style, "animation": animation}
        }
        asyncio.run_coroutine_threadsafe(self._broadcast(self.ws_alerts, payload), self.loop)
    # --- Triggers, Chat y Alertas comparten el mismo método de broadcast pero con sets de WebSockets separados. ---
    def _get_asset_path(self, filename: str) -> Path:
        if hasattr(sys, '_MEIPASS'): 
            base_dir = Path(sys._MEIPASS) / "assets" / "overlays"
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "overlays"
        return base_dir / filename if filename else base_dir