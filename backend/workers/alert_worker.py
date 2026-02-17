# backend/workers/alert_worker.py

import sys
import json
import asyncio
from pathlib import Path
from aiohttp import web, WSMsgType
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class AlertOverlayWorker(QObject):
    # ==========================================
    # 1. SEÑALES UI
    # ==========================================
    service_started = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port=6002): # 🔴 Usamos el puerto 6002 para no chocar con el Chat (6001)
        super().__init__()
        self.port = port
        self.app = web.Application()
        
        # Rutas exclusivas del servidor de Alertas
        self.app.router.add_get('/alerts', self.alerts_overlay_handler)
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Ruta estática para assets
        overlays_path = self._get_overlay_path("")
        if overlays_path.exists():
            self.app.router.add_static('/assets', path=str(overlays_path))

        # Estado interno
        self.runner = None
        self.site = None
        self.clients = set()
        self.loop = None
        self.thread = None

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
            self.error_occurred.emit(f"Error en servidor Alerts Overlay: {e}")
        finally:
            self.loop.run_until_complete(self._stop_aiohttp())
            self.loop.close()

    async def _start_aiohttp(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await self.site.start()
        self.service_started.emit(f"Servidor de Alertas iniciado en http://127.0.0.1:{self.port}/alerts")

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
    # REGIÓN 3: UTILIDADES DE RUTAS
    # =========================================================================
    def _get_overlay_path(self, filename: str) -> Path:
        if hasattr(sys, '_MEIPASS'): 
            base_dir = Path(sys._MEIPASS) / "assets" / "overlays"
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "overlays"
        return base_dir / filename if filename else base_dir

    # =========================================================================
    # REGIÓN 4: HANDLERS HTTP & WEBSOCKETS
    # =========================================================================
    async def alerts_overlay_handler(self, request):
        path = self._get_overlay_path("alerts_overlay.html")
        if path.exists():
            return web.FileResponse(path)
        return web.Response(
            status=404, 
            text=f"<h1>Error 404</h1><p>Archivo alerts_overlay.html no encontrado en:<br>{path}</p>", 
            content_type='text/html'
        )

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    print(f'WS Alertas cerrado con excepción: {ws.exception()}')
        finally:
            self.clients.remove(ws)
        return ws

    # =========================================================================
    # REGIÓN 5: MÉTODO DE DISPARO DE ALERTAS (BROADCAST)
    # =========================================================================
    async def broadcast_data(self, data_dict):
        if not self.clients: return
        message = json.dumps(data_dict)
        await asyncio.gather(
            *(ws.send_str(message) for ws in self.clients if not ws.closed), 
            return_exceptions=True
        )

    def send_alert(self, alert_type: str, title: str, message: str):
        """
        Llama a este método desde tu bot para disparar la alerta visual en OBS.
        alert_type: 'follow', 'subscription', 'host', etc.
        """
        if not self.loop: return
        payload = {
            "type": "new_alert",
            "payload": {
                "alert_type": alert_type, 
                "title": title,
                "message": message
            }
        }
        asyncio.run_coroutine_threadsafe(self.broadcast_data(payload), self.loop)