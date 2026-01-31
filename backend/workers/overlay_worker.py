# backend/overlay_server.py

import asyncio
import os
import sys
import logging
from typing import Optional, Set, Dict, Any

from aiohttp import web, WSMsgType
from PyQt6.QtCore import QThread, pyqtSignal

from backend.core.db_controller import DBHandler
from backend.utils.logger_text import Log 

# ==========================================
# 1. CONSTANTES & CONFIGURACIÓN
# ==========================================
SERVER_PORT = 8081
CHUNK_SIZE = 1024 * 1024  # 1MB para streaming local

# Silenciar logs ruidosos de librerías de terceros
LOG_MODULES_TO_SILENCE = ['aiohttp.access', 'aiohttp.server', 'comtypes', 'kickpython']
for lib in LOG_MODULES_TO_SILENCE:
    logging.getLogger(lib).setLevel(logging.WARNING)

class OverlayServerWorker(QThread):
    """
    Servidor Web (aiohttp) que corre en un hilo secundario.
    Sirve el HTML del Overlay y maneja WebSockets para alertas en tiempo real.
    """    
    # Señal para enviar logs a la consola principal UI
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.db = DBHandler()        
        # Asyncio & Aiohttp State
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None        
        # Clientes Conectados
        self.websockets: Set[web.WebSocketResponse] = set()        
        # Estado lógico
        self.is_active = self.db.get_bool("overlay_enabled")

    # =========================================================================
    # REGIÓN 1: API PÚBLICA (LLAMADA DESDE CONTROLLER/UI)
    # =========================================================================
    def set_active(self, state: bool):
        """Habilita o deshabilita el envío de eventos (Broadcast)."""
        self.is_active = state
        status = "ACTIVO" if state else "INACTIVO"
        self.log_signal.emit(Log.system(f"Servidor Overlay: {status}"))

    def send_event(self, action: str, payload: dict = None):
        """Encola un mensaje para ser enviado a todos los clientes WebSocket."""
        if not self.is_active: return        
        if self.loop and self.loop.is_running(): 
            asyncio.run_coroutine_threadsafe(self._broadcast(action, payload), self.loop)

    def stop(self):
        """Detiene el servidor y el hilo de forma segura."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()

    # =========================================================================
    # REGIÓN 2: CICLO DE VIDA DEL SERVIDOR (THREAD RUN)
    # =========================================================================
    def run(self):
        """Punto de entrada del QThread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)       
        app = web.Application()
        self._setup_routes(app)
        self.runner = web.AppRunner(app, access_log=None)       
        try:
            self.loop.run_until_complete(self._async_start(app))
            self.loop.run_forever() # Bloqueo principal
        except Exception as e:
            self.log_signal.emit(Log.error(f"Excepción Crítica en Servidor: {e}"))
        finally:
            self.loop.run_until_complete(self._async_cleanup())
            self.loop.close()

    async def _async_start(self, app):
        """Inicializa el runner y el sitio TCP."""
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', SERVER_PORT)
        await self.site.start()
        self.log_signal.emit(Log.success(f"Overlay Online: http://127.0.0.1:{SERVER_PORT}"))

    async def _async_cleanup(self):
        """Cierra conexiones pendientes al apagar."""
        # 1. Desconectar clientes WebSocket
        if self.websockets:
            for ws in list(self.websockets):
                await ws.close(code=1001, message=b"Server shutting down")        
        # 2. Detener servidor
        if self.site: 
            await self.site.stop()
        if self.runner: 
            await self.runner.cleanup()

    # =========================================================================
    # REGIÓN 3: RUTAS HTTP & ARCHIVOS
    # =========================================================================
    def _setup_routes(self, app):
        # Index: El HTML principal
        app.router.add_get('/', self.handle_index)
        # WebSocket: Canal de datos
        app.router.add_get('/ws', self.websocket_handler)        
        # Media: Archivos del usuario (imágenes/sonidos)
        app.router.add_get('/media/{filename}', self.handle_media_request)       
        # Assets: CSS/JS estáticos propios del bot
        assets_path = self._get_asset_path("") 
        if os.path.exists(assets_path):
            app.router.add_static('/assets', path=assets_path)

    async def handle_index(self, request):
        path = self._get_asset_path("overlay.html")
        if os.path.exists(path):
            return web.FileResponse(path)
        return web.Response(status=404, text="<h1>Error 404</h1><p>overlay.html no encontrado en assets.</p>", content_type='text/html')

    async def handle_media_request(self, request):
        """Sirve archivos dinámicos desde la carpeta configurada por el usuario."""
        filename = request.match_info['filename']
        user_media_folder = self.db.get("media_folder")
        
        if not user_media_folder or not os.path.exists(user_media_folder):
            return web.Response(status=404, text="Carpeta multimedia no configurada.")
            
        full_path = os.path.join(user_media_folder, filename)
        
        try:
            full_path = os.path.abspath(full_path)
            base_path = os.path.abspath(user_media_folder)
            if not full_path.startswith(base_path):
                return web.Response(status=403, text="Acceso Denegado.")
        except:
            return web.Response(status=400, text="Ruta inválida.")

        if os.path.exists(full_path) and os.path.isfile(full_path):
            return web.FileResponse(full_path, chunk_size=CHUNK_SIZE)
            
        return web.Response(status=404, text="Archivo no encontrado.")

    # =========================================================================
    # REGIÓN 4: GESTIÓN DE WEBSOCKETS
    # =========================================================================
    async def websocket_handler(self, request):
        """Maneja la conexión persistente con el overlay."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    self.log_signal.emit(Log.error(f'WS Error: {ws.exception()}'))
        finally:
            self.websockets.discard(ws)
        return ws

    async def _broadcast(self, action: str, payload: Dict[str, Any]):
        """Envía JSON a todos los clientes conectados."""
        if not self.websockets: return
        data = {"action": action}
        if payload: data.update(payload)

        active_sockets = list(self.websockets)
        
        for ws in active_sockets:
            try:
                await ws.send_json(data)
            except Exception:
                self.websockets.discard(ws)

    # =========================================================================
    # REGIÓN 5: UTILIDADES DE RUTAS
    # =========================================================================
    def _get_asset_path(self, filename: str) -> str:
        """
        Resuelve rutas de archivos estáticos. 
        """
        if hasattr(sys, '_MEIPASS'): 
            base_dir = os.path.join(sys._MEIPASS, "assets")
        else:         
            # 1. Obtenemos ruta del archivo actual (.../backend/workers/overlay_worker.py)
            current_file = os.path.abspath(__file__)           
            # 2. Subimos a 'workers'
            workers_dir = os.path.dirname(current_file)           
            # 3. Subimos a 'backend'
            backend_dir = os.path.dirname(workers_dir)           
            # 4. Subimos a 'Raíz del Proyecto'
            root_dir = os.path.dirname(backend_dir)
            base_dir = os.path.join(root_dir, "assets")

        return os.path.join(base_dir, filename) if filename else base_dir