# backend/workers/chat_worker.py

import sys
import json
import asyncio
from pathlib import Path
from aiohttp import web, WSMsgType
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class ChatOverlayWorker(QObject):
    # ==========================================
    # 1. SEÑALES UI
    # ==========================================
    service_started = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port=6001):
        super().__init__()
        self.port = port
        self.app = web.Application()
        
        # Rutas del servidor
        self.app.router.add_get('/chat', self.chat_overlay_handler)
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Ruta estática para assets (CSS, JS, imágenes) dentro de la carpeta overlays
        overlays_path = self._get_overlay_path("")
        if overlays_path.exists():
            self.app.router.add_static('/assets', path=str(overlays_path))

        # Estado interno
        self.runner = None
        self.site = None
        self.clients = set()
        self.loop = None
        self.thread = None
        
        self.latest_config = {} 

    # =========================================================================
    # REGIÓN 2: CICLO DE VIDA DEL SERVIDOR Y AIOHTTP
    # =========================================================================
    def start(self):
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run_server)
        self.thread.start()

    def _run_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_aiohttp())
            self.loop.run_forever()
        except Exception as e:
            self.error_occurred.emit(f"Error en servidor Chat Overlay: {e}")
        finally:
            self.loop.run_until_complete(self._stop_aiohttp())
            self.loop.close()

    async def _start_aiohttp(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await self.site.start()
        self.service_started.emit(f"Servidor Chat Overlay iniciado en http://127.0.0.1:{self.port}/chat")

    async def _stop_aiohttp(self):
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()

    def stop(self):
        if self.loop:
             self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
             self.thread.quit()
             self.thread.wait(1000)

    # =========================================================================
    # REGIÓN 3: UTILIDADES DE RUTAS (COMPATIBILIDAD EXE/DEV)
    # =========================================================================
    def _get_overlay_path(self, filename: str) -> Path:
        """Resuelve rutas de forma dinámica, apuntando a assets/overlays."""
        if hasattr(sys, '_MEIPASS'): 
            # Ruta cuando está compilado (PyInstaller)
            base_dir = Path(sys._MEIPASS) / "assets" / "overlays"
        else:
            # Ruta relativa en modo de desarrollo: 
            # Sube de workers -> backend -> raíz del proyecto -> entra a assets/overlays
            base_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "overlays"

        return base_dir / filename if filename else base_dir

    # =========================================================================
    # REGIÓN 4: HANDLERS HTTP & WEBSOCKETS
    # =========================================================================
    async def chat_overlay_handler(self, request):
        path = self._get_overlay_path("chat_overlay.html")
        
        if path.exists():
            return web.FileResponse(path)
            
        return web.Response(
            status=404, 
            text=f"<h1>Error 404</h1><p>Archivo chat_overlay.html no encontrado en:<br>{path}</p>", 
            content_type='text/html'
        )

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        
        # Enviar la última configuración de estilos al conectar
        if self.latest_config:
            await ws.send_str(json.dumps({
                "type": "update_chat_styles", 
                "payload": self.latest_config
            }))
            
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    print(f'WS cerrado con excepción: {ws.exception()}')
        finally:
            self.clients.remove(ws)
        return ws

    # =========================================================================
    # REGIÓN 5: MÉTODOS DE DIFUSIÓN (BROADCAST) A LOS CLIENTES
    # =========================================================================
    async def broadcast_data(self, data_dict):
        if not self.clients: return
        message = json.dumps(data_dict)

        await asyncio.gather(
            *(ws.send_str(message) for ws in self.clients if not ws.closed), 
            return_exceptions=True
        )

    def send_chat_message_to_overlay(self, sender, content, badges=None, user_color=None, timestamp=""):
        if not self.loop: return
        payload = {
            "type": "new_message",
            "payload": {
                "sender": sender, 
                "content": content,
                "badges": badges or [], 
                "color": user_color, 
                "timestamp": timestamp
            }
        }
        asyncio.run_coroutine_threadsafe(self.broadcast_data(payload), self.loop)

    def update_chat_styles(self, style_dict):
        if not self.loop: return

        # Actualiza el diccionario de la configuración más reciente
        self.latest_config |= style_dict
        
        payload = {"type": "update_chat_styles", "payload": style_dict}
        asyncio.run_coroutine_threadsafe(self.broadcast_data(payload), self.loop)