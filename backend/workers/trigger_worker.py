# backend/workers/overlay_worker.py

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional, Set, Dict, Any

from aiohttp import web, WSMsgType
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

class OverlayServerWorker(QThread):
    """
    Servidor Web (aiohttp) que corre en un hilo secundario.
    Sirve el HTML del Overlay y maneja WebSockets para alertas en tiempo real.
    """    
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.db = DBHandler()        
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None        
        self.websockets: Set[web.WebSocketResponse] = set()        
        self.is_active = self.db.get_bool("overlay_enabled")

    # =========================================================================
    # REGIÓN 1: API PÚBLICA (LLAMADA DESDE CONTROLLER/UI)
    # =========================================================================
    def set_active(self, state: bool):
        self.is_active = state
        self.log_signal.emit(LoggerText.system(f"Servidor Overlay: {'ACTIVO' if state else 'INACTIVO'}"))

    def send_event(self, action: str, payload: dict = None):
        if not self.is_active: return        
        if self.loop and self.loop.is_running(): 
            asyncio.run_coroutine_threadsafe(self._broadcast(action, payload), self.loop)

    def stop(self):
        if self.loop:
             self.loop.call_soon_threadsafe(self.loop.stop)
        self.quit()
        self.wait(1000)

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
            self.log_signal.emit(LoggerText.error(f"Excepción Crítica en Servidor: {e}"))
        finally:
            self.loop.run_until_complete(self._async_cleanup())
            self.loop.close()

    async def _async_start(self, app):
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', SERVER_PORT)
        await self.site.start()
        self.log_signal.emit(LoggerText.success(f"Overlay Online: http://127.0.0.1:{SERVER_PORT}"))

    async def _async_cleanup(self):
        if self.websockets:
            await asyncio.gather(
                *(ws.close(code=1001, message=b"Server shutting down") for ws in self.websockets),
                return_exceptions=True
            )
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()

    # =========================================================================
    # REGIÓN 3: RUTAS HTTP & ARCHIVOS
    # =========================================================================
    def _setup_routes(self, app):
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/ws', self.websocket_handler)        
        app.router.add_get('/media/{filename}', self.handle_media_request)       
        
        assets_path = self._get_asset_path("") 
        if assets_path.exists():
            app.router.add_static('/assets', path=str(assets_path))

    async def handle_index(self, request):
        path = self._get_asset_path("overlay.html")
        if path.exists():
            return web.FileResponse(path)
        return web.Response(status=404, text="<h1>Error 404</h1><p>overlay.html no encontrado en assets.</p>", content_type='text/html')

    async def handle_media_request(self, request):
        filename = request.match_info['filename']
        folder_str = self.db.get("media_folder")
        
        if not folder_str:
            return web.Response(status=404, text="Carpeta multimedia no configurada.")
        
        user_folder = Path(folder_str).resolve()
        if not user_folder.exists():
            return web.Response(status=404, text="Carpeta no encontrada.")

        full_path = (user_folder / filename).resolve()

        if not full_path.is_relative_to(user_folder):
            return web.Response(status=403, text="Acceso Denegado.")

        if full_path.is_file():
            return web.FileResponse(full_path, chunk_size=CHUNK_SIZE)
            
        return web.Response(status=404, text="Archivo no encontrado.")

    # =========================================================================
    # REGIÓN 4: GESTIÓN DE WEBSOCKETS
    # =========================================================================
    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    self.log_signal.emit(LoggerText.error(f'WS Error: {ws.exception()}'))
        finally:
            self.websockets.discard(ws)
        return ws

    async def _broadcast(self, action: str, payload: Dict[str, Any] = None):
        if not self.websockets: return

        data = {"action": action} | (payload or {})

        await asyncio.gather(
            *(ws.send_json(data) for ws in self.websockets if not ws.closed),
            return_exceptions=True
        )

    # =========================================================================
    # REGIÓN 5: UTILIDADES DE RUTAS
    # =========================================================================
    def _get_asset_path(self, filename: str) -> Path:
        """Resuelve rutas estáticas apuntando a assets/overlays."""
        if hasattr(sys, '_MEIPASS'): 
            # Ruta cuando el bot está compilado en .exe (PyInstaller)
            base_dir = Path(sys._MEIPASS) / "assets" / "overlays"
        else:
            # Modo desarrollo: Sube 3 niveles (workers -> backend -> raíz) -> entra a assets/overlays
            base_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "overlays"

        return base_dir / filename if filename else base_dir